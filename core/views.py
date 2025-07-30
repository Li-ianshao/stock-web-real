import base64
import io
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 
import json
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import ta
from core.utils.fetcher import fetch_stock_data, load_or_fetch_stock_data, clear_all_pickles, fetch_historical_data
from core.utils.screener import filter_bband_stocks, filter_dividend_stocks, filter_rsi_alert_stocks, filter_macd_cross_stocks, filter_big_drop_stocks, get_stock_data_by_symbol, calculate_bbands, calculate_rsi, calculate_macd
from core.constants import load_sp500_symbols, TEST_SYMBOLS
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
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
ch_font = FontProperties(fname='C:/Windows/Fonts/msjh.ttc')  # Windows 微軟正黑體路徑
import re

#print(load_sp500_symbols()) 有抓到S&P500清單

def nan_to_none(obj):
    if isinstance(obj, float) and np.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_to_none(v) for v in obj]
    return obj

def stock_api(request, symbol):
    symbol = symbol.upper()
    period = '10y'
    stock_data = fetch_stock_data([symbol], period='2y')
    #print(stock_data)

    holding_days = [5, 10, 15, 20]

    historical_data = fetch_historical_data(symbol,period=period,holding_days=holding_days)

    if historical_data is None or historical_data.empty:
        return JsonResponse({"error": "無 RSI 資料或事件"}, status=400)
    
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
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Upper'] = bb.bollinger_hband()

    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd().squeeze()
    df['MACD_signal'] = macd.macd_signal().squeeze()
    df['MACD_hist'] = macd.macd_diff().squeeze()

    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

    # 策略信號
    df['BB_Lower_Cross'] = ((df['Close'].shift(1) < df['BB_Lower'].shift(1)) & (df['Close'] >= df['BB_Lower']))
    df['MACD_GC'] = (df['MACD'].shift(1) < df['MACD_signal'].shift(1)) & (df['MACD'] >= df['MACD_signal'])
    df['RSI_Cross30'] = (df['RSI'].shift(1) < 30) & (df['RSI'] >= 30)

    # ----------- 畫圖 -----------
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios':[3,1.2,1]})

    
    dates = df.index
    print(df.index)
    print(type(df.index))
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
    ax.bar(dates[up], df['Close'][up]-df['Open'][up], candle_w, bottom=df['Open'][up], color='red', edgecolor='k', label='Up')
    ax.bar(dates[down], df['Close'][down]-df['Open'][down], candle_w, bottom=df['Open'][down], color='green', edgecolor='k', label='Down')
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
    ax = axes[1]
    pos = df['MACD_hist'] > 0
    neg = ~pos
    ax.bar(dates[pos], df.loc[pos, 'MACD_hist'], color='green', alpha=0.85, label='MACD Hist +')
    ax.bar(dates[neg], df.loc[neg, 'MACD_hist'], color='red', alpha=0.85, label='MACD Hist -')
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
    ax.set_title("每個獲利目標的達標率(%) vs 天數", fontproperties='Noto Sans CJK TC')
    ax.set_xlabel("持有天數", fontproperties='Noto Sans CJK TC')
    ax.set_ylabel("目標獲利率 (%)", fontproperties='Noto Sans CJK TC')

    # 儲存為 base64 圖片
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64_heat = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()


    
    df['Date'] = df.index.strftime('%Y-%m-%d')

    # 加入各項技術指標欄位
    df['upper_band'], df['lower_band'] = calculate_bbands(df)
    df['rsi'] = calculate_rsi(df,False)
    df['macd'], df['signal'], df['hist'] = calculate_macd(df['Close'])

    df = df.where(pd.notnull(df), None)

    price_data = df.to_dict(orient='records')
    price_data = nan_to_none(price_data)  # 這步最重要！
    
    return JsonResponse({
        "symbol": symbol,
        'heatmap': img_base64_heat,
        'techmap': img_base64_tech,
        "event_count": len(historical_data),
        'company_name': stock_data[symbol]['info'].get('longName') or stock_data['info'].get('shortName'),
        'sector': stock_data[symbol]['info'].get('sector'),
        'industry': stock_data[symbol]['info'].get('industry'),
        'market_cap': stock_data[symbol]['info'].get('marketCap'),
        'price_to_book': stock_data[symbol]['info'].get('priceToBook'),
        'price_to_sales': stock_data[symbol]['info'].get('priceToSalesTrailing12Months'),
        'trailing_eps': stock_data[symbol]['info'].get('trailingEps'),
        'forward_eps': stock_data[symbol]['info'].get('forwardEps'),
        'trailingPE': stock_data[symbol]['info'].get('trailingPE'),
        'forwardPE': stock_data[symbol]['info'].get('forwardPE'),
        'revenue_growth': stock_data[symbol]['info'].get('revenueGrowth'),
        'gross_margins': stock_data[symbol]['info'].get('grossMargins'),
        'operating_margins': stock_data[symbol]['info'].get('operatingMargins'),
        'profit_margins': stock_data[symbol]['info'].get('profitMargins'),
        'return_on_assets': stock_data[symbol]['info'].get('returnOnAssets'),
        'return_on_equity': stock_data[symbol]['info'].get('returnOnEquity'),
        'dividend_rate': stock_data[symbol]['info'].get('dividendRate'),
        'dividend_yield': stock_data[symbol]['info'].get('dividendYield'),
        'payout_ratio': stock_data[symbol]['info'].get('payoutRatio'),
        'total_debt': stock_data[symbol]['info'].get('totalDebt'),
        'debt_to_equity': stock_data[symbol]['info'].get('debtToEquity'),
        'free_cashflow': stock_data[symbol]['info'].get('freeCashflow'),
        'operating_cashflow': stock_data[symbol]['info'].get('operatingCashflow'),
        'averageVolume': stock_data[symbol]['info'].get('averageVolume'),
        'website': stock_data[symbol]['info'].get('website'),
        'price_data': price_data,
    })

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

def get_raw_data():
    return load_or_fetch_stock_data(load_sp500_symbols())

@login_required
def clear_cache_view(request):
    print('clear_cache_view');
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
