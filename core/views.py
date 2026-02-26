import base64
import io
import math
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 
import json
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import ta as TA
import pandas_ta as ta
from core.utils.fetcher import fetch_stock_data, load_or_fetch_stock_data, clear_all_pickles, fetch_historical_data, getData, get_sp500_tickers, get_latest_stock_price
from core.utils.screener import filter_bband_stocks, filter_dividend_stocks, filter_rsi_alert_stocks, filter_macd_cross_stocks, filter_big_drop_stocks, get_stock_data_by_symbol, calculate_bbands, calculate_rsi, calculate_macd
from core.constants import load_sp500_symbols, TEST_SYMBOLS
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from django.http import JsonResponse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import seaborn as sns
from matplotlib.font_manager import FontProperties
from django.views.decorators.csrf import csrf_exempt
ch_font = FontProperties(fname='C:/Windows/Fonts/msjh.ttc')  # Windows 微軟正黑體路徑
import re
import time
import requests
from core.DivindendChartGenerator import get_dividend_chart_base64
import yfinance as yf

#print(load_sp500_symbols()) 有抓到S&P500清單

# 將歷年股價資料的nan或是空值轉換成none 屬於工具類
def nan_to_none(obj):
    if isinstance(obj, float) and np.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_to_none(v) for v in obj]
    return obj



#========================================================================================
# 設定Azure翻譯套件環境
# 載入 .env 檔案
load_dotenv()

AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION")
AZURE_TRANSLATOR_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT")

#=======================================================================================



latest_stock_data = None


def stock_price_api(request, symbol):
    """
    提供給前端呼叫的 API View
    """
    price_data = get_latest_stock_price(symbol)
    
    if price_data:
        return JsonResponse(price_data)
    else:
        return JsonResponse({"status": "error", "message": "無法獲取股價"}, status=400)

