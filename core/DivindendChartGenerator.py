# import yfinance as yf
# import pandas as pd
# import matplotlib.pyplot as plt
# from datetime import datetime, timedelta

# def get_dividend_history(ticker_symbol):
#     # 1. 取得股票資料
#     ticker = yf.Ticker(ticker_symbol)
    
#     # 計算十年前的日期
#     start_date = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    
#     # 2. 獲取配息歷史
#     dividends = ticker.dividends
    
#     if dividends.empty:
#         print(f"找不到 {ticker_symbol} 的配息紀錄。")
#         return
    
#     # 篩選近十年的數據
#     dividends = dividends[dividends.index >= start_date]
    
#     # 3. 資料整理：按季度（Quarter）加總
#     # 這樣可以處理那些一年多次配息或不定期配息的情況
#     quarterly_div = dividends.resample('Q').sum()
    
#     # 格式化日期索引，方便繪圖顯示 (例如: 2023-Q1)
#     quarterly_div.index = quarterly_div.index.to_period('Q')
    
#     # 4. 輸出文字數據
#     print(f"\n--- {ticker_symbol} 近十年每季配息金額 ---")
#     print(quarterly_div.tail(10)) # 顯示最近 10 季
    
#     # 5. 繪製統計圖
#     plt.figure(figsize=(12, 6))
#     quarterly_div.plot(kind='bar', color='skyblue', edgecolor='navy')
    
#     plt.title(f'Quarterly Dividend History: {ticker_symbol} (Past 10 Years)')
#     plt.xlabel('Quarter')
#     plt.ylabel('Dividend Amount (USD)')
#     plt.xticks(rotation=45)
#     plt.grid(axis='y', linestyle='--', alpha=0.7)
#     plt.tight_layout()
    
#     plt.show()

# # 使用範例：輸入美股代號 (例如: AAPL, MSFT, O)
# target_ticker = input("請輸入股票代號 (例如 AAPL): ").upper()
# get_dividend_history(target_ticker)

import io
import base64
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta

def get_dividend_chart_base64(ticker_symbol):
    """
    不再回傳圖片，而是回傳 D3.js 需要的 JSON 數據格式
    """
    ticker = yf.Ticker(ticker_symbol)
    # 計算 10 年前的日期
    start_date = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    dividends = ticker.dividends
    if dividends.empty or dividends[dividends.index >= start_date].empty:
        return [] # 回傳空列表
    
    # 篩選並按季度加總
    dividends = dividends[dividends.index >= start_date]
    quarterly_div = dividends.resample('Q').sum()
    
    # 整理成 D3 易讀的格式: [{"date": "2023Q1", "amount": 0.5}, ...]
    data_points = []
    for index, value in quarterly_div.items():
        data_points.append({
            "date": str(index.to_period('Q')), # 轉為 '2023Q1' 格式
            "amount": round(float(value), 4) # 確保是數字且取到小數點後四位
        })
    
    return data_points