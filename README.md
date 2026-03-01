# 📈 파이썬 주식 데이터 분석 대시보드 (Stock Analysis Dashboard)

> **Streamlit을 활용한 직관적이고 강력한 주식 데이터 시각화 도구입니다!** 🚀

한국(KRX) 및 미국(NASDAQ, NYSE, AMEX) 주식 시장의 실시간 데이터를 가져와 캔들스틱 차트와 핵심 기술적 지표들을 한눈에 쉽게 분석할 수 있습니다. 

---

## ✨ 주요 기능 (Features)

* 🌍 **글로벌 마켓 지원**: 버튼 하나로 한국 주식과 미국 주식 사이를 자유롭게 이동하며 검색할 수 있습니다.
* 📊 **인터랙티브 캔들 차트**: 확대/축소가 가능한 생동감 넘치는 차트 (Plotly 기반) 제공.
* 📈 **전문적인 기술적 지표**: 
  - **이동평균선(MA)**: 5일, 10일, 20일, 60일 선을 통한 트렌드 분석
  - **RSI (상대강도지수)**: 과매수/과매도 구간 파악
  - **MACD**: 추세의 전환점(골든/데드 크로스) 분석
* 💡 **자동 매매 신호 분석**: 차트 상에 크로스 지점을 표시해주어 매매 타이밍을 잡기 편합니다.
* 💾 **데이터 내보내기**: 분석한 주가 데이터와 지표들을 클릭 한 번에 엑셀(.xlsx) 파일로 저장할 수 있습니다.

---

## 🛠️ 설치 및 실행 가이드 (How to Run)

복잡한 설정 없이 아래 순서대로 터미널에 복사 후 붙여넣어 보세요!

### 1단계: 프로젝트 다운로드 (Clone)
```bash
git clone https://github.com/herald71/phython_stock.git
cd phython_stock
```

### 2단계: 가상환경 설정 (선택사항, 하지만 권장해요!)
프로젝트만의 독립된 환경을 만들어 충돌을 방지합니다.
```bash
python -m venv .venv

# 🔹 Windows 사용자
.\.venv\Scripts\activate

# 🔹 Mac / Linux 사용자
source .venv/bin/activate
```

### 3단계: 필수 프로그램 설치 (Install)
주식 데이터, 차트 도구 등 필요한 라이브러리를 한 번에 설치합니다.
```bash
pip install -r requirements.txt
```
*(또는 `pip install streamlit finance-datareader pandas plotly xlsxwriter pykrx`)*

### 4단계: 프로그램 시작! (Run)
아래 명령어를 입력하면 브라우저가 열리면서 대시보드가 실행됩니다.
```bash
streamlit run stock_dashboard.py
```

---

## � 어떻게 사용하나요? (Usage)

1. **마켓 선택**: 화면 왼쪽 사이드바에서 `한국 주식` 또는 `미국 주식`을 선택합니다.
2. **종목 검색**: 
   - 한국 주식: '삼성전자' 또는 '005930' 입력
   - 미국 주식: '애플' 또는 'AAPL' 입력 후 엔터!
3. **지표 설정**: 보고 싶은 기술적 지표 (MA, RSI, MACD 등)의 체크박스를 켜고 끕니다.
4. **결과 확인**: 기간을 설정하고 `조회하기`를 누르면 화면에 차트와 데이터가 요약되어 나타납니다.

---

## 🤝 기여하기 (Contributing)
이 프로젝트는 교육 및 개인 주식 분석용으로 만들어졌습니다.  
더 좋은 아이디어나 기능 추가 제안, 버그 제보는 언제나 **Issue**나 **Pull Request**로 환영합니다! 🎉

---
**License**: 자유롭게 참고하고 배포하셔도 좋습니다. (Personal & Educational Use)
