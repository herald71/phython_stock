import FinanceDataReader as fdr
import time
import os

tickers = ['MMM', 'AOS', 'ABT', 'ABBV', 'ACN', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
print(f"Testing {len(tickers)} tickers...")

for ticker in tickers:
    try:
        print(f"Downloading {ticker}...", end=" ", flush=True)
        df = fdr.DataReader(ticker, '2025-01-01')
        print(f"Success ({len(df)} rows)")
    except Exception as e:
        print(f"FAILED: {e}")
    time.sleep(0.1)
