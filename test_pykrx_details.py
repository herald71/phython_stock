from pykrx import stock
import pandas as pd

ticker = "005930"
print(f"--- Testing pykrx for {ticker} ---")

# Test 1: Historical OHLCV (Basic check)
print("Testing get_market_ohlcv_by_date...")
df_ohlcv = stock.get_market_ohlcv_by_date("20250102", "20250110", ticker)
print(f"OHLCV Rows: {len(df_ohlcv)}")
if not df_ohlcv.empty:
    print(df_ohlcv.head(2))

# Test 2: Historical Fundamentals
print("\nTesting get_market_fundamental_by_date...")
df_fund = stock.get_market_fundamental_by_date("20250102", "20250110", ticker)
print(f"Fundamental Rows: {len(df_fund)}")
if not df_fund.empty:
    print(df_fund.head(2))
else:
    print("Historical fundamentals returned EMPTY.")
    
    # Test 3: Single date fundamental for ALL stocks
    print("\nTesting get_market_fundamental for single date (20250102)...")
    df_all = stock.get_market_fundamental("20250102")
    print(f"Total stocks fundamental: {len(df_all)}")
    if not df_all.empty and ticker in df_all.index:
        print(f"Found {ticker} in single date fundamental!")
        print(df_all.loc[ticker])
