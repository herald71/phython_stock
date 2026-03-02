import FinanceDataReader as fdr
import pandas as pd

print("--- Testing fdr.StockListing for KOSPI ---")
try:
    df = fdr.StockListing('KOSPI')
    print(f"Columns: {df.columns.tolist()}")
    if not df.empty:
        print("\nFirst row sample:")
        print(df.iloc[0])
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing pykrx get_market_fundamental_by_ticker ---")
from pykrx import stock
try:
    df_t = stock.get_market_fundamental_by_ticker("20250304")
    print(f"Rows: {len(df_t)}")
    if not df_t.empty:
        print(f"Columns: {df_t.columns.tolist()}")
        print(df_t.head(1))
except Exception as e:
    print(f"Error: {e}")
