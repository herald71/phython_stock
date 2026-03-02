import FinanceDataReader as fdr
import yfinance as yf
import traceback

print(f"FDR Version: {fdr.__version__}")
print(f"yfinance Version: {yf.__version__}")

ticker = 'MMM'
print(f"\n--- Testing FDR with {ticker} ---")
try:
    df = fdr.DataReader(ticker, '2024-01-01')
    print("FDR Success!")
    print(df.tail())
except Exception as e:
    print(f"FDR Error: {e}")
    traceback.print_exc()

print(f"\n--- Testing yfinance directly with {ticker} ---")
try:
    data = yf.download(ticker, start='2024-01-01')
    if not data.empty:
        print("yfinance Success!")
        print(data.tail())
    else:
        print("yfinance returned empty data")
except Exception as e:
    print(f"yfinance Error: {e}")
    traceback.print_exc()
