from pykrx import stock
import traceback

date = "20250228" # A valid trading day (Friday)
markets = ["KOSPI", "KOSDAQ", "ALL"]

for m in markets:
    print(f"--- Testing market: {m} on {date} ---")
    try:
        df = stock.get_market_fundamental(date, market=m)
        print(f"Success! Rows: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")
        if not df.empty:
            print(df.head(1))
    except Exception:
        print(f"Failed for {m}")
        traceback.print_exc()
    print("-" * 30)
