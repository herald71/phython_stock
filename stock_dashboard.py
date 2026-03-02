import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# 필수 라이브러리 설치 안내:
# streamlit: 웹 대시보드 제작용 라이브러리
# finance-datareader: 주식 데이터를 가져오는 라이브러리
# pandas: 데이터를 가공하고 분석하는 라이브러리
# xlsxwriter: 엑셀 파일 생성을 도와주는 라이브러리
# plotly: 인터랙티브한 그래프(차트)를 만드는 라이브러리
# 터미널에서 아래 명령어를 실행하여 필요한 라이브러리를 설치해 주세요.
# pip install streamlit finance-datareader pandas xlsxwriter plotly

# --- 1. 페이지 기본 설정 및 사용자 안내 ---
# set_page_config: 웹 페이지의 타이틀(제목), 아이콘, 레이아웃(넓게 보기 등)을 설정합니다.
st.set_page_config(page_title="주식 데이터 조회기", page_icon="📈", layout="wide")

# --- CSS 커스텀 스타일 추가 (가독성 개선) ---
# st.metric의 폰트 크기가 커서 지표가 잘리는 현상을 해결하기 위해 CSS를 주입합니다.
st.markdown("""
    <style>
    /* 기본 metric의 폰트 크기 및 간격 미세 조정 */
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    [data-testid="stMetric"] { padding: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 주식 시장 데이터 조회 및 다운로드 앱")

# --- 헬퍼 함수: 지표 직접 그리기 (색상 강조 및 도움말 추가) ---
def draw_custom_metric(col, label, value, color="#31333F", help_text=""):
    """
    st.metric 대신 사용하는 커스텀 HTML 지표 함수입니다.
    도움말 아이콘(❔)과 마우스 오버 툴팁을 제공합니다.
    """
    help_icon = f'<span style="cursor:help; margin-left:4px; font-size: 0.7rem; color: #999;" title="{help_text}">❔</span>' if help_text else ""
    # HTML 코드 내 공백/들여쓰기가 있으면 마크다운이 코드로 오해할 수 있어 한 줄로 결합합니다.
    html_code = f'<div style="display: flex; flex-direction: column; align-items: flex-start; padding: 5px;"><div style="display: flex; align-items: center; margin-bottom: 2px;"><span style="font-size: 0.8rem; color: #555; white-space: nowrap;">{label}</span>{help_icon}</div><span style="font-size: 1.2rem; font-weight: bold; color: {color}; line-height: 1.1; white-space: nowrap;">{value}</span></div>'
    col.markdown(html_code, unsafe_allow_html=True)

# st.info: 사용자에게 파란색 박스로 안내 메시지를 표시합니다.
st.info("💡 **이용 가이드**: 사이드바에서 국가를 선택한 후 종목명이나 티커(예: 삼성전자, AAPL)를 입력하고 '조회하기' 버튼을 누르세요.")

# --- 시장 심리 지수 (공포지수) 섹션 추가 ---
@st.cache_data(ttl=3600) # 1시간마다 갱신
def get_market_sentiment():
    """
    CNN Fear & Greed Index, VIX, VKOSPI 지수를 가져오는 함수입니다.
    """
    sentiment_data = {
        "fng_score": None, "fng_text": "N/A", 
        "vix_score": None, "vkospi_score": None
    }
    
    # 1. CNN Fear & Greed Index
    try:
        # CNN API는 이제 더 정교한 헤더를 요구할 수 있습니다.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.cnn.com/markets/fear-and-greed'
        }
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            sentiment_data["fng_score"] = data['fear_and_greed']['score']
            sentiment_data["fng_text"] = data['fear_and_greed']['rating'].upper()
    except Exception:
        pass

    # 2. VIX 지수 (미국)
    try:
        vix_df = fdr.DataReader('VIX') # fdr.DataReader('VIX') 가 더 안정적일 수 있음
        if not vix_df.empty:
            sentiment_data["vix_score"] = vix_df.iloc[-1]['Close']
    except Exception:
        pass

    # 3. VKOSPI 지수 (한국) - 인베스팅닷컴에서 추출
    try:
        from bs4 import BeautifulSoup
        # 인베스팅닷컴 코스피 변동성 지수 페이지
        vk_url = "https://kr.investing.com/indices/kospi-volatility"
        vk_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        vk_r = requests.get(vk_url, headers=vk_headers, timeout=5)
        if vk_r.status_code == 200:
            soup = BeautifulSoup(vk_r.text, 'html.parser')
            # 사용자가 지정한 data-test="instrument-price-last" 속성을 가진 div 추출
            price_div = soup.find('div', {'data-test': 'instrument-price-last'})
            if price_div:
                val_str = price_div.text.strip()
                sentiment_data["vkospi_score"] = float(val_str.replace(',', ''))
    except Exception:
        pass
        
    return sentiment_data

# 상단에 시장 심리 지수 표시
st.markdown("### 🌐 현재 시장 심리 상태 (Market Sentiment)")
sentiment = get_market_sentiment()
m_col1, m_col2, m_col3, m_col4 = st.columns([1, 1, 1, 3])

# Fear & Greed Index 표시
if sentiment["fng_score"] is not None:
    score = sentiment["fng_score"]
    fng_color = "#FF4B4B" if score < 25 else "#FFAA00" if score < 45 else "#31333F" if score < 55 else "#AAFF00" if score < 75 else "#2CA02C"
    draw_custom_metric(m_col1, "Fear & Greed Index", f"{score:.1f}", color=fng_color, help_text="CNN 제공 시장 심리 지수입니다. 0(극도의 공포) ~ 100(극도의 탐욕) 사이로 표시됩니다.")
else:
    m_col1.warning("F&G 로드 실패")

# VIX 지수 표시 (미국)
if sentiment["vix_score"] is not None:
    vix_val = sentiment["vix_score"]
    vix_color = "#31333F" if vix_val < 20 else "#FFAA00" if vix_val < 30 else "#FF4B4B"
    draw_custom_metric(m_col2, "VIX (미국 공포지수)", f"{vix_val:.2f}", color=vix_color, help_text="S&P 500의 향후 30일간 기대 변동성입니다. 20 이상이면 불안, 30 이상이면 극심한 패닉으로 해석합니다.")
else:
    m_col2.warning("VIX 로드 실패")

# VKOSPI 지수 표시 (한국)
if sentiment["vkospi_score"] is not None:
    vk_val = sentiment["vkospi_score"]
    vk_color = "#31333F" if vk_val < 20 else "#FFAA00" if vk_val < 25 else "#FF4B4B"
    draw_custom_metric(m_col3, "VKOSPI (한국 공포지수)", f"{vk_val:.2f}", color=vk_color, help_text="코스피 200 옵션 가격을 바탕으로 한 향후 30일간의 예상 변동성입니다. 30이 넘으면 시장이 패닉 상태임을 의미하며 역사적 최고치는 약 71입니다.")
else:
    m_col3.warning("VKOSPI 로드 실패")

# 상태 설명 메시지
with m_col4:
    if sentiment["fng_score"] is not None:
        status_msg = {
            "EXTREME FEAR": "😱 **극도의 공포**: 시장이 매우 비관적입니다. 과매도 구간일 가능성이 큽니다.",
            "FEAR": "😰 **공포**: 투자자들이 위축되어 있습니다. 조심스러운 접근이 필요합니다.",
            "NEUTRAL": "😐 **중립**: 시장 성향이 뚜렷하지 않은 상태입니다.",
            "GREED": "😏 **탐욕**: 시장이 다소 과열되어 있습니다. 수익 실현을 고민할 때입니다.",
            "EXTREME GREED": "🤑 **극도의 탐욕**: 시장이 매우 낙관적이며 과열되었습니다. 거품을 경계해야 합니다."
        }
        st.write(status_msg.get(sentiment["fng_text"], "시장 데이터를 분석 중입니다."))
    else:
        st.write("시장 심리 데이터를 불러올 수 없습니다.")

# 시장 심리 지수 가이드 expander 추가
with st.expander("❔ 시장 심리 상태 지표 상세 설명 가이드"):
    st.markdown("""
    ### 📊 지표별 상세 가이드
    
    #### 1. CNN Fear & Greed Index
    - **개요**: 미국 시장의 7가지 지표(주가 강도, 옵션 수요 등)를 종합한 심리 지수입니다.
    - **기준**: 0~25(극도 공포), 25~45(공포), 45~55(중립), 55~75(탐욕), 75~100(극도 탐욕)
    - **활용**: "남들이 공포에 떨 때 사고, 탐욕스러울 때 팔아라"는 역발상 투자 지표로 자주 쓰입니다.

    #### 2. VIX (미국 공포지수)
    - **개요**: S&P 500 지수 옵션의 변동성을 나타내는 지표입니다.
    - **기준**: **20 미만**(안정), **20~30**(불안 가중), **30 이상**(심각한 패닉/폭락장).
    - **특징**: 주가지수와 반대로 움직이는 경향이 있어 '공포지수'라 부릅니다.

    #### 3. VKOSPI (한국 공포지수)
    - **개요**: 코스피 200 옵션 가격을 기반으로 한 한국판 변동성 지수입니다.
    - **기준**: **20 미만**(평온), **20~30**(불안), **30 이상**(패닉 상태).
    - **역사적 수치**: 2020년 팬데믹 당시 최고 **71.39**를 기록한 바 있습니다. 수치가 높을수록 "지금 시장이 매우 두려워하고 있다"는 뜻입니다.

    ---
    💡 **전문가 팁**: 공포지수가 최고조에 달했을 때가 종종 역사적인 저점(매수 기회)인 경우가 많습니다. 하지만 높은 변동성은 큰 손실을 초래할 수 있으니 주의 깊게 관찰하세요!
    """)

st.divider()

# --- 2. 종목 매핑을 위한 데이터 로딩 (한국 & 미국) ---
# @st.cache_data: 데이터를 한 번 불러오면 메모리에 저장(캐싱)하여, 다음에 조회할 때 속도를 훨씬 빠르게 만듭니다.
@st.cache_data
def load_stock_list(market_type):
    """
    선택한 국가(시장)의 상장 종목 목록을 가져오는 함수입니다.
    market_type: "한국" 또는 "미국"
    """
    if market_type == "한국":
        try:
            # 1차 시도: KRX-DESC (상세 리스트)
            return fdr.StockListing('KRX-DESC')
        except Exception:
            try:
                # 2차 시도: 일반 KRX 리스트
                return fdr.StockListing('KRX')
            except Exception:
                try:
                    # 3차 시도: pykrx (IndexError 방지 핸들링 추가)
                    with st.spinner('FDR 서버 응답 지연으로 대체 데이터를 시도합니다...'):
                        tickers = stock.get_market_ticker_list(market="ALL")
                        rows = []
                        for ticker in tickers:
                            name = stock.get_market_ticker_name(ticker)
                            rows.append({'Code': ticker, 'Name': name, 'Symbol': ticker})
                        if not rows: raise ValueError("No rows from pykrx")
                        return pd.DataFrame(rows)
                except Exception:
                    # 4차 시도: 로컬 CSV 파일 (최종 보루)
                    try:
                        with st.spinner('온라인 연결 문제로 로컬 데이터 저장소를 사용합니다...'):
                            df_local = pd.read_csv('kospi_list.csv')
                            df_local.rename(columns={'종목코드': 'Code', '종목명': 'Name'}, inplace=True)
                            df_local['Symbol'] = df_local['Code']
                            return df_local
                    except Exception:
                        return pd.DataFrame(columns=['Code', 'Name', 'Symbol'])
    else:
        # 미국 시장 (NASDAQ, NYSE) 통합 리스트 구성
        # st.spinner: 데이터를 불러오는 동안 '로딩 중' 메시지를 화면에 보여줍니다.
        with st.spinner('미국 상장 종목 목록을 불러오는 중입니다... 처음 한 번만 실행됩니다.'):
            try:
                df_nasdaq = fdr.StockListing('NASDAQ')
                df_nyse = fdr.StockListing('NYSE')
                cols = ['Symbol', 'Name']
                df_us = pd.concat([df_nasdaq[cols], df_nyse[cols]], ignore_index=True)
                df_us = df_us.drop_duplicates(subset=['Symbol'])
                return df_us
            except Exception:
                # 미국 시장 로드 실패 시 빈 데이터프레임 반환 (에러 방지)
                return pd.DataFrame(columns=['Symbol', 'Name'])

# --- 3. 사이드바 UI 구성 ---
st.sidebar.header("🔍 검색 설정")

# 국가 선택 (라디오 버튼) - 폼 외부에 두어 즉시 반응하게 합니다.
market_choice = st.sidebar.radio("국가 선택", ["한국", "미국"], horizontal=True)

# 조회 기간 선택 (새 기능 추가)
period_choice = st.sidebar.radio("조회 기간 선택", ["1년", "3년", "5년", "10년", "사용자 설정"], horizontal=True)

# 선택된 기간에 따라 기본 시작일 계산
default_end = datetime.today().date()
if period_choice == "1년":
    default_start = default_end - timedelta(days=365)
elif period_choice == "3년":
    default_start = default_end - timedelta(days=365*3)
elif period_choice == "5년":
    default_start = default_end - timedelta(days=365*5)
elif period_choice == "10년":
    default_start = default_end - timedelta(days=365*10)
else:
    # '사용자 설정'이거나 기타 경우 기본 1년
    default_start = default_end - timedelta(days=365)

# 종목 리스트 미리 로드
df_listing = load_stock_list(market_choice)

# 나머지 설정은 폼(Form)으로 묶어서 '조회하기' 클릭 시 한꺼번에 실행되도록 합니다.
with st.sidebar.form("search_form"):
    # st.text_input: 사용자가 텍스트(종목명 또는 코드)를 입력할 수 있는 칸입니다.
    default_input = "삼성전자" if market_choice == "한국" else "AAPL"
    stock_input = st.text_input("종목명 또는 티커 입력", value=default_input)

    # st.date_input: 달력 모양의 입력을 통해 날자로 범위를 설정합니다.
    start_date = st.date_input("시작일", value=default_start)
    end_date = st.date_input("종료일", value=default_end)
    
    # 지표 표시 설정
    st.subheader("🛠️ 지표 설정")
    show_ma = st.checkbox("이동평균선 (MA) 표시", value=True)
    show_rsi = st.checkbox("상대강도지수 (RSI) 표시", value=True)
    show_macd = st.checkbox("MACD 표시", value=True)
    
    # st.form_submit_button: 작성한 폼을 서버로 보내는(실행하는) 버튼입니다.
    submit_button = st.form_submit_button("조회하기")

# --- 4. 종목 코드/티커 변환 함수 ---
def get_stock_code(name_or_symbol, df_listing, market_type):
    """
    사용자가 입력한 이름 또는 티커를 바탕으로 실제 주식 코드를 찾는 함수입니다.
    """
    # 공백 제거
    name_or_symbol = name_or_symbol.strip()
    
    if market_type == "한국":
        # 한국: 사용자가 숫자로 된 '코드'를 직접 입력했는지 확인(isdigit)
        if name_or_symbol.isdigit():
            return name_or_symbol
        # 이름으로 검색하여 일치하는 행을 찾습니다.
        matching = df_listing[df_listing['Name'] == name_or_symbol]
        return matching.iloc[0]['Code'] if not matching.empty else None
    else:
        # 미국: 티커(Symbol, 예: AAPL) 우선 검색 (대문자로 변환하여 비교)
        # 대소문자 구분 없이 검색하기 위해 처리
        matching_symbol = df_listing[df_listing['Symbol'].str.upper() == name_or_symbol.upper()]
        if not matching_symbol.empty:
            return matching_symbol.iloc[0]['Symbol']
        
        # 이름(Name)에 사용자의 입력어가 포함되어 있는지 부분 일치 검색을 합니다.
        matching_name = df_listing[df_listing['Name'].str.contains(name_or_symbol, case=False, na=False)]
        return matching_name.iloc[0]['Symbol'] if not matching_name.empty else None

# --- 5. 데이터 조회 및 출력 로직 ---
# '조회하기' 버튼이 클릭되었을 때만 실행됩니다.
if submit_button:
    # 4번에서 만든 함수를 통해 실제 코드를 찾아냅니다.
    stock_code = get_stock_code(stock_input, df_listing, market_choice)
    
    if stock_code:
        st.subheader(f"📊 {stock_input} ({stock_code}) 데이터 - {market_choice}")
        
        with st.spinner('데이터를 불러오는 중입니다...'):
            try:
                # fdr.DataReader: 주식 코드를 통해 실제 가격 정보를 가져옵니다.
                stock_df = fdr.DataReader(stock_code, start_date, end_date)
            except Exception as e:
                # 오류 발생 시 에러 메시지 출력
                st.error(f"오류 발생: {e}")
                stock_df = pd.DataFrame()
        
        # 데이터가 비어있지 않은 경우에만 분석 및 시각화 진행
        if not stock_df.empty:
            # 보정 작업: 인덱스에 있는 날짜 데이터를 일반 컬럼으로 뺍니다(reset_index).
            stock_df.index.name = 'Date'
            stock_df = stock_df.reset_index()
            
            # --- 6. 요약 지표 ---
            st.markdown("### 📌 기간 내 요약 지표")
            col1, col2, col3, col4, col5, col6 = st.columns(6) # 화면을 6개의 열로 나눕니다.
            
            # iloc[-1]: 가장 마지막 줄(최근 데이터)의 값을 가져옵니다.
            p_current = stock_df.iloc[-1]['Close'] # 현재가
            p_max = stock_df['High'].max()        # 해당 기간 최고가
            p_min = stock_df['Low'].min()         # 해당 기간 최저가
            
            # 거래량 지표 계산
            v_today = stock_df.iloc[-1]['Volume'] # 당일 거래량
            # tail(20).mean(): 최근 20일치 데이터를 가져와서 평균을 냅니다.
            v_avg_20 = int(stock_df['Volume'].tail(20).mean()) 
            
            # RVOL(상대거래량): 당일 거래량이 평균 대비 얼마나 터졌는지 계산 (1.0 기준)
            rvol = v_today / v_avg_20 if v_avg_20 > 0 else 0
            
            # 단위 설정 (원 또는 $)
            unit = "원" if market_choice == "한국" else "$"
            # 국가별 가격 형식(소수점 유무) 지정
            fmt = ",.0f" if market_choice == "한국" else ",.2f"
            
            # 커스텀 헬퍼 함수를 사용하여 지표를 그립니다. (빨간색 강조 포함)
            draw_custom_metric(col1, "현재가", f"{float(p_current):{fmt}} {unit}", color="#FF0000")
            draw_custom_metric(col2, "최고가", f"{float(p_max):{fmt}} {unit}")
            draw_custom_metric(col3, "최저가", f"{float(p_min):{fmt}} {unit}")
            draw_custom_metric(col4, "당일 거래량", f"{v_today:,} 주")
            draw_custom_metric(col5, "최근 20일 평균거래량", f"{v_avg_20:,} 주")
            draw_custom_metric(col6, "상대거래량 (RVOL)", f"{rvol:.2f}", color="#FF0000", help_text="현재 거래량을 최근 20일 평균 거래량으로 나눈 수치입니다. 1.0보다 크면 평소보다 거래가 활발함을 의미합니다.")
            
            # --- 7. 보조 지표 계산 (MA, RSI, MACD) ---
            # 이동평균선(MA)
            stock_df['MA5'] = stock_df['Close'].rolling(window=5).mean()
            stock_df['MA10'] = stock_df['Close'].rolling(window=10).mean()
            stock_df['MA20'] = stock_df['Close'].rolling(window=20).mean()
            stock_df['MA60'] = stock_df['Close'].rolling(window=60).mean()

            # RSI (Relative Strength Index) 계산
            def calculate_rsi(data, window=14):
                delta = data.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                # 0으로 나누기 방지
                rs = gain / loss.replace(0, 0.001)
                return 100 - (100 / (1 + rs))
            
            stock_df['RSI'] = calculate_rsi(stock_df['Close'])

            # MACD (Moving Average Convergence Divergence) 계산
            # 12일 지수이동평균 - 26일 지수이동평균
            exp1 = stock_df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = stock_df['Close'].ewm(span=26, adjust=False).mean()
            stock_df['MACD'] = exp1 - exp2
            # 시그널 라인 (9일 EMA)
            stock_df['Signal'] = stock_df['MACD'].ewm(span=9, adjust=False).mean()
            stock_df['MACD_Hist'] = stock_df['MACD'] - stock_df['Signal']

            # 골든크로스 & 데드크로스 신호 판별 (20일선 vs 60일선)
            stock_df['Golden'] = (stock_df['MA20'].shift(1) < stock_df['MA60'].shift(1)) & (stock_df['MA20'] > stock_df['MA60'])
            stock_df['Death'] = (stock_df['MA20'].shift(1) > stock_df['MA60'].shift(1)) & (stock_df['MA20'] < stock_df['MA60'])

            # --- 8. Plotly 차트 (캔들스틱 + 이동평균선 + 매매신호 + 보조지표 + 거래량) ---
            st.markdown("### 📈 주가 및 보조지표 추이")
            
            # 서브플롯 구성 정의
            rows = 2
            row_heights = [0.7, 0.3]
            specs = [[{"secondary_y": False}], [{"secondary_y": False}]]
            
            if show_rsi:
                rows += 1
                row_heights = [0.55, 0.15, 0.3]
                specs.insert(1, [{"secondary_y": False}])
            if show_macd:
                rows += 1
                old_heights = row_heights
                if show_rsi:
                    row_heights = [0.45, 0.15, 0.15, 0.25]
                else:
                    row_heights = [0.55, 0.15, 0.30]
                specs.insert(-1, [{"secondary_y": False}])

            fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
            
            # 1행: 캔들스틱 차트
            fig.add_trace(go.Candlestick(
                x=stock_df['Date'], open=stock_df['Open'], high=stock_df['High'], 
                low=stock_df['Low'], close=stock_df['Close'], name='주가',
                increasing_line_color='red', decreasing_line_color='blue'
            ), row=1, col=1)

            # 이동평균선 추가 (체크박스 확인)
            if show_ma:
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['MA5'], name='MA5', line=dict(color='#E377C2', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['MA10'], name='MA10', line=dict(color='#FFD700', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['MA20'], name='MA20', line=dict(color='#2CA02C', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['MA60'], name='MA60', line=dict(color='#9467BD', width=1.5)), row=1, col=1)

            # --- 매매 신호 (골든/데드크로스) 추가 ---
            # 골든크로스 신호: 빨간색 위쪽 화살표
            buy_signals = stock_df[stock_df['Golden']]
            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals['Date'], y=buy_signals['Low'] * 0.98,
                    mode='markers+text', name='매수신호',
                    marker=dict(symbol='triangle-up', size=12, color='red'),
                    text='매수', textposition='bottom center',
                    textfont=dict(color='red', size=12, family='Arial Black')
                ), row=1, col=1)

            # 데드크로스 신호: 파란색 아래쪽 화살표
            sell_signals = stock_df[stock_df['Death']]
            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals['Date'], y=sell_signals['High'] * 1.02,
                    mode='markers+text', name='매도신호',
                    marker=dict(symbol='triangle-down', size=12, color='blue'),
                    text='매도', textposition='top center',
                    textfont=dict(color='blue', size=12, family='Arial Black')
                ), row=1, col=1)
            
            # --- 보조 지표 차트 추가 ---
            current_row = 2
            
            # RSI 차트
            if show_rsi:
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['RSI'], name='RSI', line=dict(color='orange', width=2)), row=current_row, col=1)
                # 과매수/과매도선
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="blue", row=current_row, col=1)
                fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
                current_row += 1
            
            # MACD 차트
            if show_macd:
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['MACD'], name='MACD', line=dict(color='blue', width=1.5)), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['Signal'], name='Signal', line=dict(color='orange', width=1.5)), row=current_row, col=1)
                # MACD 히스토그램 (막대그래프)
                colors = ['red' if val >= 0 else 'blue' for val in stock_df['MACD_Hist']]
                fig.add_trace(go.Bar(x=stock_df['Date'], y=stock_df['MACD_Hist'], name='MACD Hist', marker_color=colors, opacity=0.7), row=current_row, col=1)
                fig.update_yaxes(title_text="MACD", row=current_row, col=1)
                current_row += 1

            # 거래량 막대 그래프 추가 (항상 마지막 행)
            fig.add_trace(go.Bar(x=stock_df['Date'], y=stock_df['Volume'], name='거래량', marker_color='gray', opacity=0.5), row=current_row, col=1)
            fig.update_yaxes(title_text="거래량", row=current_row, col=1)
            
            # 레이아웃(크기, 여백, 아래 슬라이더 숨기기 등) 설정
            fig.update_layout(height=400 + (rows * 100), showlegend=True, xaxis_rangeslider_visible=False, margin=dict(t=20, b=20, l=20, r=20))
            fig.update_xaxes(tickformat="%Y-%m-%d") # 날짜 형식 지정
            st.plotly_chart(fig, use_container_width=True) # 화면에 차트 표시
            
            # --- 8. 테이블 포맷팅 (데이터 정리) ---
            st.markdown("### 📋 최근 10일 데이터")
            
            # 미국 주식 등에서 Change(변동률) 컬럼이 없는 경우 직접 계산
            # pct_change(): 전일 대비 몇 % 올랐는지(변동률) 계산합니다.
            if 'Change' not in stock_df.columns:
                # 종가(Close)를 기준으로 전일 대비 변동률 계산
                stock_df['Change'] = stock_df['Close'].pct_change()
            
            # 보여줄 열(Column) 선택
            display_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change']
            
            # 최신 날짜순으로 정렬 후 최근 10일치만 추출
            # 최근 날짜가 위로 오도록 정렬(ascending=False)하고 상위 10개만 추출
            df_disp = stock_df.sort_values(by='Date', ascending=False).head(10).copy()
            df_disp = df_disp[display_cols]
            
            # 한글화 및 스타일링
            # 영어로 된 열 이름을 한글로 바꿉니다.
            rename_map = {'Date':'날짜', 'Open':'시가', 'High':'고가', 'Low':'저가', 'Close':'종가', 'Volume':'거래량', 'Change':'변동률'}
            df_disp.rename(columns=rename_map, inplace=True)
            
            # 변동률 숫자에 따라 색깔을 넣는 함수 (양수면 빨강, 음수면 파랑)
            def color_change(val):
                if pd.isna(val): return ''
                return f'color: {"red" if val > 0 else "blue" if val < 0 else "black"}'

            # 한국 주식은 소수점 없이, 미국 주식은 소수점 2자리
            # 국가별 가격 형식(소수점 유무) 지정
            price_fmt = '{:,.0f}' if market_choice == "한국" else '{:,.2f}'
            
            # 화면에 예쁘게 표시하기 위한 포맷 설정 (날짜 형식, 천단위 콤마 등)
            fmt_dict = { 
                '날짜': lambda x: x.strftime('%Y-%m-%d'), 
                '시가': price_fmt, '고가': price_fmt, '저가': price_fmt, '종가': price_fmt, 
                '거래량': '{:,.0f}' 
            }
            if '변동률' in df_disp.columns:
                fmt_dict['변동률'] = '{:.2%}' # 백분율(%) 형식
            
            # st.dataframe: 데이터를 표 형식으로 보여주며, 스타일(색상 등)을 적용합니다.
            st.dataframe(df_disp.style.map(color_change, subset=['변동률'] if '변동률' in df_disp.columns else []).format(fmt_dict), use_container_width=True, hide_index=True)
            
            # --- 9. 엑셀 다운로드 기능 ---
            # BytesIO를 사용하여 물리적 파일을 만들지 않고 메모리 상에서 엑셀 파일을 생성합니다.
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # 엑셀 시트에 저장할 때는 다시 최신순으로 정렬하여 저장
                stock_df.sort_values(by='Date', ascending=False).to_excel(writer, index=False, sheet_name='Stock Data')
            # 다운로드 버튼 생성
            st.download_button(
                label=f"📥 {stock_input} 데이터 다운로드 (.xlsx)", 
                data=output.getvalue(), 
                file_name=f"{stock_input}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning(f"'{stock_input}' 종목을 찾을 수 없습니다. 다시 확인해 주세요.")
else:
    # 아무것도 조회하지 않았을 때 초기 화면 안내
    st.info("사이드바에서 조회 조건을 설정하고 '조회하기' 버튼을 눌러주세요.")
