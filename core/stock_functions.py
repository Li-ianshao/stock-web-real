import pandas as pd
import yfinance as yf
import ta
import json
import bs4 as bs
from datetime import timedelta, date
import datetime
import time
import requests
from requests.adapters import HTTPAdapter, Retry
from io import StringIO
import matplotlib.pyplot as plt

def get_sp500_tickers(as_yfinance: bool = True, timeout: int = 15) -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    sess = requests.Session()
    sess.mount("https://", HTTPAdapter(max_retries=Retry(
        total=5, backoff_factor=0.3,
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )))
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = sess.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()

    # ✅ 用 StringIO 包住 resp.text，避免 FutureWarning
    tables = pd.read_html(StringIO(r.text), attrs={"id": "constituents"})  # 需要 lxml 解析器
    if not tables:
        raise RuntimeError("Constituents table not found.")
    df = tables[0]

    tickers = (
        df["Symbol"].astype(str).str.strip().tolist()
    )
    if as_yfinance:
        tickers = [t.replace(".", "-") for t in tickers]  # BRK.B -> BRK-B
    return tickers

def getAristocrats(as_yf=True):
    url = "https://en.wikipedia.org/wiki/S%26P_500_Dividend_Aristocrats"

    # 用帶 UA 的 session + 重試
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    })
    sess.mount("https://", HTTPAdapter(max_retries=Retry(
        total=5, backoff_factor=0.3,
        status_forcelist=[403,429,500,502,503,504],
        allowed_methods=["GET"]
    )))

    r = sess.get(url, timeout=15)
    r.raise_for_status()

    # 用 StringIO 包裝字串給 read_html
    tables = pd.read_html(StringIO(r.text))   # 需要 pip install lxml
    # 找到含有 Symbol/Ticker 欄位且至少幾十列的表
    df = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any(("symbol" in c or "ticker" in c) for c in cols) and len(t) > 20:
            df = t; break
    if df is None:
        raise RuntimeError("Ticker table not found (page layout may have changed).")

    # 取出欄名
    col = next(c for c in df.columns if "Symbol" in str(c) or "Ticker" in str(c))
    tickers = (
        df[col].astype(str).str.strip().str.replace("\u200b","", regex=False).tolist()
    )
    if as_yf:
        tickers = [t.replace(".", "-") for t in tickers]  # BRK.B -> BRK-B
    return tickers

def getData(ticker_list):
	data = yf.download(
		tickers = ticker_list,
		period = '6mo',
		interval = '1d',
		group_by = 'ticker',
		auto_adjust = False,
		prepost = False,
		threads = True
	)
	data = data.T
	return data

def get_sp100_tickers(as_yfinance: bool = True, fallback_if_fail: bool = True) -> list[str]:
    """
    抓取 S&P 100 成分股，回傳 list。
    - as_yfinance=True：把 '.' 轉成 '-'（BRK.B -> BRK-B），方便 yfinance。
    - fallback_if_fail=True：抓取失敗時回傳內建備用清單（不一定剛好 100 檔）。
    """
    url = "https://en.wikipedia.org/wiki/S%26P_100"

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1,
                    status_forcelist=[403, 429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        resp = session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10
        )
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))

        df = None
        for t in tables:
            # 🔑 把欄位名稱全部轉成 str
            cols = [str(c).lower() for c in t.columns]
            if any("symbol" in c or "ticker" in c for c in cols):
                df = t
                break
        if df is None:
            raise RuntimeError("No SP100 table found.")

        # 找到 ticker 欄位名
        col_name = next(c for c in df.columns if "symbol" in str(c).lower() or "ticker" in str(c).lower())

        tickers = (
            df[col_name]
            .astype(str)
            .str.strip()
            .tolist()
        )
        tickers = sorted({t for t in tickers if t and t.lower() != "nan"})

        if as_yfinance:
            tickers = [t.replace(".", "-") for t in tickers]

        return tickers

    except Exception as e:
        print(f"抓取失敗: {e}")
        if fallback_if_fail:
            return ["AAPL", "MSFT", "AMZN", "GOOGL", "BRK-B", "JNJ"]  # 備用
        else:
            raise