@csrf_exempt
def stockdata_api(request):
    global latest_stock_data

    if request.method == 'POST':
        # 1. 接收前端傳來的 JSON
        try:
            data = json.loads(request.body.decode('utf-8'))
            latest_stock_data = {
                "update_time": time.time(),  # UNIX timestamp
                "data": data
            }
            # 將資料寫入檔案
            with open('latest_data.json', 'w', encoding='utf-8') as f:
                json.dump(latest_stock_data, f)
            return JsonResponse({'status': 'success', 'msg': '資料已收到並存儲'}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': f'資料格式錯誤: {e}'}, status=400)
    
    elif request.method == 'GET':
        # 2. 回傳最新資料
        if latest_stock_data is not None:
            return JsonResponse(latest_stock_data, safe=False)
        else:
            with open('latest_data.json', 'r', encoding='utf-8') as f:
                latest_stock_data = json.load(f)
            return JsonResponse(latest_stock_data, safe=False)

    else:
        return JsonResponse({'status': 'error', 'msg': '不支援的方法'}, status=405)
    


# 產業與對應的代表性 ETF 
SECTORS = {
    'Technology (科技)': 'XLK',
    'Health Care (醫療)': 'XLV',
    'Financials (金融)': 'XLF',
    'Energy (能源)': 'XLE',
    'Consumer Discretionary (非必需消費)': 'XLY',
    'Consumer Staples (必需消費)': 'XLP',
    'Industrials (工業)': 'XLI',
    'Materials (原物料)': 'XLB',
    'Real Estate (房地產)': 'XLRE',
    'Utilities (公用事業)': 'XLU',
    'Communication Services (通訊)': 'XLC'
}

def index(request):
    """渲染前端 HTML 頁面"""
    return render(request, 'streamgraph/index.html')

def get_flow_data(request):
    """提供給 D3.js 的 API，回傳過去一年的資金流動數據"""
    tickers = list(SECTORS.values())
    
    # 取得過去一年的週線資料 (用週線可以讓河流圖更平滑)
    data = yf.download(tickers, period="1y", interval="1wk")
    
    # 計算資金流動 (Dollar Volume) = 收盤價 * 成交量
    # yfinance 回傳的多層級 MultiIndex DataFrame: data['Close']['XLK']
    df_close = data['Close']
    df_volume = data['Volume']
    df_flow = df_close * df_volume
    
    # 處理缺失值
    df_flow = df_flow.fillna(0)
    
    # 轉換格式以符合 D3.js 需求
    # 目標格式: [{'date': '2023-01-01', 'Technology': 1000, 'Financials': 2000, ...}, ...]
    result = []
    for date, row in df_flow.iterrows():
        item = {'date': date.strftime('%Y-%m-%d')}
        for sector_name, ticker in SECTORS.items():
            # 確保數值是 Python 原生的 float
            item[sector_name] = float(row[ticker]) if ticker in row else 0
        result.append(item)
        
    # 將資料餵給AI並進行分析
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
        「你是一位專業的首席分析師。以下是美股 11 大產業的資金流動數據。請直接針對數據進行診斷分析，嚴禁在回覆中重複、列出或引用原始 JSON 數據。請直接以 Markdown 格式輸出分析重點，包含：1. 資金集中度、2. 異常波動、3. 產業輪動建議。」
        
        這是我過去一年美股 11 大產業的資金流動數據。

        {result}
        
        請幫我分析：

        目前市場的資金主要集中在哪三個板塊？這反映了什麼樣的投資人情緒？

        觀察 2026 年 2 月的波峰，哪些產業擴張最明顯？結合當時的財報季，這是否具備持續性？

        是否存在資金從防禦型（Utilities/Staples）轉向進攻型（Tech/Financials）的訊號？

        根據資金流動趨勢，下一個季度我應該關注哪些潛在被低估或過熱的產業？」
        """

    try:
        # 2026 年新版 SDK 呼叫方式
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        analysis_result = response.text
        
    except Exception as e:
        if "429" in str(e):
            analysis_result = "### ⚠️ 流量限制\n免費版請求太快，請等一分鐘再試。"
        else:
            analysis_result = f"### ❌ API 呼叫失敗\n{str(e)}"

    print("AI分析")
    print(analysis_result)
    return JsonResponse({
        'data': result,
        'aiResponse': analysis_result
    }, safe=False)


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
# 設定FinHub的環境變數，用來抓Form4的必要設定
def _check_key():
    api_key = FINNHUB_API_KEY
    if not api_key:
        raise RuntimeError("請先設定環境變數 FINNHUB_API_KEY")
    return api_key

# 1. 設定您的 Gemini API Key 
from google import genai  #免費版
from django.shortcuts import render

# 初始化 Client (API Key 放在這裡)  



def stock_analysis_view(request, symbol):
    # 1. 初始化新版 Client 
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    symbol = symbol.upper()
    analysis_result = ""


    try:
        # --- A. 抓取 yfinance 資料 ---
        stock = yf.Ticker(symbol)
        
        # 1. 基本面
        info = stock.info
        fundamental = {
            "公司名稱": info.get("longName", "未知"),
            "產業": info.get("industry", "未知"),
            "本益比": info.get("forwardPE", "N/A"),
            "市值": info.get("marketCap", "N/A"),
            "分析師建議": info.get("recommendationKey", "N/A")
        }

        # 2. 技術指標
        df = stock.history(period="6mo")
        latest_tech = {}
        if not df.empty:
            # # RSI
            # delta = df['Close'].diff()
            # gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            # loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            # df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            # # MACD
            # exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            # exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            # df['MACD'] = exp1 - exp2

            # 1. 計算 RSI (預設長度為 14)
            # append=True 會直接將結果 'RSI_14' 加入 df
            df.ta.rsi(length=14, append=True)

            # 2. 計算 MACD (預設 fast=12, slow=26, signal=9)
            # append=True 會加入 'MACD_12_26_9', 'MACDH_12_26_9', 'MACDS_12_26_9'
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
                        

            
            
            # BBAND
            bbands_data = df.ta.bbands(length=20, std=2)
            print(df)
            latest_tech = {
                "最後收盤價": round(df['Close'].iloc[-1], 2),
                "RSI": round(df['RSI_14'].iloc[-1], 2) if not pd.isna(df['RSI_14'].iloc[-1]) else "N/A",
                "MACD": round(df['MACD_12_26_9'].iloc[-1], 2) if not pd.isna(df['MACD_12_26_9'].iloc[-1]) else "N/A",
                "布林上限": round(bbands_data['BBU_20_2.0_2.0'].iloc[-1], 2),
                "布林中軌": round(bbands_data['BBM_20_2.0_2.0'].iloc[-1], 2),
                "布林下限": round(bbands_data['BBL_20_2.0_2.0'].iloc[-1], 2)
            }
            print(latest_tech)


        # 3. 選擇權與新聞
        expirations = stock.options

        if expirations:
            # 抓取最近一個到期日的資料
            latest_expiry = expirations[0]
            opts = stock.option_chain(latest_expiry)
            
            # 2. 整理 Call 和 Put 的簡單統計 (例如成交量最大的合約)
            calls = opts.calls.sort_values(by='volume', ascending=False).head(3)
            puts = opts.puts.sort_values(by='volume', ascending=False).head(3)
            
            # 計算 Put/Call Ratio (以成交量計)
            total_call_vol = opts.calls['volume'].sum()
            total_put_vol = opts.puts['volume'].sum()
            pc_ratio = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else "N/A"

            options_summary = {
                "到期日": latest_expiry,
                "Put/Call成交量比": pc_ratio,
                "熱門Call(履約價)": calls['strike'].tolist(),
                "熱門Put(履約價)": puts['strike'].tolist(),
            }
        else:
            options_summary = "該標的無選擇權交易資料"
        
        # print(options_summary)
        raw_news = stock.news
        news_list = []

        if raw_news:
            for n in raw_news[:5]:
                # 嘗試從多個可能的鍵值中抓取資訊
                # 優先順序：標題 (title) -> 摘要 (text) -> 發佈者 (publisher) -> 最後才顯示「無標題」
                content = n.get('content', {})
                title = content.get('title') or content.get('text') or content.get('publisher') or "無標題"
                
                # 如果抓到的是 publisher，可以稍微標註一下
                if title == content.get('publisher'):
                    title = f"來自 {title} 的相關報導"
                    
                news_list.append(title)
        else:
            news_list = ["目前無相關新聞數據"]


        print(news_list)

        
        prompt = f"""
        針對 {symbol} 的基本面，技術面，選擇權籌碼面進行深度診斷：
        1. 基本面簡述：{fundamental}
        2. 技術指標參考：{latest_tech}
        3. 新聞面:{news_list}
        4. 選擇權異動資料：{options_summary}

        請特別針對「Put/Call Ratio」與「熱門履約價」進行解讀：
        - 目前的成交量分佈暗示了市場看漲還是看跌？
        - 壓力位與支撐位可能落在哪些履約價附近？
        - 綜合給出投資風險評估與繁體中文建議。
        """

        try:
            # 2026 年新版 SDK 呼叫方式
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            analysis_result = response.text
        except Exception as e:
            if "429" in str(e):
                analysis_result = "### ⚠️ 流量限制\n免費版請求太快，請等一分鐘再試。"
            else:
                analysis_result = f"### ❌ API 呼叫失敗\n{str(e)}"

    except Exception as e:
        analysis_result = f"### ❌ 數據處理發生錯誤\n{str(e)}"

    # 改為回傳 JsonResponse，對接前端的淡藍色對話框
    return JsonResponse({
        'status': 'success',
        'ticker': symbol,
        'analysis_result': analysis_result
    })

    

def get_form4_data(symbol: str, from_date: str = None, to_date: str = None, with_sentiment: bool = False):
    """
    從 Finnhub 抓取內部人交易 (近似 Form 4)；可選擇一併抓 insider sentiment。

    Args:
        symbol (str): 如 "CTSH"
        from_date (str|None): "YYYY-MM-DD"
        to_date (str|None): "YYYY-MM-DD"
        with_sentiment (bool): 是否同時抓 insider sentiment

    Returns:
        dict: {
          "transactions": pd.DataFrame,   # 內部人交易
          "sentiment": pd.DataFrame|None  # 月度情緒 (選擇性)
        }
    """
    token = _check_key()

    # --- insider transactions ---
    tx_params = {"symbol": symbol, "token": token}
    if from_date: tx_params["from"] = from_date
    if to_date:   tx_params["to"] = to_date

    BASE = "https://finnhub.io/api/v1"

    tx_resp = requests.get(f"{BASE}/stock/insider-transactions", params=tx_params, timeout=30)
    tx_resp.raise_for_status()
    tx_json = tx_resp.json()
    tx_df = pd.DataFrame(tx_json.get("data", []))

    # 正規化常用欄位（可能少數欄位缺失，先補齊避免 KeyError）
    for col in ["symbol","name","transaction","share","change","price","filingDate","transactionDate","offset"]:
        if col not in tx_df.columns:
            tx_df[col] = pd.NA

    # --- insider sentiment (optional) ---
    sent_df = None
    if with_sentiment:
        sent_params = {"symbol": symbol, "token": token}
        sent_resp = requests.get(f"{BASE}/stock/insider-sentiment", params=sent_params, timeout=30)
        sent_resp.raise_for_status()
        sent_json = sent_resp.json()
        sent_df = pd.DataFrame(sent_json.get("data", []))
        # 一樣做欄位補齊
        for col in ["symbol","year","month","change","mspr"]:
            if col not in sent_df.columns:
                sent_df[col] = pd.NA

    return {"transactions": tx_df, "sentiment": sent_df}

def get_form4_clean(symbol: str, only_buy_sell: bool = True, days=90):
    """
    回傳清洗後的交易資料（預設只保留 Buy/Sale 與常用欄位）。
    """

    today = datetime.today().date()
    three_months_ago = today - timedelta(days=days)   # 大約 3 個月

    data = get_form4_data(symbol, from_date=str(three_months_ago), to_date=str(today), with_sentiment=False)
    df = data["transactions"].copy()

    if df.empty:
        return df

    if only_buy_sell:
        df = df[df["transaction"].isin(["Buy","Sale"])]

    # 轉日期型別 & 排序
    for c in ["filingDate","transactionDate"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df = df.sort_values(["filingDate","transactionDate"], ascending=[False, False])

    # 精簡欄位順序
    keep = ["symbol","name","transactionCode","share","change","transactionPrice","filingDate","transactionDate"]
    df = df[[c for c in keep if c in df.columns]]
    return df


def azure_translate_texts(texts, to_lang="zh-Hant", timeout=15, chunk_size=50):
    
    if not texts:
        return []
    url = f"{AZURE_TRANSLATOR_ENDPOINT}?api-version=3.0&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    out = []
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        body = [{"text": (t or "")} for t in chunk]
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        out.extend([item["translations"][0]["text"] for item in data])
    return out

def translate_news_items(news_items, to_lang="zh-Hant"):
    """
    接受你貼的 list[dict] 結構，為每筆加上 title_zh、summary_zh 後回傳同一個 list。
    """
    if not news_items:
        return news_items

    titles   = [n.get("title", "") for n in news_items]
    summaries = [n.get("summary", "") for n in news_items]

    titles_zh   = azure_translate_texts(titles, to_lang=to_lang)
    summaries_zh = azure_translate_texts(summaries, to_lang=to_lang)

    for n, t_zh, s_zh in zip(news_items, titles_zh, summaries_zh):
        n["title_zh"] = t_zh
        n["summary_zh"] = s_zh

    # 可選：標記語言
    # 你也可以在外層加個 news_lang，如果需要的話
    return news_items

def stock_api(request, symbol):
    symbol = symbol.upper()
    period = '10y'
    stock_data = fetch_stock_data([symbol], period='1y')

    short_interest = stock_data[symbol]['info'].get("sharesShort", None)   # 放空股數
    short_ratio = stock_data[symbol]['info'].get("shortRatio", None)       # 放空比率

    # print(f"Short Interest: {short_interest}")
    # print(f"Short Ratio: {short_ratio}")

    news_list = []
    for news in stock_data.get(symbol, {}).get('news', []):
        content = news.get('content', {}) or {}
        click_url = content.get('clickThroughUrl', {}) or {}

        news_list.append({
            "title": content.get('title') or "(No title)",
            "pubDate": content.get('pubDate') or "(No date)",
            "provider": content.get('provider') or "(No provider)",
            "link": click_url.get('url') or "",
            "summary": content.get('summary') or "(No summary)"
        })

    news_list_translated = translate_news_items(news_list)

    #print(news_list_translated)

    holding_days = [5, 10, 15, 20, 30, 40]

    goals=[2, 4, 6, 8, 10]

    historical_data = fetch_historical_data(symbol,period=period,holding_days=holding_days, goals=goals)
    # print(historical_data)

    if historical_data is None or historical_data.empty:
        historical_data = pd.DataFrame(columns=['None', 'no data'])

    
    
    # 
    # return_cols = [f"Return_{n}d(%)" for n in holding_days]

    # # 計算平均報酬
    # mean_returns = historical_data[return_cols].mean()

    # # 畫圖
    # 抓目標和天數
    df = stock_data[symbol]['history'].copy()
    
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(symbol, axis=1, level=1)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

    # BBands
    bb = TA.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Upper'] = bb.bollinger_hband()

    # MACD
    macd = TA.trend.MACD(df['Close'])
    df['MACD'] = macd.macd().squeeze()
    df['MACD_signal'] = macd.macd_signal().squeeze()
    df['MACD_hist'] = macd.macd_diff().squeeze()

    # RSI
    df['RSI'] = TA.momentum.RSIIndicator(df['Close'], window=14).rsi()

    # 策略信號
    df['BB_Lower_Cross'] = ((df['Close'].shift(1) < df['BB_Lower'].shift(1)) & (df['Close'] >= df['BB_Lower']))
    df['MACD_GC'] = (df['MACD'].shift(1) < df['MACD_signal'].shift(1)) & (df['MACD'] >= df['MACD_signal'])
    df['RSI_Cross30'] = (df['RSI'].shift(1) < 30) & (df['RSI'] >= 30)


    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios':[3,1.2,1]})

    
    dates = df.index
    candle_w = 2  # 使用時間軸，width設2天

    n_labels = 12
    date_ticks = np.linspace(0, len(df.index) - 1, n_labels, dtype=int)
    date_labels = [df.index[i].strftime('%Y-%m-%d') for i in date_ticks]

    for ax in axes:
        ax.set_xticks(df.index[date_ticks])
        ax.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=12)
            
        

    # 1. K線 + BBAND + 量
    ax = axes[0]
    up = df['Close'] >= df['Open']
    down = ~up
    ax.bar(dates[up], df['Close'][up]-df['Open'][up], candle_w, bottom=df['Open'][up], color='green', edgecolor='k', label='Up')
    ax.bar(dates[down], df['Close'][down]-df['Open'][down], candle_w, bottom=df['Open'][down], color='red', edgecolor='k', label='Down')
    ax.vlines(dates, df['Low'], df['High'], color='black', linewidth=0.5)
    ax.plot(dates, df['BB_Upper'], color='blue', linestyle='--', label='BBand Upper')
    ax.plot(dates, df['BB_Lower'], color='blue', linestyle='--', label='BBand Lower')
    bb_cross = df[df['BB_Lower_Cross']]
    ax.scatter(bb_cross.index, bb_cross['Low']*0.98, color='magenta', marker='o', s=60, label='BBand Lower Break')
    for idx, row in bb_cross.iterrows():
        y = row['Low']*0.96
        date_str = idx.strftime('%Y-%m-%d')
        ax.text(idx, y, date_str, color='magenta', fontsize=8, rotation=90, ha='center', va='top')
    ax2 = ax.twinx()
    ax2.bar(dates, df['Volume'], width=candle_w, color='navy', alpha=0.4, label='Volume')
    ax2.set_ylim(0, df['Volume'].max()*5)
    ax2.axis('off')
    ax.set_ylabel("Price")
    ax.set_title(f"{symbol} Candlestick / BBands / Volume")
    ax.legend(loc='upper left')

    # 2. MACD
    # 先計算 histogram 變動方向
    hist = df['MACD_hist'].values
    # 上一根
    hist_prev = np.roll(hist, 1)
    hist_prev[0] = np.nan

    # 分類
    cond1 = (hist > 0) & (hist > hist_prev)      # 上面且繼續走高 → 亮綠
    cond2 = (hist > 0) & (hist <= hist_prev)     # 上面但回落   → 暗綠
    cond3 = (hist < 0) & (hist < hist_prev)      # 下面繼續走低 → 紅色
    cond4 = (hist < 0) & (hist >= hist_prev)     # 下面但回升   → 暗紅

    dates = df.index

    ax = axes[1]
    pos = df['MACD_hist'] > 0
    neg = ~pos
    ax.bar(dates[cond1], hist[cond1], color='#22c55e', alpha=0.9, label='MACD Hist up ↑')    # 亮綠
    ax.bar(dates[cond2], hist[cond2], color='#166534', alpha=0.85, label='MACD Hist weak ↑') # 暗綠
    ax.bar(dates[cond3], hist[cond3], color='#ef4444', alpha=0.85, label='MACD Hist down ↓') # 紅
    ax.bar(dates[cond4], hist[cond4], color='#7f1d1d', alpha=0.85, label='MACD Hist weak ↓') # 暗紅
    ax.plot(dates, df['MACD'], color='blue', label='MACD')
    ax.plot(dates, df['MACD_signal'], color='orange', label='Signal')
    macd_cross = df[df['MACD_GC']]
    ax.scatter(macd_cross.index, macd_cross['MACD'], color='purple', marker='^', s=80, label='MACD Golden Cross')
    for idx, row in macd_cross.iterrows():
        y = row['MACD']-1 if row['MACD'] > 0 else row['MACD']+1
        date_str = idx.strftime('%Y-%m-%d')
        ax.text(idx, y, date_str, color='red', fontsize=8, rotation=90, ha='center', va='top')
    ax.set_ylabel('MACD')
    ax.set_title("MACD")
    ax.legend(loc='upper left')

    # 3. RSI
    ax = axes[2]
    ax.plot(dates, df['RSI'], color='purple', label='RSI')
    ax.axhline(30, color='grey', linestyle='--', lw=1)
    rsi_cross = df[df['RSI_Cross30']]
    ax.scatter(rsi_cross.index, rsi_cross['RSI'], color='red', marker='^', s=80, label='RSI Crossover 30')
    for idx, row in rsi_cross.iterrows():
        y = row['RSI']*0.97
        date_str = idx.strftime('%Y-%m-%d')
        ax.text(idx, y, date_str, color='purple', fontsize=8, rotation=90, ha='center', va='top')
    ax.set_ylabel('RSI')
    ax.set_title("RSI")
    ax.legend(loc='upper left')

    # x軸日期旋轉
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
    fig.tight_layout()
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64_tech = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()




    if historical_data.empty:
        img_base64_heat_goal = empty_heatmap_base64("No RSI crossing above 30 found in history")
        heat_goal_detail = ""
    else:
        goal_cols = [col for col in historical_data.columns if re.match(r'G_([\d\.]+)%_(\d+)d', col)]
        goals = sorted({float(re.match(r'G_([\d\.]+)%', col).group(1)) for col in goal_cols})
        days = sorted({int(re.match(r'G_[\d\.]+%_(\d+)d', col).group(1)) for col in goal_cols})
        # 熱力圖
        heatmap_data = pd.DataFrame(index=goals, columns=days)
        for t in goals:
            t_fmt = int(t) if t == int(t) else t
            for d in days:
                col = f'G_{t_fmt}%_{d}d'
                if col in historical_data.columns:
                    heatmap_data.loc[t, d] = historical_data[col].mean() * 100
        heatmap_data = heatmap_data.astype(float)

        plt.figure(figsize=(10, 6))
        fig, ax = plt.subplots(figsize=(10,6))
        sns.heatmap(heatmap_data.iloc[::-1], annot=True, fmt=".1f", cmap="YlGnBu", ax=ax)
        ax.set_title("Achievement Rate vs Holding Days")
        ax.set_xlabel("Holding Days")
        ax.set_ylabel("Target Return (%)")

        # 目標達標機率列表
        heat_goal_detail = heatmap_data.round(2).to_dict()  # {天數: {目標報酬: 機率%}}

        # 儲存為 base64 圖片
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        img_base64_heat_goal = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()
        


    # 假設 historical_data 為完整 df，有 DateTimeIndex，有 'Close' 欄
    # dividends 為配息日 datetime 的 list (或 Series)
    dividends = stock_data[symbol]['dividends']
    days = [10, 20, 30, 40, 50, 60]
    results = {d: [] for d in days}



    for div_date in dividends.index:
        if div_date not in df.index:
            continue
        idx = df.index.get_loc(div_date)
        if idx == 0:  # 第一個日期沒前一天
            continue
        pre_close = df.iloc[idx - 1]['Close']
        # 取得之後 N 天內的最大收盤價
        for d in days:
            if idx + d >= len(df):
                continue
            window = df.iloc[idx: idx + d]['Close']
            max_close = window.max()
            pct = (max_close - pre_close) / pre_close * 100
            results[d].append(round(pct, 2))

    # 每一個配息日後 10,20...60天內的最大漲幅
    dividend_list = []
    for div_date in dividends.index:
        if div_date not in df.index: continue
        idx = df.index.get_loc(div_date)
        if idx == 0: continue
        pre_close = df.iloc[idx - 1]['Close']
        item = {'date': div_date.strftime('%Y-%m-%d'), 'pre_close': pre_close}
        for d in days:
            if idx + d >= len(df): continue
            window = df.iloc[idx: idx + d]['Close']
            max_close = window.max()
            pct = (max_close - pre_close) / pre_close * 100
            item[f'max_return_{d}d'] = round(pct, 2)
        dividend_list.append(item)

    # 製作熱力圖 DataFrame
    heatmap_df = pd.DataFrame(
        [[np.mean(results[d]) if results[d] else np.nan for d in days]],
        index=['Max Return %'], columns=days
    )

    plt.figure(figsize=(8,2))
    sns.heatmap(heatmap_df, annot=True, fmt=".2f", cmap="YlGnBu")
    plt.title("Avg Max Return (%) after Dividends")
    plt.xlabel("Days after dividend")
    plt.ylabel("")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64_heat_div = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()


    
    df['Date'] = df.index.strftime('%Y-%m-%d')

    # 加入各項技術指標欄位
    df['upper_band'], df['lower_band'] = calculate_bbands(df)
    df['rsi'] = calculate_rsi(df,False)
    df['macd'], df['signal'], df['hist'] = calculate_macd(df['Close'])

    df = df.where(pd.notnull(df), None)

    dividends_list = [
        {"date": dt.strftime("%Y-%m-%d"), "dividend": float(v)}
        for dt, v in stock_data[symbol]['dividends'].items()
    ]

    # 1) 整體比例（機構/內部人持股）
    info = {}
    try:
        # heldPercentInstitutions / heldPercentInsiders 與 Yahoo 頁面一致
        i_pct = stock_data[symbol]['info'].get("heldPercentInstitutions")
        insider_pct = stock_data[symbol]['info'].get("heldPercentInsiders")
        info = {
            "institution_percent": round(i_pct * 100, 2) if isinstance(i_pct, (int, float)) else None,
            "insider_percent": round(insider_pct * 100, 2) if isinstance(insider_pct, (int, float)) else None,
        }
    except Exception:
        info = {"institution_percent": None, "insider_percent": None}

    # 2) 機構持股明細（前幾大機構）
    holders = []
    try:
        ih = stock_data[symbol]['institutional_holders']  # DataFrame: Holder, Shares, Date Reported, % Out, Value
        if ih is not None and not ih.empty:
            df_holders = ih.copy()
            # 欄名在不同版本可能是 '% Out' 或 'Percent Out'
            pct_col = "% Out" if "% Out" in df_holders.columns else ("Percent Out" if "Percent Out" in df_holders.columns else None)

            # 轉文字避免 Timestamp/NaN
            if "Date Reported" in df.columns:
                df_holders["Date Reported"] = df_holders["Date Reported"].astype(str)

            def safe_float(x):
                try:
                    return float(x)
                except Exception:
                    return None

            for _, r in df_holders.iterrows():
                holders.append({
                    "holder": str(r.get("Holder", "")),
                    "shares": int(r.get("Shares")) if not (isinstance(r.get("Shares"), float) and math.isnan(r.get("Shares"))) else None,
                    "date_reported": r.get("Date Reported"),
                    "percent_out": round(safe_float(r.get(pct_col)) * 100, 4) if pct_col and r.get(pct_col) is not None else None,
                    "value": int(r.get("Value")) if r.get("Value") is not None and not (isinstance(r.get("Value"), float) and math.isnan(r.get("Value"))) else None,
                })
    except Exception:
        holders = []
        holders.append({
                    "holder": "查無資料"
                })

    # 3) Major holders（快速總覽：機構/內部人持股比、浮動股數等）
    major = []
    
    try:
        mh = stock_data[symbol]['major_holders']  # 常見為 4×2 的表（% insiders / % institutions / shares outstanding / float）
        if mh is not None:
            # 轉成「標題: 值」陣列
            # yfinance 常見行為：第一欄為數值、第二欄為描述
            for index, row in mh.iterrows():
                # print(index)
                try:
                    value = mh.loc[index, 'Value']
                    label = index
                    # 百分比類轉成 %
                    if isinstance(value, (int, float)) and "Percent" in str(label):
                        value = f"{round(value * 100, 2)}%"
                    major.append({"label": str(label), "value": str(value)})
                except Exception as e:
                    print(f"Error happened: {e}")
                    major.append({"label": index, "value": "Can't find data"})
                    continue
    except Exception as e:
        print(f"Error happened: {e}")
        major = []
        major.append({"label": "holder", "value": "Can't find data"})




    price_data = df.to_dict(orient='records')
    price_data = nan_to_none(price_data)  # 這步最重要！

    dividend_ts = stock_data[symbol]['info'].get('dividendDate')
    exDividendDate_ts = stock_data[symbol]['info'].get('exDividendDate')
    
    if dividend_ts:
        dividend_date = datetime.fromtimestamp(dividend_ts).strftime('%Y-%m-%d')
        exDividend_Date = datetime.fromtimestamp(exDividendDate_ts).strftime('%Y-%m-%d')
    else:
        dividend_date = "找不到配息日資料"
        exDividend_Date = "找不到配息日資料"
    
    #取得Form 4 資料
    Form4 = get_form4_clean(symbol, only_buy_sell=False)
    # print(price_data)
    
    Form4_transactions = Form4.to_dict(orient="records") if not Form4.empty else []

    # 抓取十年配息資料並繪製成統計表
    div_chart = get_dividend_chart_base64(symbol)

    

    return JsonResponse({
        'symbol': symbol,
        #Profitability & Operations
        'trailing_eps': stock_data[symbol]['info'].get('trailingEps',"(Empty)"),
        'forward_eps': stock_data[symbol]['info'].get('forwardEps',"(Empty)"),
        'return_on_assets': stock_data[symbol]['info'].get('returnOnAssets',"(Empty)"),
        'return_on_equity': stock_data[symbol]['info'].get('returnOnEquity',"(Empty)"),
        'gross_margins': stock_data[symbol]['info'].get('grossMargins',"(Empty)"),
        'operating_margins': stock_data[symbol]['info'].get('operatingMargins',"(Empty)"),
        'profit_margins': stock_data[symbol]['info'].get('profitMargins',"(Empty)"),
        'ebitda': stock_data[symbol]['info'].get('ebitda', "(Empty)"),
        'ebitda_margins': stock_data[symbol]['info'].get('ebitdaMargins', "(Empty)"),
        #Valuation & Multiples
        'trailingPE': stock_data[symbol]['info'].get('trailingPE',"(Empty)"),
        'forwardPE': stock_data[symbol]['info'].get('forwardPE',"(Empty)"),
        'price_to_book': stock_data[symbol]['info'].get('priceToBook',"(Empty)"),
        'price_to_sales': stock_data[symbol]['info'].get('priceToSalesTrailing12Months',"(Empty)"),
        'enterprise_to_ebitda': stock_data[symbol]['info'].get('enterpriseToEbitda', "(Empty)"),
        'dividend_rate': stock_data[symbol]['info'].get('dividendRate',"(Empty)"),
        'dividend_yield': stock_data[symbol]['info'].get('dividendYield',"(Empty)"),
        'payout_ratio': stock_data[symbol]['info'].get('payoutRatio',"(Empty)"),
        #Health & Cash Flow
        'total_debt': stock_data[symbol]['info'].get('totalDebt',"(Empty)"),
        'debt_to_equity': stock_data[symbol]['info'].get('debtToEquity',"(Empty)"),
        'free_cashflow': stock_data[symbol]['info'].get('freeCashflow',"(Empty)"),
        'operating_cashflow': stock_data[symbol]['info'].get('operatingCashflow',"(Empty)"),
        'revenue_growth': stock_data[symbol]['info'].get('revenueGrowth',"(Empty)"),
        #Visualizations
        'techmap': img_base64_tech,
        'div_chart': div_chart,
        'heatmap_goal': img_base64_heat_goal,
        'heatmap_goal_detail': heat_goal_detail,
        'heatmap_div': img_base64_heat_div,
        'heatmap_div_detail': dividend_list,
        'price_data': price_data,
        #Activity & Context
        'institution_overview': info,      # {institution_percent, insider_percent}
        'institutional_holders': holders,  # list of dict
        'major_holders': major,       # list of {label, value}
        'Form4_transactions': Form4_transactions,
        'sharesShort': stock_data[symbol]['info'].get('sharesShort') or stock_data['info'].get('sharesShort',"(Empty)"),
        'shortRatio': stock_data[symbol]['info'].get('shortRatio') or stock_data['info'].get('shortRatio',"(Empty)"),
        'news_list':news_list_translated,
        'dividend_date': dividend_date,
        'exDividend_Date': exDividend_Date,
        'dividends':dividends_list,
        'website': stock_data[symbol]['info'].get('website',"(Empty)"),
        'averageVolume': stock_data[symbol]['info'].get('averageVolume',"(Empty)"),
        'industry': stock_data[symbol]['info'].get('industry',"(Empty)"),
        'event_count': len(historical_data),
        'company_name': stock_data[symbol]['info'].get('longName') or stock_data['info'].get('shortName',"(Empty)"),
        'sharesOutstanding': stock_data[symbol]['info'].get('sharesOutstanding') or stock_data['info'].get('sharesOutstanding',"(Empty)"),
        'sector': stock_data[symbol]['info'].get('sector',"(Empty)"),
        'market_cap': stock_data[symbol]['info'].get('marketCap',"(Empty)"),
    })

def empty_heatmap_base64(text="沒有資料 / No Signal"):
    plt.figure(figsize=(6, 2))
    plt.text(0.5, 0.5, text, fontsize=20, color='gray',
             ha='center', va='center')
    plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_base64

def stock_input_view(request):
    return render(request, 'core/RSI_Cross.html')

def get_last_update_time():
    try:
        with open("cache/last_updated.txt", "r") as f:
            timestamp = f.read().strip()
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "尚無記錄"

def get_raw_data(period='3mo'):
    return load_or_fetch_stock_data(load_sp500_symbols(),period=period)

@login_required
def clear_cache_view(request):
    # print('clear_cache_view');
    clear_all_pickles()
    return redirect('tab_dividend')  # 或跳回首頁頁籤

@login_required
def tab_dividend_view(request):
    filtered_data = filter_dividend_stocks(get_raw_data())
    last_updated = get_last_update_time()
    context = {
        'stocks': filtered_data,
        'column_headers' : [
            {'label': '股票代碼', 'key': 'symbol'},
            {'label': '收盤價', 'key': 'close'},
            {'label': '配息日', 'key': 'ex_date'},  # 這就是你要排序的主欄位
            {'label': '配息金額', 'key': 'dividend'},
            {'label': '此次配息率', 'key': 'dividend_ratio'},
            {'label': '殖利率', 'key': 'yield'},
            {'label': '當日漲跌幅', 'key': 'price_change'},
            {'label': '一年最低價', 'key': 'year_low'},
            {'label': '一年最高價', 'key': 'year_high'},
            {'label': 'RSI', 'key': 'rsi'},
            {'label': 'volume_Delta', 'key': 'volume_delta'},
        ],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
        "last_updated": last_updated,
    }
    return render(request, 'core/tab_dividend.html', context)


@login_required
def tab_rsi_view(request):
    filtered_data = filter_rsi_alert_stocks(get_raw_data())
    last_updated = get_last_update_time()
    context = {
        'stocks': filtered_data,
        'column_headers' : [
            {'label': '股票代碼', 'key': 'symbol'},
            {'label': '收盤價', 'key': 'close'},
            {'label': '配息日', 'key': 'ex_date'},  # 這就是你要排序的主欄位
            {'label': '配息金額', 'key': 'dividend'},
            {'label': '此次配息率', 'key': 'dividend_ratio'},
            {'label': '殖利率', 'key': 'yield'},
            {'label': '當日漲跌幅', 'key': 'price_change'},
            {'label': '一年最低價', 'key': 'year_low'},
            {'label': '一年最高價', 'key': 'year_high'},
            {'label': 'RSI', 'key': 'rsi'},
            {'label': 'volume_Delta', 'key': 'volume_delta'},
        ],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
        "last_updated": last_updated,
    }
    return render(request, 'core/tab_rsi.html', context)

@login_required
def tab_bband_view(request):
    filtered_data = filter_bband_stocks(get_raw_data())
    last_updated = get_last_update_time()
    context = {
        'stocks': filtered_data,
        'column_headers' : [
            {'label': '股票代碼', 'key': 'symbol'},
            {'label': '收盤價', 'key': 'close'},
            {'label': '配息日', 'key': 'ex_date'},  # 這就是你要排序的主欄位
            {'label': '配息金額', 'key': 'dividend'},
            {'label': '此次配息率', 'key': 'dividend_ratio'},
            {'label': '殖利率', 'key': 'yield'},
            {'label': '當日漲跌幅', 'key': 'price_change'},
            {'label': '一年最低價', 'key': 'year_low'},
            {'label': '一年最高價', 'key': 'year_high'},
            {'label': 'RSI', 'key': 'rsi'},
            {'label': 'volume_Delta', 'key': 'volume_delta'},
        ],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
        "last_updated": last_updated,
    }
    return render(request, 'core/tab_bband.html', context)

@login_required
def tab_macd_view(request):
    filtered_data = filter_macd_cross_stocks(get_raw_data())
    last_updated = get_last_update_time()
    context = {
        'stocks': filtered_data,
        'column_headers' : [
            {'label': '股票代碼', 'key': 'symbol'},
            {'label': '收盤價', 'key': 'close'},
            {'label': '配息日', 'key': 'ex_date'},  # 這就是你要排序的主欄位
            {'label': '配息金額', 'key': 'dividend'},
            {'label': '此次配息率', 'key': 'dividend_ratio'},
            {'label': '殖利率', 'key': 'yield'},
            {'label': '當日漲跌幅', 'key': 'price_change'},
            {'label': '一年最低價', 'key': 'year_low'},
            {'label': '一年最高價', 'key': 'year_high'},
            {'label': 'RSI', 'key': 'rsi'},
            {'label': 'volume_Delta', 'key': 'volume_delta'},
        ],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
        "last_updated": last_updated,
    }
    return render(request, 'core/tab_macd.html', context)

@login_required
def tab_drop_view(request):
    filtered_data = filter_big_drop_stocks(get_raw_data())
    last_updated = get_last_update_time()
    context = {
        'stocks': filtered_data,
        'column_headers' : [
            {'label': '股票代碼', 'key': 'symbol'},
            {'label': '收盤價', 'key': 'close'},
            {'label': '配息日', 'key': 'ex_date'},  # 這就是你要排序的主欄位
            {'label': '配息金額', 'key': 'dividend'},
            {'label': '此次配息率', 'key': 'dividend_ratio'},
            {'label': '殖利率', 'key': 'yield'},
            {'label': '當日漲跌幅', 'key': 'price_change'},
            {'label': '一年最低價', 'key': 'year_low'},
            {'label': '一年最高價', 'key': 'year_high'},
            {'label': 'RSI', 'key': 'rsi'},
            {'label': 'volume_Delta', 'key': 'volume_delta'},
        ],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
        "last_updated": last_updated,
    }
    return render(request, 'core/tab_drop.html', context)

@login_required
def stock_detail_view(request, symbol):
    previous_url = request.META.get('HTTP_REFERER')
    if not url_has_allowed_host_and_scheme(url=previous_url, allowed_hosts={request.get_host()}):
        previous_url = reverse('tab_dividend')

    stock_data = get_stock_data_by_symbol(symbol, get_raw_data())

    df = stock_data['history'].copy()
    df['Date'] = df.index.strftime('%Y-%m-%d')

    # 加入各項技術指標欄位
    df['upper_band'], df['lower_band'] = calculate_bbands(df)
    df['rsi'] = calculate_rsi(df,False)
    df['macd'], df['signal'], df['hist'] = calculate_macd(df['Close'])

    df = df.where(pd.notnull(df), None)
    price_data = json.dumps(df.to_dict(orient='records'))

    return render(request, 'core/detail.html', {
        'symbol': symbol,
        'previous_url': previous_url,
        'company_name': stock_data['info'].get('longName') or stock_data['info'].get('shortName'),
        'sector': stock_data['info'].get('sector'),
        'industry': stock_data['info'].get('industry'),
        'employees': stock_data['info'].get('fullTimeEmployees'),
        'address': stock_data['info'].get('address1'),
        'city': stock_data['info'].get('city'),
        'state': stock_data['info'].get('state'),
        'country': stock_data['info'].get('country'),
        'website': stock_data['info'].get('website'),
        'description': stock_data['info'].get('longBusinessSummary'),
        'price_data': price_data
    })
