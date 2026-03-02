import requests
import json
import pandas as pd
from datetime import datetime, timedelta

def get_krx_fundamentals(ticker):
    # 최근 영업일을 찾기 위해 최근 10일 탐색
    url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://data.krx.co.kr/contents/MDC/MTA/OTM/MDC0302.jsp",
    }
    
    today = datetime.now()
    
    for i in range(10):
        target_date = (today - timedelta(days=i)).strftime("%Y%m%d")
        
        payload = {
            "bld": "dbnew/mdc/MDC/OTM/OTM020/MDC030201", # 개별종목 지표
            "itvTpCd": "1", # 1: 최근결산, 2: 최근 12개월(선행)
            "mktId": "ALL",
            "trdDd": target_date,
            "isuCd": ticker,
            "share": "1",
            "money": "1",
            "csvxls_isNo": "false",
        }
        
        try:
            print(f"Trying date: {target_date}...")
            # Note: IsuCd for Samsung is often formatted as 'KR7005930003' in this API
            # Let's try to get more general info if specific ticker fails, but usually short code works if mapped
            
            # For KRX API, isuCd often requires the full ISIN code or a mapping step.
            # But let's try searching by all stocks if specific is hard.
            
            resp = requests.post(url, data=payload, headers=headers)
            data = resp.json()
            
            if 'output' in data and data['output']:
                df = pd.DataFrame(data['output'])
                # 삼성전자 필터링 (다양한 검색 방식 고려)
                # 데이터가 리스트로 오는데, 종목코드로 필터링
                # KRX API output columns: ISU_SRT_CD (단축코드), ISU_NM (종목명), TDD_CLSPRC (종가), EPS, PER, BPS, PBR 등
                
                print(f"Success! Data found for {target_date}")
                return df
                
        except Exception as e:
            print(f"Error on {target_date}: {e}")
            
    return None

# 삼성전자의 단축코드 005930
print("Fetching fundamentals from KRX direct API...")
df = get_krx_fundamentals("005930")

if df is not None:
    # 필터링 (KRX API는 전체 목록을 줄 수도 있음)
    samsung = df[df['ISU_SRT_CD'] == '005930']
    if not samsung.empty:
        print("\nSamsung Electronics Fundamentals (Direct API):")
        print(f"EPS: {samsung['EPS'].values[0]}")
        print(f"PER: {samsung['PER'].values[0]}")
        print(f"PBR: {samsung['PBR'].values[0]}")
        print(f"BPS: {samsung['BPS'].values[0]}")
        print(f"종가: {samsung['TDD_CLSPRC'].values[0]}")
    else:
        print("\nData found but Samsung (005930) not in list. Available columns:")
        print(df.columns.tolist())
        print(df.head(1))
else:
    print("Failed to fetch data from KRX API.")
