from pykrx import stock
import pandas as pd

date = "20250102"
print(f"--- Raw check for {date} ---")

try:
    df = stock.get_market_fundamental(date)
    print("Columns from get_market_fundamental:")
    print(df.columns.tolist())
    if not df.empty:
        print("\nFirst row sample:")
        print(df.iloc[0])
except Exception as e:
    print(f"Error: {e}")
