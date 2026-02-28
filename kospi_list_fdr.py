"""
프로그램명 : kospi_list_fdr.py
작성일자 : 2026-02-27
버전 : 1.0
설명 : FinanceDataReader를 이용하여 코스피 전체 종목 리스트를 추출하고 CSV로 저장
"""

import pandas as pd
import FinanceDataReader as fdr
from tabulate import tabulate
import time


def get_kospi_tickers_fdr():
    """
    FinanceDataReader를 이용하여
    코스피 전 종목의 티커와 종목명을 추출합니다.
    """
    print("FinanceDataReader를 통해 코스피 종목 리스트를 불러오는 중입니다...")

    try:
        # 코스피 전체 종목 리스트 가져오기
        df = fdr.StockListing('KOSPI')

        # 필요한 컬럼만 추출
        kospi_df = df[['Code', 'Name']].copy()
        kospi_df.columns = ['종목코드', '종목명']

        print(f"성공적으로 {len(kospi_df)}개의 코스피 종목을 추출했습니다.")
        return kospi_df

    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")
        return None


if __name__ == "__main__":
    start_time = time.time()

    kospi_df = get_kospi_tickers_fdr()

    if kospi_df is not None:
        print("\n" + "=" * 50)
        print("      코스피(KOSPI) 종목 리스트 (FinanceDataReader)")
        print("=" * 50)

        # 상위 10개 출력
        print(tabulate(kospi_df.head(10), headers='keys', tablefmt='psql', showindex=False))

        print(f"\n... 외 총 {len(kospi_df)}개 종목")
        print(f"소요 시간: {time.time() - start_time:.2f}초")
        print("=" * 50)

        # CSV 저장
        kospi_df.to_csv("kospi_list.csv", index=False, encoding="utf-8-sig")
        print("\n'kospi_list.csv' 파일로 저장이 완료되었습니다.")
    else:
        print("\n데이터를 가져오지 못했습니다.")