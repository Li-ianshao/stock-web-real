from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.utils.fetcher import fetch_stock_data, load_or_fetch_stock_data, clear_all_pickles
from core.utils.screener import filter_bband_stocks, filter_dividend_stocks, filter_rsi_alert_stocks, filter_macd_cross_stocks, filter_big_drop_stocks, get_stock_data_by_symbol
from core.constants import load_sp500_symbols, TEST_SYMBOLS
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse

#print(load_sp500_symbols()) 有抓到S&P500清單

raw_data  = load_or_fetch_stock_data(load_sp500_symbols())

@login_required
def clear_cache_view(request):
    print('clear_cache_view');
    clear_all_pickles()
    return redirect('tab_dividend')  # 或跳回首頁頁籤

@login_required
def tab_dividend_view(request):
    filtered_data = filter_dividend_stocks(raw_data)
    context = {
        'stocks': filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_dividend.html', context)


@login_required
def tab_rsi_view(request):
    filtered_data = filter_rsi_alert_stocks(raw_data)
    context = {
        'stocks': filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_rsi.html', context)

@login_required
def tab_bband_view(request):
    filtered_data = filter_bband_stocks(raw_data)
    context = {
        'stocks': filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_bband.html', context)

@login_required
def tab_macd_view(request):
    filtered_data = filter_macd_cross_stocks(raw_data)
    context = {
        'stocks': filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_macd.html', context)

@login_required
def tab_drop_view(request):
    filtered_data = filter_big_drop_stocks(raw_data)
    context = {
        'stocks': filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_drop.html', context)

@login_required
def stock_detail_view(request, symbol):
    previous_url = request.META.get('HTTP_REFERER')
    if not url_has_allowed_host_and_scheme(url=previous_url, allowed_hosts={request.get_host()}):
        previous_url = reverse('tab_dividend')

    stock_data = get_stock_data_by_symbol(symbol, raw_data)

    return render(request, 'core/detail.html', {
        'symbol': symbol,
        'previous_url': previous_url,
        'stock_data':stock_data,
    })
