from pykrx import stock
import datetime

# 오늘 날짜
today = datetime.datetime.now().strftime("%Y%m%d")

print(f"Testing pykrx fundamental data for date: {today}")

try:
    # 삼성전자(005930)의 PER, PBR, EPS 정보 가져오기
    # get_market_fundamental_by_date 는 특정 날짜의 데이터를 가져옴
    df = stock.get_market_fundamental_by_date(today, today, "005930")
    print("\nSamsung Electronics Fundamentals:")
    print(df)
    
    if not df.empty:
        per = df['PER'].values[0]
        pbr = df['PBR'].values[0]
        eps = df['EPS'].values[0]
        print(f"\nExtracted Values:")
        print(f"PER: {per}")
        print(f"PBR: {pbr}")
        print(f"EPS: {eps}")
    else:
        print("No data found for the given date. Trying yesterday...")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        df = stock.get_market_fundamental_by_date(yesterday, yesterday, "005930")
        print(df)

except Exception as e:
    print(f"Error: {e}")
