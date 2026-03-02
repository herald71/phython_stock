from pykrx import stock
import pandas as pd

# 1. Get a valid trading date
print("Finding valid trading date...")
ohlcv = stock.get_market_ohlcv_by_date("20250301", "20250310", "005930")
if not ohlcv.empty:
    valid_date = ohlcv.index[0].strftime("%Y%m%d")
    print(f"Valid trading date: {valid_date}")
    
    try:
        print(f"--- Fetching fundamental for {valid_date} ---")
        df = stock.get_market_fundamental(valid_date)
        print("Columns found:")
        print(df.columns.tolist())
        if not df.empty and "005930" in df.index:
            print("Samsung data found!")
            print(df.loc["005930"])
    except Exception as e:
        print(f"Error for {valid_date}: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No trading days found in range.")