def rsiAndDividends():
	data = getData(sp500)
	data = data.sort_index()

	rsi_crossover = []
	rsi_below30 = []
	div = []
	drops = []
	alerts = []
	errors = []

	for ticker in sp500:
		ticker2 = yf.Ticker(ticker)
		df_2 = ticker2.history(period='1y')

		if ticker in aristocrats:
			aris = True
		else:
			aris = False

		if ticker in sp100:
			snp100 = True
		else:
			snp100 = False

		info = ticker2.info
		
		name = info.get('longName')
		industry = info.get('industry', 'Unknown')

		# 找出 RSI Crossover 30 的股票
		try:
			#print(ticker)
			df = data.loc[(ticker,),].T

			if df.empty or len(df) < 20:
				continue

			df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi().squeeze()
			df = df.dropna()
		
			if len(df) >= 2:
				if (df['RSI'].iloc[-2] < 30) and (df['RSI'].iloc[-1] >= 30):
					rsi_crossover.append({
						"Ticker": ticker,
						'Name':name,
						'Industry': industry,
						'RSI': round(df['RSI'].iloc[-1]),
						'SNP100': str(snp100),
						"股息貴族": str(aris)
						})
				if (df['RSI'].iloc[-1] < 30):
					rsi_below30.append({
						"Ticker": ticker,
						'Name':name,
						'Industry': industry,
						'RSI': round(df['RSI'].iloc[-1]),
						'SNP100': str(snp100),
						"股息貴族": str(aris)
						})


						

			# 檢查該檔股價是否低於警示值
			close = round(df['Close'].iloc[-1],2) 
            
			if ticker in alert:
				try:
					if close < alert[ticker]:
						alerts.append({
							"Ticker": ticker,
							'Name':name,
							'Industry': industry,
							'SNP100': str(snp100),
							"current": close,
							"target": alert[ticker],
							"status": "⚠ 低於目標",
							"股息貴族": str(aris)
						})
				except Exception as e:
					errors.append(ticker)

			# Drops, 過去兩個月內最大跌幅超過 30% 的股票
			df_t = df.tail(60)
			p_max = df_t['Close'].max()
			drop = round((p_max - close) / p_max * 100,2)

			if drop >= 25 and snp100:
				drops.append({
					'Ticker': ticker,
					'Name': name,
					'Industry': industry,
					'最大跌幅': str(drop) + '%',
					'SNP100': str(snp100),
					'股息貴族': str(aris)
				})

		except Exception as e:
			print(f"{ticker} error: {e} at block #1")

		# 找出 dividend dates and yields
		try:
			'''
			ticker2 = yf.Ticker(ticker)
			df_2 = ticker2.history(period='1y')

			if ticker in aristocrats:
				aris = True
			else:
				aris = False

			info = ticker2.info
			name = info.get('longName')
			industry = info['industry']
			'''

			div_pay_date = info.get('dividendDate','')  # 過去的付息日期
			
			if div_pay_date != '':  # 只處理有付息日期的股票
				div_pay_date = datetime.datetime.fromtimestamp(div_pay_date, datetime.UTC).strftime('%Y-%m-%d')
				yields = round(info['dividendYield'],2)
				#print(f"yields={yields}")

				exDividendDate = info.get('exDividendDate','') # 最近配息日期
				exDividendDate = datetime.datetime.fromtimestamp(exDividendDate, datetime.UTC).strftime('%Y-%m-%d')

				if exDividendDate > date.today().strftime("%Y-%m-%d") and yields > 4.0:
					div.append({
						'Ticker': ticker,
						'Name': name,
						'industry': industry,
						'Div_Date': exDividendDate,
						'Yields': round(yields, 2), #str(round(yields, 2)) + '%',
						'SNP100': str(snp100),
						'股息貴族':str(aris)
					})

		except Exception as e:
			#print(f"{ticker} error: {e} at block #2")
			errors.append(ticker)

	

	rsi_crossover = sorted(rsi_crossover, key=lambda d: d['RSI'])
	div = sorted(div, key=lambda d: d['Div_Date']) # sort list of dictionaries
	drops = sorted(drops, key=lambda d: d['最大跌幅'], reverse=True)

	my_dict = {"RSI_Xover_30": rsi_crossover}
	my_dict["RSI_Below30"] = rsi_below30
	my_dict["dividends"] = div
	my_dict['drops'] = drops
	my_dict['alerts'] = alerts


	json_str = json.dumps(my_dict, ensure_ascii=False, indent=2)

	#print(json_str)
	try:
		url = "https://stock-web-real-cfcydzdxg3c0hnck.centralus-01.azurewebsites.net/core/api/stockdata/"
		resp = requests.post(url, json=my_dict)  # ← 用 json= 而不是 data=
		# resp = requests.post(
		# 	url,
		# 	data=json_str,  # 轉換成 JSON String
		# 	headers={"Content-Type": "application/json"}
		# )
		print(resp)
		print("status:", resp.status_code)
		print("reason:", resp.reason)
		print("redirected?", bool(resp.is_redirect), "history:", [h.status_code for h in resp.history])
		print("resp headers:", resp.headers)
		print("resp text:", resp.text[:500])
		print('\n\nData sent @ '+ str(datetime.datetime.now()))
		#print(my_dict)
		print(json_str)
	except Exception as e:
			print(f"send error: {e}")

def get_dividend_history(ticker_symbol):
	

    # 1. 取得股票資料
    ticker = yf.Ticker(ticker_symbol)
    
    # 計算十年前的日期
    start_date = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    # 2. 獲取配息歷史
    dividends = ticker.dividends
    
    if dividends.empty:
        print(f"找不到 {ticker_symbol} 的配息紀錄。")
        return
    
    # 篩選近十年的數據
    dividends = dividends[dividends.index >= start_date]
    
    # 3. 資料整理：按季度（Quarter）加總
    # 這樣可以處理那些一年多次配息或不定期配息的情況
    quarterly_div = dividends.resample('Q').sum()
    
    # 格式化日期索引，方便繪圖顯示 (例如: 2023-Q1)
    quarterly_div.index = quarterly_div.index.to_period('Q')
    
    # 4. 輸出文字數據
    print(f"\n--- {ticker_symbol} 近十年每季配息金額 ---")
    print(quarterly_div.tail(10)) # 顯示最近 10 季
    
    # 5. 繪製統計圖
    plt.figure(figsize=(12, 6))
    quarterly_div.plot(kind='bar', color='skyblue', edgecolor='navy')
    
    plt.title(f'Quarterly Dividend History: {ticker_symbol} (Past 10 Years)')
    plt.xlabel('Quarter')
    plt.ylabel('Dividend Amount (USD)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plt.savefig('Img.png')

    return 'Img.png'

def nan_to_none(obj):
    if isinstance(obj, float) and np.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_to_none(v) for v in obj]
    return obj

