import FinanceDataReader as fdr
import matplotlib.pyplot as plt

# [1단계] 사용자로부터 분석할 종목과 기간을 입력받습니다.
# 종목코드는 영문 대문자나 숫자로 입력하며, 날짜는 YYYY-MM-DD 형식을 사용합니다.
Code = input("분석할 종목 코드를 입력하세요 (예: 005930): ")
Start = input("시작일을 입력하세요 (예: 2023-01-01): ")
End = input("종료일을 입력하세요 (예: 2023-12-31): ")

print(f"\n입력된 정보: 종목({Code}), 기간({Start} ~ {End})")

# [2단계] 입력받은 정보를 바탕으로 주가 데이터를 불러옵니다.
df = fdr.DataReader(Code, Start, End)

# 데이터가 비어있는지 확인합니다.
if df.empty:
    print("⚠️ 데이터를 가져오지 못했습니다. 종목코드나 날짜 형식을 확인해 주세요!")
else:
    print(f"✅ 총 {len(df)}건의 데이터를 성공적으로 불러왔습니다.")

    # [3단계] 불러온 데이터를 차트로 시각화합니다.
    # 그래프 크기 설정 (가로 10, 세로 6)
    plt.figure(figsize=(10, 6))
    
    # 종가(Close)를 기준으로 선 그래프를 그립니다.
    df['Close'].plot()

    # 차트의 제목과 축 이름을 설정합니다.
    plt.title(f"Stock Chart: {Code}")
    plt.xlabel("Date")
    plt.ylabel("Price")
    
    # 격자(Grid)를 추가하여 읽기 편하게 만듭니다.
    plt.grid(True)
    
    # 마지막으로 차트를 화면에 보여줍니다.
    print("\n📈 차트 창이 열립니다. 확인 후 창을 닫아주세요.")
    plt.show()
