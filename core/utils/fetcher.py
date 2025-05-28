import os
import pickle
import yfinance as yf

# 預設快取檔路徑
CACHE_FILE = 'cache/sp500_data.pico'


def fetch_stock_data(symbols, period='3mo', interval='1d'):
    """
    從 yfinance 抓取多支股票的歷史價格與 info
    :return: {symbol: {'history': DataFrame, 'info': dict}}
    """
    result = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                continue

            result[symbol] = {
                'history': hist,
                'info': ticker.info
            }

        except Exception as e:
            print(f"⚠️ 抓取 {symbol} 失敗：{e}")
            continue

    return result


def load_or_fetch_stock_data(symbols, period='3mo', interval='1d', cache_path=CACHE_FILE, force_reload=False):
    """
    嘗試從本地讀取快取資料；若無則從 yfinance 抓取並寫入 pickle 快取
    """
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    if not force_reload and os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                print(f"✅ 從快取載入資料：{cache_path}")
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️ 無法讀取快取，重新抓取：{e}")

    # 抓取新資料
    print("⏬ 開始從 yfinance 抓取資料...")
    data = fetch_stock_data(symbols, period=period, interval=interval)

    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 資料已快取到：{cache_path}")
    except Exception as e:
        print(f"⚠️ 無法寫入快取：{e}")

    return data
