import pandas as pd

# 從 Wikipedia 擷取 S&P 500 股票代碼
SP500_SYMBOLS = None

TEST_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'JNJ',
    'KO', 'XOM', 'JPM', 'PG', 'NVDA', 'CCI', 'WU', 'TTE', 'BEN', 'CRWD', 'KSS'
]

def load_sp500_symbols():
    global SP500_SYMBOLS
    if SP500_SYMBOLS is None:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(url)[0]
        SP500_SYMBOLS = df['Symbol'].tolist()
    return SP500_SYMBOLS