import base64
import io
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 
import json
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
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
    stock_data = fetch_stock_data([symbol], period='1y')
    print(stock_data)

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
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlGnBu", ax=ax)
    ax.set_title("每個獲利目標的達標率(%) vs 天數", fontproperties='Microsoft JhengHei')
    ax.set_xlabel("持有天數", fontproperties='Microsoft JhengHei')
    ax.set_ylabel("目標獲利率 (%)", fontproperties='Microsoft JhengHei')

    # 儲存為 base64 圖片
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()


    df = stock_data[symbol]['history'].copy()
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
        'heatmap': img_base64,
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
