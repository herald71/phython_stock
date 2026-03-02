import FinanceDataReader as fdr
import pandas as pd

print("--- Testing fdr.StockListing('KRX') ---")
try:
    df = fdr.StockListing('KRX')
    print(f"Rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    if not df.empty:
        print("\nFirst row sample:")
        print(df.iloc[0])
except Exception as e:
    print(f"Error: {e}")
