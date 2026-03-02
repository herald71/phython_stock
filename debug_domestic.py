import FinanceDataReader as fdr
from pykrx import stock
import pandas as pd
from datetime import datetime

ticker = "005930" # 삼성전자
start_date = "2025-03-01"
end_date = "2026-03-02"

print(f"--- Debugging Domestic Stock: {ticker} ---")

try:
    # 1. FDR Data
    df_fdr = fdr.DataReader(ticker, start=start_date, end=end_date)
    print(f"FDR Rows: {len(df_fdr)}")
    if not df_fdr.empty:
        print(f"FDR columns: {df_fdr.columns.tolist()}")
        print(f"FDR index sample: {df_fdr.index[0]} ({type(df_fdr.index)})")
        
        # Initialize columns like in the main script
        for col in ['BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS']:
            df_fdr[col] = None

    # 2. Pykrx Data
    pykrx_start = start_date.replace('-', '')
    pykrx_end = end_date.replace('-', '')
    df_fund = stock.get_market_fundamental_by_date(pykrx_start, pykrx_end, ticker)
    print(f"Pykrx Rows: {len(df_fund)}")
    
    if not df_fund.empty:
        print(f"Pykrx columns: {df_fund.columns.tolist()}")
        print(f"Pykrx index sample: {df_fund.index[0]} ({type(df_fund.index)})")
        
        # Align index type
        df_fund.index = pd.to_datetime(df_fund.index)
        print(f"Pykrx aligned index sample: {df_fund.index[0]} ({type(df_fund.index)})")
        
        # 3. Test Update
        print("\n--- Testing df.update() ---")
        cols_to_use = [c for c in ['BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS'] if c in df_fund.columns]
        df_fdr.update(df_fund[cols_to_use])
        
        # Check if BPS has values
        non_null_bps = df_fdr['BPS'].dropna()
        print(f"BPS non-null count after update: {len(non_null_bps)}")
        if len(non_null_bps) > 0:
            print("Update worked!")
        else:
            print("Update FAILED to fill values.")
            
            # Check for index mismatch
            common_indices = df_fdr.index.intersection(df_fund.index)
            print(f"Number of common indices: {len(common_indices)}")
            if len(common_indices) == 0:
                print("Indices do not match at all!")
                print("FDR index[0]:", df_fdr.index[0])
                print("Pykrx index[0]:", df_fund.index[0])

except Exception as e:
    print(f"Error: {e}")
