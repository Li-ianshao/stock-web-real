import os
import pickle
import numpy as np
import pandas as pd
import ta
import yfinance as yf
from datetime import datetime
from django.http import JsonResponse
from ta.momentum import RSIIndicator
import pytz

# 預設快取檔路徑
CACHE_FILE = 'cache/sp500_data.pico'
CACHE_DIR = 'cache/'

def fetch_historical_data(symbol, period='10y', holding_days=[5, 10, 15, 20], goals=[2, 2.5, 3, 3.5, 4, 4.5, 5, 8, 10]):
    df = yf.download(symbol, period=period, auto_adjust=True)

    if df.empty or len(df) < 30:
        return None

    close_series = df['Close'].squeeze()
    df['RSI'] = ta.momentum.RSIIndicator(close_series, window=14).rsi()
    df.dropna(inplace=True)

    signals = []
  
    for i in range(1, len(df) - max(holding_days)):
        if df['RSI'].iloc[i-1] < 30 and df['RSI'].iloc[i] >= 30:
            buy_date = df.index[i]
            buy_price = float(df['Close'].iloc[i].item() if isinstance(df['Close'].iloc[i], pd.Series) else df['Close'].iloc[i])
            row = [buy_date.strftime('%Y-%m-%d'), buy_price]
            # 計算各持有日數的賣出價和報酬
            for n in holding_days:
                colName = 'High_' + str(n) + 'd'
                df_temp = df[df.index > buy_date]
            
                df_nd = df_temp.head(n)
                df_nd_High = df_nd['High'].max()
                row.extend(df_nd_High)

            signals.append(row)

    if not signals:
        return "近五年無 RSI 上穿 30 的事件"

    # 整理 DataFrame
    cols = ['BuyDate', 'BuyPrice']
    for n in holding_days:
        cols += [f'High_{n}d']
    
    signals_df = pd.DataFrame(signals, columns=cols)
    signals_df = signals_df.round(2)

    for n in holding_days:
        for x in goals:
            signals_df['G_' + str(x) + '%_' + str(n) + 'd'] = np.where(signals_df['High_' + str(n) + 'd'] > signals_df['BuyPrice'] * (1 + x/100), 1, 0)

    signals_df.to_csv(f"RSI_Crossover30_{symbol}_signals.csv", index=False)

    return signals_df

def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    tickers = df['Symbol'].tolist()
    tickers = [t.replace('.', '-') for t in tickers]
    return tickers

def getData(ticker_list):
    data = yf.download(
        tickers = ticker_list,
        period = '6mo',
        interval = '1d',
        group_by = 'ticker',
        auto_adjust = False,
        prepost = False,
        threads = True,
        proxy = None,
        timeout=10
    )
    data = data.T
    return data

def clear_all_pickles():
    print('clear_all_pickles')
    """
    刪除指定資料夾下所有 .pkl 檔案
    """
    if not os.path.exists(CACHE_DIR):
        print(f"快取資料夾不存在：{CACHE_DIR}")
        return

    count = 0
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".pico"):
            os.remove(os.path.join(CACHE_DIR, filename))
            count += 1
    print(f"已刪除 {count} 個 .pico 快取檔案")

def fetch_stock_data(symbols, period='3mo', interval='1d'):
    """
    從 yfinance 抓取多支股票的歷史價格與 info
    :return: {symbol: {'history': DataFrame, 'info': dict}}
    """
    result = {}
    for symbol in symbols:
        try:
            print(f"正在抓取 {symbol} 的資料...")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                print(f"發現 {symbol} 無歷史資料，跳過")
                continue

            result[symbol] = {
                'history': hist,
                'info': ticker.info
            }

        except Exception as e:
            print(f"抓取 {symbol} 失敗：{e}")
            continue
    
    central = pytz.timezone("America/Chicago")
    now_ct = datetime.now(central).strftime('%Y-%m-%d %H:%M:%S')
    with open('cache/last_updated.txt', 'w') as f:
        f.write(now_ct)

    return result


def load_or_fetch_stock_data(symbols, period='3mo', interval='1d', cache_path=CACHE_FILE, force_reload=False):
    """
    嘗試從本地讀取快取資料；若無則從 yfinance 抓取並寫入 pickle 快取
    """
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    if not force_reload and os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                print(f"從快取載入資料：{cache_path}")
                return pickle.load(f)
        except Exception as e:
            print(f"無法讀取快取，重新抓取：{e}")

    # 抓取新資料
    print("開始從 yfinance 抓取資料...")
    data = fetch_stock_data(symbols, period=period, interval=interval)

    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"資料已快取到：{cache_path}")
    except Exception as e:
        print(f"無法寫入快取：{e}")

    return data
