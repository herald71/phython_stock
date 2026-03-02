"""
프로그램명 : sp500_tickers.py
작성일자 : 2026-02-27
버전 : 1.0
설명 : Wikipedia에서 S&P 500 구성 종목 티커를 실시간 추출하여
       리스트 출력 및 CSV 파일로 저장하는 프로그램
작성자 관점 : 퀀트 투자 및 금융 데이터 자동화 실무용
"""

# =========================
# 1. 라이브러리 Import
# =========================

import pandas as pd
import requests
from tabulate import tabulate
import time


# =========================
# 2. S&P 500 데이터 수집 함수
# =========================

def get_sp500_data():
    """
    Wikipedia의 S&P 500 구성 종목 페이지에서
    티커, 회사명, 섹터, 산업 정보를 추출합니다.
    """

    print("S&P 500 데이터를 Wikipedia에서 수집 중입니다...")

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # pandas로 HTML 테이블 읽기
        tables = pd.read_html(response.text)

        # 첫 번째 테이블이 S&P 500 구성 종목 리스트
        df = tables[0]

        # 필요한 컬럼만 선택 및 이름 변경
        # 컬럼 인덱스: Symbol, Security, GICS Sector, GICS Sub-Industry 등
        df = df[['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry']].copy()
        df.columns = ['Ticker', 'Company', 'Sector', 'Industry']

        # 티커 세정 (가끔 '.' 대신 '-'를 쓰는 경우가 있음)
        df['Ticker'] = df['Ticker'].str.replace('.', '-', regex=False)

        print(f"총 {len(df)}개의 종목 정보를 성공적으로 수집했습니다.")

        return df

    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")
        return None


# =========================
# 3. 메인 실행부
# =========================

if __name__ == "__main__":

    start_time = time.time()

    # 데이터 가져오기
    sp500_df = get_sp500_data()

    if sp500_df is not None:

        print("\n" + "=" * 85)
        print("              S&P 500 종목 리스트 (상위 10개 미리보기)")
        print("=" * 85)

        # 상위 10개 출력 (더 넓게 보기 위해 psql 스타일 유지)
        print(tabulate(sp500_df.head(10),
                       headers='keys',
                       tablefmt='psql',
                       showindex=False))

        print(f"\n... 외 총 {len(sp500_df)}개 종속")
        print(f"작업 소요 시간: {time.time() - start_time:.2f}초")

        # CSV 파일 저장 (엑셀 한글 깨짐 방지 utf-8-sig)
        file_name = "sp500_tickers_detailed.csv"
        sp500_df.to_csv(file_name,
                        index=False,
                        encoding="utf-8-sig")

        print(f"\n✅ '{file_name}' 파일 저장 완료!")

    else:
        print("\n❌ 데이터를 가져오는 데 실패했습니다.")
