import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

# --- 헬퍼 함수: 지표 직접 그리기 (색상 강조용) ---
def draw_custom_metric(col, label, value, color="#31333F", help_text=""):
    """
    st.metric 대신 사용하는 커스텀 HTML 지표 함수입니다.
    색상을 확실하게 강제하기 위해 사용합니다.
    """
    html_code = f"""
    <div style="display: flex; flex-direction: column; align-items: flex-start; padding: 5px;">
        <span style="font-size: 0.8rem; color: #555; margin-bottom: 2px;" title="{help_text}">{label}</span>
        <span style="font-size: 1.5rem; font-weight: bold; color: {color}; line-height: 1.2;">{value}</span>
    </div>
    """
    col.markdown(html_code, unsafe_allow_html=True)

# st.info: 사용자에게 파란색 박스로 안내 메시지를 표시합니다.
st.info("💡 **이용 가이드**: 사이드바에서 국가를 선택한 후 종목명이나 티커(예: 삼성전자, AAPL)를 입력하고 '조회하기' 버튼을 누르세요.")

# --- 2. 종목 매핑을 위한 데이터 로딩 (한국 & 미국) ---
# @st.cache_data: 데이터를 한 번 불러오면 메모리에 저장(캐싱)하여, 다음에 조회할 때 속도를 훨씬 빠르게 만듭니다.
@st.cache_data
def load_stock_list(market_type):
    """
    선택한 국가(시장)의 상장 종목 목록을 가져오는 함수입니다.
    market_type: "한국" 또는 "미국"
    """
    if market_type == "한국":
        # KRX-DESC: 한국 거래소의 종목 이름과 코드를 포함한 상세 리스트를 가져옵니다.
        return fdr.StockListing('KRX-DESC')
    else:
        # 미국 시장 (NASDAQ, NYSE) 통합 리스트 구성
        # st.spinner: 데이터를 불러오는 동안 '로딩 중' 메시지를 화면에 보여줍니다.
        with st.spinner('미국 상장 종목 목록을 불러오는 중입니다... 처음 한 번만 실행됩니다.'):
            # NASDAQ과 NYSE 시장의 종목 정보를 각각 가져옵니다.
            df_nasdaq = fdr.StockListing('NASDAQ')
            df_nyse = fdr.StockListing('NYSE')
            # 필요한 최소 컬럼('Symbol': 티커, 'Name': 회사명)만 골라서 하나로 합칩니다.
            cols = ['Symbol', 'Name']
            df_us = pd.concat([df_nasdaq[cols], df_nyse[cols]], ignore_index=True)
            # 중복된 티커가 있을 경우 첫 번째 것만 남기고 제거합니다.
            df_us = df_us.drop_duplicates(subset=['Symbol'])
            return df_us

# --- 3. 사이드바 UI 구성 ---
# st.sidebar.form: 왼쪽 사이드바에 입력 폼을 만듭니다. 버튼을 누르기 전까지는 코드가 실행되지 않도록 막아줍니다.
with st.sidebar.form("search_form"):
    st.header("🔍 검색 설정")
    
    # st.radio: 선택지를 제공합니다. (한국/미국 중 하나 선택)
    market_choice = st.radio("국가 선택", ["한국", "미국"], horizontal=True)
    
    # 위에서 정의한 함수를 사용하여 종목 리스트를 미리 로드합니다.
    df_listing = load_stock_list(market_choice)
    
    # st.text_input: 사용자가 텍스트(종목명 또는 코드)를 입력할 수 있는 칸입니다.
    default_input = "삼성전자" if market_choice == "한국" else "AAPL"
    stock_input = st.text_input("종목명 또는 티커 입력", value=default_input)

    # st.date_input: 달력 모양의 입력을 통해 날자로 범위를 설정합니다.
    # 오늘(datetime.today())로부터 1년 전(timedelta(days=365))을 기본값으로 설정합니다.
    default_end = datetime.today().date()
    default_start = default_end - timedelta(days=365)
    start_date = st.date_input("시작일", value=default_start)
    end_date = st.date_input("종료일", value=default_end)
    
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
            
            # --- 7. 이동평균선(MA) 및 매매 신호 계산 ---
            # rolling(window=N).mean(): 최근 N일간의 종가 평균을 계산합니다.
            stock_df['MA5'] = stock_df['Close'].rolling(window=5).mean()
            stock_df['MA10'] = stock_df['Close'].rolling(window=10).mean()
            stock_df['MA20'] = stock_df['Close'].rolling(window=20).mean()
            stock_df['MA60'] = stock_df['Close'].rolling(window=60).mean()

            # 골든크로스 & 데드크로스 신호 판별 (20일선 vs 60일선)
            # shift(1): 전날 데이터를 가져옵니다.
            # 골든크로스: 전날에는 20일선이 아래였는데, 오늘 위로 올라온 경우
            stock_df['Golden'] = (stock_df['MA20'].shift(1) < stock_df['MA60'].shift(1)) & (stock_df['MA20'] > stock_df['MA60'])
            # 데드크로스: 전날에는 20일선이 위였는데, 오늘 아래로 내려온 경우
            stock_df['Death'] = (stock_df['MA20'].shift(1) > stock_df['MA60'].shift(1)) & (stock_df['MA20'] < stock_df['MA60'])

            # --- 8. Plotly 차트 (캔들스틱 + 이동평균선 + 매매신호 + 거래량) ---
            st.markdown("### 📈 주가 및 거래량 추이")
            # 2개의 행(차트 2층)을 가지는 서브플롯을 만듭니다. (7:3 비율)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # 캔들스틱 차트 추가 (주가의 시가, 고가, 저가, 종가를 한눈에 표시)
            fig.add_trace(go.Candlestick(
                x=stock_df['Date'], open=stock_df['Open'], high=stock_df['High'], 
                low=stock_df['Low'], close=stock_df['Close'], name='주가',
                increasing_line_color='red', decreasing_line_color='blue' # 한국식 색상 적용(상승 빨강, 하락 파랑)
            ), row=1, col=1)

            # 이동평균선들을 차트에 추가합니다.
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
            
            # 거래량 막대 그래프 추가
            fig.add_trace(go.Bar(x=stock_df['Date'], y=stock_df['Volume'], name='거래량', marker_color='gray', opacity=0.5), row=2, col=1)
            
            # 레이아웃(크기, 여백, 아래 슬라이더 숨기기 등) 설정
            fig.update_layout(height=600, showlegend=True, xaxis_rangeslider_visible=False, margin=dict(t=20, b=20, l=20, r=20))
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
