# ============================================================
# Program Name : download_index_data.py
# Author       : Python Expert Mode
# Created Date : 2026-03-01
# Description  : Download full historical KOSPI and S&P500 index data
#                using FinanceDataReader and save as CSV files.
#                Also visualize both indices.
# ============================================================

# -----------------------------
# 1️⃣ 라이브러리 불러오기
# -----------------------------
import FinanceDataReader as fdr   # 금융 데이터 다운로드 라이브러리
import pandas as pd               # 데이터 처리용
import matplotlib.pyplot as plt   # 그래프 출력용


# -----------------------------
# 2️⃣ 전체 기간 데이터 다운로드
# -----------------------------
# start='1900' 을 사용하면 가능한 가장 오래된 데이터부터 가져옵니다.

print("Downloading KOSPI index data...")
kospi = fdr.DataReader('KS11', start='1900')  # KS11 = KOSPI index ticker

print("Downloading S&P500 index data...")
sp500 = fdr.DataReader('^GSPC', start='1900')  # ^GSPC = S&P500 index ticker


# -----------------------------
# 3️⃣ CSV 파일로 저장
# -----------------------------
# index=True → 날짜도 함께 저장

kospi.to_csv('kospi_index.csv', index=True)
sp500.to_csv('sp500_index.csv', index=True)

print("CSV files saved successfully.")


# -----------------------------
# 4️⃣ 데이터 기본 정보 출력
# -----------------------------
print("\nKOSPI Data Info:")
print(kospi.head())

print("\nS&P500 Data Info:")
print(sp500.head())


# -----------------------------
# 5️⃣ 그래프 시각화
# -----------------------------
plt.figure(figsize=(12, 6))

# Close price 기준으로 그래프 작성
plt.plot(kospi['Close'], label='KOSPI Close')
plt.plot(sp500['Close'], label='SP500 Close')

plt.title("KOSPI vs SP500 Index")
plt.xlabel("Date")
plt.ylabel("Index Level")
plt.legend()
plt.grid(True)

plt.show()

print("Program finished successfully.")