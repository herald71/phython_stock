import pykrx
from pykrx import stock
import traceback

print(f"pykrx version: {pykrx.__version__}")

date = "20240102"
print(f"--- Testing for {date} ---")

try:
    df = stock.get_market_fundamental(date)
    print("Success!")
    print(df.columns.tolist())
except Exception:
    traceback.print_exc()
