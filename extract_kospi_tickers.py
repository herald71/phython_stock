import pandas as pd
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import time

def get_kospi_tickers_naver_direct():
    """
    네이버 금융 시가총액 페이지를 직접 크롤링하여 
    코스피 전 종목의 티커와 종목명을 추출합니다.
    (API 에러에 영향을 받지 않는 가장 확실한 방법)
    """
    print("네이버 금융에서 실시간 코스피 종목 리스트를 추출하는 중입니다...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    kospi_data = []
    page = 1
    
    try:
        while True:
            # sosok=0 은 코스피, sosok=1 은 코스닥
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
            response = requests.get(url, headers=headers)
            
            # 파서(lxml)가 없어도 동작하도록 fallback 설정
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except:
                soup = BeautifulSoup(response.text, 'html.parser')
            
            # 종목명이 들어있는 a 태그들 찾기
            # class="tltle" 인 태그에 종목명과 링크(티커 포함)가 있음
            title_tags = soup.select('a.tltle')
            
            if not title_tags:
                break
                
            for tag in title_tags:
                name = tag.text
                href = tag['href']
                # href 예: /item/main.naver?code=005930
                ticker = href.split('code=')[-1]
                kospi_data.append({'종목코드': ticker, '종목명': name})
            
            # 진행 상황 출력 (5페이지마다)
            if page % 5 == 0:
                print(f"{page}페이지 읽기 완료...")
            
            page += 1
            time.sleep(0.1) # 서버 부하 방지
            
            # 코스피 종목은 보통 35~40페이지 내외임
            if page > 50: break

        df = pd.DataFrame(kospi_data)
        if not df.empty:
            print(f"성공적으로 {len(df)}개의 코스피 종목을 추출했습니다.")
            return df
        else:
            return None

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return None

if __name__ == "__main__":
    start_time = time.time()
    kospi_df = get_kospi_tickers_naver_direct()
    
    if kospi_df is not None:
        print("\n" + "="*50)
        print("      코스피(KOSPI) 실시간 종목 리스트 (네이버 금융)")
        print("="*50)
        
        # 상위 10개 출력
        print(tabulate(kospi_df.head(10), headers='keys', tablefmt='psql', showindex=False))
        
        print(f"\n... 외 총 {len(kospi_df)}개 종목")
        print(f"소요 시간: {time.time() - start_time:.2f}초")
        print("="*50)
        
        # CSV 저장
        kospi_df.to_csv("kospi_list.csv", index=False, encoding="utf-8-sig")
        print("\n'kospi_list.csv' 파일로 저장이 완료되었습니다.")
    else:
        print("\n데이터를 가져오지 못했습니다. 네트워크를 확인해 주세요.")
