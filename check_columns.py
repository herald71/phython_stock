from pykrx import stock
import pandas as pd

ticker = "005930"
date = "20250102"

print(f"--- Checking columns for {ticker} on {date} ---")
try:
    df = stock.get_market_fundamental(date)
    print(f"Columns: {df.columns.tolist()}")
    if not df.empty:
        if ticker in df.index:
            print(f"Data for {ticker}:")
            print(df.loc[ticker])
        else:
            print(f"Ticker {ticker} not found in index.")
            # Try to find it
            found = [idx for idx in df.index if ticker in str(idx)]
            if found: print(f"Found similar indices: {found[:5]}")
except Exception as e:
    print(f"Error 1: {e}")

print("\n--- Testing get_market_fundamental_by_date with range ---")
try:
    df_range = stock.get_market_fundamental_by_date("20250102", "20250110", ticker)
    print(f"Range Rows: {len(df_range)}")
    if not df_range.empty:
        print(f"Range Columns: {df_range.columns.tolist()}")
        print(df_range.head(1))
except Exception as e:
    print(f"Error 2: {e}")

print("\n--- Testing get_market_fundamental_by_ticker ---")
try:
    # Some versions have this
    df_t = stock.get_market_fundamental_by_ticker(date)
    print(f"Ticker-based Rows: {len(df_t)}")
    if not df_t.empty:
        print(f"Ticker-based Columns: {df_t.columns.tolist()}")
except Exception as e:
    print(f"Error 3: {e}")
