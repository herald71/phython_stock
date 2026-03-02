import FinanceDataReader as fdr
from datetime import datetime, timedelta
import sys

try:
    today_str = datetime.now().strftime("%Y-%m-%d")
    start_date_download = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")
    end_date_download = today_str

    print(f"Fetching MMM data from {start_date_download} to {end_date_download}...")
    df = fdr.DataReader('MMM', start_date_download, end_date_download)
    print("Success!")
    print(df.tail())
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
