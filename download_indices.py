import FinanceDataReader as fdr
import matplotlib.pyplot as plt
import pandas as pd

# 1. 데이타를 다운로드 받는 함수 정의
def download_stock_indices():
    # --- 코스피(KOSPI) 지수 다운로드 ---
    # '^KS11'은 야후 파이낸스의 KOSPI 지수 심볼입니다 (현재 KRX 소스보다 안정적입니다).
    print("KOSPI 데이터를 다운로드 중입니다...")
    kospi = fdr.DataReader('^KS11')
    
    # 데이터를 CSV 파일로 저장 (파일명: kospi_index.csv)
    kospi.to_csv('kospi_index.csv')
    print("KOSPI 데이터가 'kospi_index.csv'로 저장되었습니다.")
    
    # --- S&P 500 지수 다운로드 ---
    # fdr.DataReader('US500')는 S&P 500 지수 데이터를 가져옵니다.
    print("S&P 500 데이터를 다운로드 중입니다...")
    sp500 = fdr.DataReader('US500')
    
    # 데이터를 CSV 파일로 저장 (파일명: sp500_index.csv)
    sp500.to_csv('sp500_index.csv')
    print("S&P 500 데이터가 'sp500_index.csv'로 저장되었습니다.")
    
    return kospi, sp500

# 2. 데이터를 그래프로 그리는 함수 정의
def plot_indices(kospi, sp500):
    # 그래프를 그릴 도화지(Figure) 설정
    plt.figure(figsize=(12, 8))
    
    # 첫 번째 그래프: KOSPI
    plt.subplot(2, 1, 1) # 2행 1열 중 첫 번째
    plt.plot(kospi.index, kospi['Close'], label='KOSPI', color='blue')
    plt.title('KOSPI Index History')
    plt.xlabel('Date')
    plt.ylabel('KOSPI Index')
    plt.grid(True)
    plt.legend()
    
    # 두 번째 그래프: S&P 500
    plt.subplot(2, 1, 2) # 2행 1열 중 두 번째
    plt.plot(sp500.index, sp500['Close'], label='S&P 500', color='red')
    plt.title('S&P 500 Index History')
    plt.xlabel('Date')
    plt.ylabel('S&P 500 Index')
    plt.grid(True)
    plt.legend()
    
    # 그래프 간격 조절 후 화면에 출력
    plt.tight_layout()
    plt.show()

# --- 프로그램 시작점 ---
if __name__ == "__main__":
    try:
        # 1. 데이터 다운로드 및 저장
        kospi_df, sp500_df = download_stock_indices()
        
        # 2. 데이터 시각화 (그래프 그리기)
        plot_indices(kospi_df, sp500_df)
        
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
