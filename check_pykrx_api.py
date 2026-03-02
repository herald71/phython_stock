from pykrx import stock
import pandas as pd

print("Listing pykrx stock methods:")
methods = [m for m in dir(stock) if m.startswith('get_market')]
for m in methods:
    print(f" - {m}")

print("\nTesting get_market_fundamental_by_date columns...")
# Use a very safe date
df = stock.get_market_fundamental_by_date("20240102", "20240105", "005930")
print(f"Sample range data size: {len(df)}")
if not df.empty:
    print(f"Columns: {df.columns.tolist()}")
    print(df.head())
else:
    print("Range data is empty. Testing single date fundamental for all stocks to see column names...")
    df_all = stock.get_market_fundamental("20240102")
    print(f"Columns for all stocks: {df_all.columns.tolist()}")
    if not df_all.empty:
        print(f"Samsung sample: {df_all.loc['005930'] if '005930' in df_all.index else 'Not found'}")
