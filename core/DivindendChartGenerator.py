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
    print("正在繪製"+ticker_symbol+"的統計圖")
    # 1. 取得股票資料
    ticker = yf.Ticker(ticker_symbol)
    start_date = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    # 2. 獲取配息歷史
    dividends = ticker.dividends
    if dividends.empty or dividends[dividends.index >= start_date].empty:
        return None
    
    # 3. 資料整理：篩選並按季度加總
    dividends = dividends[dividends.index >= start_date]
    quarterly_div = dividends.resample('Q').sum()
    
    # 4. 繪圖 (使用 Agg 後端以防在伺服器環境報錯)
    plt.switch_backend('Agg') 
    plt.figure(figsize=(10, 5), facecolor='#f8fafc') # 使用您喜歡的淡色背景
    
    # 繪製長條圖
    ax = quarterly_div.plot(kind='bar', color='#3b82f6', edgecolor='#1d4ed8', width=0.8)
    
    plt.title(f'{ticker_symbol} - 10 Year Quarterly Dividend', fontsize=14, fontweight='bold', color='#1e293b')
    plt.xlabel('Quarter', fontsize=10)
    plt.ylabel('Amount (USD)', fontsize=10)
    
    # 簡化 X 軸標籤，避免太擁擠
    tick_labels = [str(p) for p in quarterly_div.index.to_period('Q')]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation=45, fontsize=8)
    
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    # 5. 將圖片轉為 Base64 字串
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close() # 務必關閉以釋放記憶體
    
    return image_base64