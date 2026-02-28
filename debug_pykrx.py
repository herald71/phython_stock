from pykrx import stock
from datetime import datetime, timedelta

def get_recent_business_day():
    # 오늘부터 거구로 최근 거래일 찾기 (최대 10일 전까지 확인)
    today = datetime.now()
    for i in range(10):
        target_date = (today - timedelta(days=i)).strftime("%Y%m%d")
        tickers = stock.get_market_ticker_list(target_date, market="KOSPI")
        if tickers:
            return target_date, tickers
    return None, []

date, tickers = get_recent_business_day()
if date:
    print(f"최근 거래일: {date}")
    print(f"종목 수: {len(tickers)}")
    for i in range(min(5, len(tickers))):
        print(f"{tickers[i]}: {stock.get_market_ticker_name(tickers[i])}")
else:
    print("거래일을 찾을 수 없습니다.")
