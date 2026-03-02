import FinanceDataReader as fdr

try:
    df = fdr.StockListing('KRX-DESC')
    print("Columns in KRX-DESC:")
    print(df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.head())
    
    samsung = df[df['Code'] == '005930']
    print("\nSamsung Electronics row:")
    print(samsung)
except Exception as e:
    print(f"Error: {e}")
