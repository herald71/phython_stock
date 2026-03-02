from pykrx import stock
import datetime

def get_latest_fundamentals(ticker):
    # 오늘부터 거꾸로 10일간 데이터를 찾아봄
    today = datetime.datetime.now()
    for i in range(10):
        target_date = (today - datetime.timedelta(days=i)).strftime("%Y%m%d")
        print(f"Checking date: {target_date}...")
        try:
            df = stock.get_market_fundamental_by_date(target_date, target_date, ticker)
            if not df.empty:
                print(f"Success! Found data on {target_date}")
                return df
        except Exception as e:
            print(f"Error on {target_date}: {e}")
    return None

ticker = "005930" # 삼성전자
print(f"Searching for fundamental data for {ticker}...")
df = get_latest_fundamentals(ticker)

if df is not None:
    print("\nSamsung Electronics Fundamentals:")
    print(df)
    per = df['PER'].values[0]
    pbr = df['PBR'].values[0]
    eps = df['EPS'].values[0]
    print(f"\nFinal Results:")
    print(f"PER: {per}")
    print(f"PBR: {pbr}")
    print(f"EPS: {eps}")
else:
    print("Failed to find data in the last 10 days.")
