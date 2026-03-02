import yfinance as yf
import requests
import os
import certifi

# SSL 해결 시도 1: 환경 변수 설정
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

print("--- Testing yfinance with SSL Fix ---")
try:
    # SSL 해결 시도 2: 세션 설정
    session = requests.Session()
    # session.verify = False # 필요시 주석 해제하여 극단적으로 우회
    
    ticker = "AAPL"
    yt = yf.Ticker(ticker, session=session)
    print(f"Fetching info for {ticker}...")
    info = yt.info
    print(f"PER: {info.get('trailingPE')}")
    print(f"PBR: {info.get('priceToBook')}")
    print("Success!")
except Exception as e:
    print(f"yfinance failed: {e}")

print("\n--- Testing pykrx with today's date ---")
from pykrx import stock
try:
    today = "20260302"
    df = stock.get_market_fundamental_by_date(today, today, "005930")
    if not df.empty:
        print("Today's data found!")
        print(df)
    else:
        print("Today's data not found. Trying without ticker filter...")
        df_all = stock.get_market_fundamental_by_date(today, today)
        print(f"Total stocks found: {len(df_all)}")
        if "005930" in df_all.index:
            print("Samsung found in total list!")
            print(df_all.loc["005930"])
except Exception as e:
    print(f"pykrx failed: {e}")
