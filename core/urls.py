from django.urls import path
from . import views

urlpatterns = [
    path('dividend/', views.tab_dividend_view, name='tab_dividend'),
    path('clear-cache/', views.clear_cache_view, name='clear_cache'),
    path('rsi/', views.tab_rsi_view, name='tab_rsi'),
    path('bband/', views.tab_bband_view, name='tab_bband'),
    path('macd/', views.tab_macd_view, name='tab_macd'),
    path('drop/', views.tab_drop_view, name='tab_drop'),
    path('rsicross/', views.stock_input_view, name='stock_input_view'),
    path('api/stock/<str:symbol>/', views.stock_api, name='stock_api'),
    path('<str:symbol>/', views.stock_detail_view, name='stock_detail'),  # 詳細頁
]
