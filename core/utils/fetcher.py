import os
import pickle
import yfinance as yf
import datetime

# 預設快取檔路徑
CACHE_FILE = 'cache/sp500_data.pico'
CACHE_DIR = 'cache/'

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
    
    with open("cache/last_updated.txt", "w") as f:
            f.write(str(datetime.datetime.now()))

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
