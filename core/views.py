from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 
import json
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.utils.fetcher import fetch_stock_data, load_or_fetch_stock_data, clear_all_pickles
from core.utils.screener import filter_bband_stocks, filter_dividend_stocks, filter_rsi_alert_stocks, filter_macd_cross_stocks, filter_big_drop_stocks, get_stock_data_by_symbol, calculate_bbands, calculate_rsi, calculate_macd
from core.constants import load_sp500_symbols, TEST_SYMBOLS
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
import os
from datetime import datetime

#print(load_sp500_symbols()) 有抓到S&P500清單

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
