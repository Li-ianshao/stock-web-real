from datetime import datetime
import pandas as pd
import time


def calculate_bbands(hist, window=20, num_std=2):
    # 計算布林通道（20日平均線 + 上下2個標準差）
    hist['bb_middle'] = hist['Close'].rolling(window).mean()
    hist['bb_std'] = hist['Close'].rolling(window).std()
    hist['bb_upper'] = hist['bb_middle'] + num_std * hist['bb_std']
    hist['bb_lower'] = hist['bb_middle'] - num_std * hist['bb_std']
    return hist['bb_upper'], hist['bb_lower']

def calculate_rsi(hist):
    # RSI 計算（14日）
    delta = hist["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean().iloc[-1]
    avg_loss = loss.rolling(window=14).mean().iloc[-1]
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = round(100 - (100 / (1 + rs)), 2) if avg_gain and avg_loss else 'N/A'
    return rsi

def calculate_macd(close_series, fast=12, slow=26, signal=9):
    ema_fast = close_series.ewm(span=fast).mean()
    ema_slow = close_series.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line

def filter_dividend_stocks(raw_data, yield_threshold=4, within_days=90):
    """
    從原始股票資料中篩選殖利率高於指定門檻的股票
    :param raw_data: 來自 pickle 檔案的 {symbol: {'info': dict, 'history': DataFrame}}
    :param yield_threshold: 例如 0.04 表示殖利率 > 4%
    :return: list of dicts，供 base.html 表格使用
    """
    result = []

    now_ts = int(time.time())
    time_limit = now_ts + (within_days * 86400)  # 3 個月內

    for symbol, content in raw_data.items():
        try:
            info = content.get('info', {})
            hist = content.get('history')

            if hist is None or hist.empty:
                continue

            dividend_yield = info.get('dividendYield') or 0
            print(f"{symbol} 殖利率: {dividend_yield}")
            if dividend_yield < yield_threshold:
                continue

            # 配息日
            ex_div_ts = info.get("exDividendDate", None)
            ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d') if ex_div_ts else 'N/A'

            if not ex_div_ts or not isinstance(ex_div_ts, (int, float)):
                continue  # 無配息日
            if not (now_ts <= ex_div_ts <= time_limit):
                continue  # 配息時間不在未來 3 個月內

            # 收盤價
            close = round(hist["Close"][-1],2) if not hist.empty else 'N/A'


            # 當日漲跌幅 %
            try:
                price_change = round(((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100, 2)
            except:
                price_change = 'N/A'

            # volume delta
            try:
                volume = info.get("volume", 0)
                avg_volume = info.get("averageVolume", 0)
                volume_delta = round((volume/avg_volume)*100,2)
            except:
                volume_delta = 'N/A'

            
            # 每股配息
            dividend = info.get("lastDividendValue", 'N/A')

            # 此次配息率 = 配息 ÷ 收盤價
            try:
                dividend_ratio = round(float(dividend) / float(close) * 100, 2)
            except:
                dividend_ratio = 'N/A'


            result.append({
                "symbol": symbol,
                "close": close,
                "ex_dividend_date": ex_div_date,
                "dividend": dividend,
                "dividend_ratio": dividend_ratio,
                "yield": dividend_yield,
                "price_change": price_change,
                "year_low": info.get("fiftyTwoWeekLow", 'N/A'),
                "year_high": info.get("fiftyTwoWeekHigh", 'N/A'),
                "rsi": calculate_rsi(hist),
                "volume_delta": volume_delta,
            })
        except Exception as e:
            result.append({
                'symbol': symbol,
                'error': str(e)
            })

    return result

def filter_rsi_alert_stocks(raw_data, rsi_low=30, rsi_high=70):
    result = []
    for symbol, content in raw_data.items():
        try:
            info = content.get('info', {})
            hist = content.get('history')
            if hist is None or hist.empty:
                continue

            rsi = calculate_rsi(hist)

            if rsi < rsi_low or rsi > rsi_high:
                
                # 收盤價
                close = round(hist["Close"][-1],2) if not hist.empty else 'N/A'

                # 當日漲跌幅 %
                try:
                    price_change = round(((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100, 2)
                except:
                    price_change = 'N/A'

                # volume delta
                try:
                    volume = info.get("volume", 0)
                    avg_volume = info.get("averageVolume", 0)
                    volume_delta = round((volume/avg_volume)*100,2)
                except:
                    volume_delta = 'N/A'

                # 配息日
                ex_div_ts = info.get("exDividendDate", None)
                ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d') if ex_div_ts else 'N/A'
                
                # 每股配息
                dividend = info.get("lastDividendValue", 'N/A')

                # 此次配息率 = 配息 ÷ 收盤價
                try:
                    dividend_ratio = round(float(dividend) / float(close) * 100, 2)
                except:
                    dividend_ratio = 'N/A'

                # 殖利率（年度總配息 ÷ 價格）
                dividend_yield = info.get("dividendYield", 0)

                result.append({
                    "symbol": symbol,
                    "close": close,
                    "ex_dividend_date": ex_div_date,
                    "dividend": dividend,
                    "dividend_ratio": dividend_ratio,
                    "yield": dividend_yield,
                    "price_change": price_change,
                    "year_low": info.get("fiftyTwoWeekLow", 'N/A'),
                    "year_high": info.get("fiftyTwoWeekHigh", 'N/A'),
                    "rsi": rsi,
                    "volume_delta": volume_delta,
                })
        except Exception as e:
            print(f"⚠️ RSI 選股錯誤 {symbol}: {e}")
            continue

    return result


def filter_bband_stocks(raw_data):
    result = []

    for symbol, content in raw_data.items():
        try:
            hist = content.get('history')
            info = content.get('info', {})
            if hist is None or hist.empty or len(hist) < 20:
                continue

            upper, lower = calculate_bbands(hist)

            latest_high = hist['High'].iloc[-1]
            latest_low = hist['Low'].iloc[-1]
            upper_latest = upper.iloc[-1]
            lower_latest = lower.iloc[-1]

            if pd.isna(upper_latest) or pd.isna(lower_latest):
                continue

            if latest_high > upper_latest or latest_low < lower_latest:
                # 收盤價
                close = round(hist["Close"][-1],2) if not hist.empty else 'N/A'

                # 當日漲跌幅 %
                try:
                    price_change = round(((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100, 2)
                except:
                    price_change = 'N/A'

                # volume delta
                try:
                    volume = info.get("volume", 0)
                    avg_volume = info.get("averageVolume", 0)
                    volume_delta = round((volume/avg_volume)*100,2)
                except:
                    volume_delta = 'N/A'

                # 配息日
                ex_div_ts = info.get("exDividendDate", None)
                ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d') if ex_div_ts else 'N/A'
                
                # 每股配息
                dividend = info.get("lastDividendValue", 'N/A')

                # 此次配息率 = 配息 ÷ 收盤價
                try:
                    dividend_ratio = round(float(dividend) / float(close) * 100, 2)
                except:
                    dividend_ratio = 'N/A'

                # 殖利率（年度總配息 ÷ 價格）
                dividend_yield = info.get("dividendYield", 0)

                result.append({
                    "symbol": symbol,
                    "close": close,
                    "ex_dividend_date": ex_div_date,
                    "dividend": dividend,
                    "dividend_ratio": dividend_ratio,
                    "yield": dividend_yield,
                    "price_change": price_change,
                    "year_low": info.get("fiftyTwoWeekLow", 'N/A'),
                    "year_high": info.get("fiftyTwoWeekHigh", 'N/A'),
                    "rsi": calculate_rsi(hist),
                    "volume_delta": volume_delta,
                })
        except Exception as e:
            print(f"⚠️ BBand 選股錯誤 {symbol}: {e}")
            continue

    return result


def filter_macd_cross_stocks(raw_data):
    result = []

    for symbol, content in raw_data.items():
        try:
            hist = content.get('history')
            info = content.get('info', {})
            if hist is None or hist.empty or len(hist) < 30:
                continue

            close = hist['Close']
            macd, signal = calculate_macd(close)

            # 檢查最近兩日是否形成黃金交叉
            if macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
                
                # 收盤價
                close = round(hist["Close"][-1],2) if not hist.empty else 'N/A'

                # 當日漲跌幅 %
                try:
                    price_change = round(((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100, 2)
                except:
                    price_change = 'N/A'

                # volume delta
                try:
                    volume = info.get("volume", 0)
                    avg_volume = info.get("averageVolume", 0)
                    volume_delta = round((volume/avg_volume)*100,2)
                except:
                    volume_delta = 'N/A'

                # 配息日
                ex_div_ts = info.get("exDividendDate", None)
                ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d') if ex_div_ts else 'N/A'
                
                # 每股配息
                dividend = info.get("lastDividendValue", 'N/A')

                # 此次配息率 = 配息 ÷ 收盤價
                try:
                    dividend_ratio = round(float(dividend) / float(close) * 100, 2)
                except:
                    dividend_ratio = 'N/A'

                # 殖利率（年度總配息 ÷ 價格）
                dividend_yield = info.get("dividendYield", 0)

                result.append({
                    "symbol": symbol,
                    "close": close,
                    "ex_dividend_date": ex_div_date,
                    "dividend": dividend,
                    "dividend_ratio": dividend_ratio,
                    "yield": dividend_yield,
                    "price_change": price_change,
                    "year_low": info.get("fiftyTwoWeekLow", 'N/A'),
                    "year_high": info.get("fiftyTwoWeekHigh", 'N/A'),
                    "rsi": calculate_rsi(hist),
                    "volume_delta": volume_delta,
                })
        except Exception as e:
            print(f"⚠️ MACD 選股錯誤 {symbol}: {e}")
            continue

    return result

def filter_big_drop_stocks(raw_data, threshold=-30):
    result = []

    for symbol, content in raw_data.items():
        try:
            hist = content.get('history')
            info = content.get('info', {})
            if hist is None or hist.empty or len(hist) < 30:
                continue

            close_series = hist['Close']
            recent_close = close_series.iloc[-1]
            lowest_close = close_series.iloc[-21:].min()

            drop_pct = round((lowest_close - recent_close) / lowest_close * 100, 2)

            if drop_pct <= threshold:
                
                # 收盤價
                close = round(hist["Close"][-1],2) if not hist.empty else 'N/A'

                # 當日漲跌幅 %
                try:
                    price_change = round(((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100, 2)
                except:
                    price_change = 'N/A'

                # volume delta
                try:
                    volume = info.get("volume", 0)
                    avg_volume = info.get("averageVolume", 0)
                    volume_delta = round((volume/avg_volume)*100,2)
                except:
                    volume_delta = 'N/A'

                # 配息日
                ex_div_ts = info.get("exDividendDate", None)
                ex_div_date = datetime.fromtimestamp(ex_div_ts).strftime('%Y-%m-%d') if ex_div_ts else 'N/A'
                
                # 每股配息
                dividend = info.get("lastDividendValue", 'N/A')

                # 此次配息率 = 配息 ÷ 收盤價
                try:
                    dividend_ratio = round(float(dividend) / float(close) * 100, 2)
                except:
                    dividend_ratio = 'N/A'

                # 殖利率（年度總配息 ÷ 價格）
                dividend_yield = info.get("dividendYield", 0)

                result.append({
                    "symbol": symbol,
                    "close": close,
                    "ex_dividend_date": ex_div_date,
                    "dividend": dividend,
                    "dividend_ratio": dividend_ratio,
                    "yield": dividend_yield,
                    "price_change": price_change,
                    "year_low": info.get("fiftyTwoWeekLow", 'N/A'),
                    "year_high": info.get("fiftyTwoWeekHigh", 'N/A'),
                    "rsi": calculate_rsi(hist),
                    "volume_delta": volume_delta,
                })

        except Exception as e:
            print(f"⚠️ Drop 選股錯誤 {symbol}: {e}")
            continue

    return result