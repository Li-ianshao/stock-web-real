from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
#from stocks.utils.fetcher import fetch_stock_data
#from stocks.utils.screener import filter_bband_stocks, filter_dividend_stocks, filter_rsi_alert_stocks, filter_macd_cross_stocks, filter_big_drop_stocks
#from stocks.constants import TEST_SYMBOLS


#raw_data  = fetch_stock_data(TEST_SYMBOLS)


#print(filtered_data)

@login_required
def tab_dividend_view(request):
    #filtered_data = filter_dividend_stocks(raw_data)
    context = {
        'stocks': [],#filtered_data,
        'column_headers': ['代碼', '收盤價', '配息日', '配息', '此次配息率', '殖利率', '當日漲跌幅', '一年最低價', '一年最高價', 'RSI', 'volume_Delta'],
        'alert_change': 5,
        'rsi_high_warn': 70,
        'rsi_high_soft': 60,
        'rsi_low_soft': 40,
        'rsi_low_warn': 30,
        'alert_volume': 100,
    }
    return render(request, 'core/tab_dividend.html', context)
'''

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
    return render(request, 'stocks/tab_rsi.html', context)

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
    return render(request, 'stocks/tab_bband.html', context)

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
    return render(request, 'stocks/tab_macd.html', context)

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
    return render(request, 'stocks/tab_drop.html', context)

@login_required
def stock_detail_view(request, symbol):
    return render(request, 'stocks/detail.html', {'symbol': symbol})

'''