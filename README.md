# 📈 주식 데이터 분석 대시보드 (Stock Analysis Dashboard)

Streamlit을 활용한 인터랙티브 주식 데이터 조회 및 분석 도구입니다. 한국(KRX) 및 미국(NASDAQ, NYSE) 시장의 주가 데이터를 실시간으로 가져와 다양한 기술적 지표와 함께 시각화해 줍니다.

## 🚀 주요 기능

- **멀티 마켓 지원**: 한국 및 미국 주식 시장 종목 검색 지원
- **인터랙티브 차트**: Plotly를 이용한 캔들스틱 차트 및 거래량 시각화
- **기술적 지표 (Technical Indicators)**:
  - 이동평균선 (MA 5, 10, 20, 60일)
  - 상대강도지수 (RSI)
  - MACD (지수이동평균 수렴/확산)
- **매매 신호**: 골든크로스 및 데드크로스 자동 판별 및 차트 표시
- **데이터 분석**: 최근 10일간의 상세 데이터 테이블 및 변동률 표시
- **엑셀 다운로드**: 분석한 데이터를 편리하게 엑셀(.xlsx) 파일로 추출 가능

## 🛠️ 설치 및 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/herald71/phython_stock.git
cd phython_stock
```

### 2. 가상 환경 설정 (권장)
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 3. 필수 라이브러리 설치
```bash
pip install streamlit finance-datareader pandas plotly xlsxwriter
```

### 4. 앱 실행
```bash
streamlit run stock_dashboard.py
```

## 🖥️ 사용 화면 예시
- 사이드바에서 국가를 선택하고 종목명(예: 삼성전자)이나 티커(예: AAPL)를 입력하세요.
- 조회 기간을 설정하고 '조회하기' 버튼을 누르세요.
- 표시할 지표(MA, RSI, MACD)를 체크박스로 자유롭게 선택할 수 있습니다.

## 📜 라이선스
이 프로젝트는 교육 및 개인 분석용으로 제작되었습니다.

---
**기여하기**: 버그 리포트나 기능 제안은 Issue 또는 Pull Request를 통해 언제든 환영합니다! 😊
