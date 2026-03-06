import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import os
from drive_memo_handler import show_memo_ui

# 구글 드라이브 연동을 위한 전역 변수 설정
GOOGLE_DRIVE_FOLDER_ID = '1nv9imwPebStoOVJFWM5U6HIvAkib5xRY' # 메모 데이터 저장소

# ============================================================
# 📈 데이터 트레이더: 종목별 최적 매매 전략 분석 프로그램
#  데이터를 업로드하면 기술적 분석 + 매매 추천 + 백테스팅을 수행합니다.
# ============================================================

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="데이터 트레이더", page_icon="📈", layout="wide")

# --- CSS 커스텀 스타일 ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    [data-testid="stMetric"] { padding: 5px !important; }
    
    .signal-buy {
        background: linear-gradient(135deg, #ff416c, #ff4b2b);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 1.3rem; font-weight: bold;
        box-shadow: 0 4px 15px rgba(255,65,108,0.4);
    }
    .signal-sell {
        background: linear-gradient(135deg, #4158d0, #2196f3);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 1.3rem; font-weight: bold;
        box-shadow: 0 4px 15px rgba(65,88,208,0.4);
    }
    .signal-neutral {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 1.3rem; font-weight: bold;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
    }
    .score-card {
        background: white; padding: 12px; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin: 5px 0;
        border-left: 4px solid #667eea;
    }
    .backtest-result {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 데이터 트레이더: 종목별 최적 매매 전략 분석기")
st.caption("CSV 파일을 업로드하면 기술적 분석, 매수/매도 추천, 백테스팅 시뮬레이션을 수행합니다.")

# --- 공통 메모 기능 (구글 드라이브 연동) ---
show_memo_ui(GOOGLE_DRIVE_FOLDER_ID)

# --- 헬퍼 함수 ---
def draw_custom_metric(col, label, value, color="#31333F", help_text=""):
    """커스텀 HTML 지표 함수"""
    help_icon = f'<span style="cursor:help; margin-left:4px; font-size:0.7rem; color:#999;" title="{help_text}">❔</span>' if help_text else ""
    html_code = f'<div style="display:flex; flex-direction:column; align-items:flex-start; padding:5px;"><div style="display:flex; align-items:center; margin-bottom:2px;"><span style="font-size:0.8rem; color:#555; white-space:nowrap;">{label}</span>{help_icon}</div><span style="font-size:1.2rem; font-weight:bold; color:{color}; line-height:1.1; white-space:nowrap;">{value}</span></div>'
    col.markdown(html_code, unsafe_allow_html=True)


# ============================================================
# --- 2. CSV 파일 업로드 ---
# ============================================================
st.markdown("---")
st.markdown("### 📁 데이터 업로드")

uploaded_file = st.file_uploader(
    " 주식 데이터 파일을 업로드해 주세요 (CSV 또는 Excel)",
    type=['csv', 'xlsx', 'xls'],
    help="Date, Open, High, Low, Close, Volume 컬럼이 포함된 CSV 또는 Excel 파일"
)

def run_backtest(df_bt, strategy_name, capital, macd_hist_col='MACD_Hist'):
    """백테스팅 시뮬레이션 실행"""
    cash = capital
    shares = 0
    portfolio_values = []
    buy_hold_values = []
    trades = []
    
    if df_bt.empty:
        return [], [], []
        
    initial_price = df_bt.iloc[0]['Close']
    buy_hold_shares = capital / initial_price
    
    for i in range(len(df_bt)):
        row = df_bt.iloc[i]
        price = row['Close']
        signal = None
        
        # 전략별 신호 생성
        if strategy_name == "골든/데드크로스 전략":
            if row['Golden'] == True and cash > 0:
                signal = 'BUY'
            elif row['Death'] == True and shares > 0:
                signal = 'SELL'
                
        elif strategy_name == "RSI 전략":
            if not pd.isna(row['RSI']):
                if row['RSI'] <= 30 and cash > 0:
                    signal = 'BUY'
                elif row['RSI'] >= 70 and shares > 0:
                    signal = 'SELL'
                    
        elif strategy_name == "MACD 전략":
            if not pd.isna(row['MACD']) and not pd.isna(row['Signal']):
                macd_h = row[macd_hist_col] if not pd.isna(row[macd_hist_col]) else 0
                if i > 0:
                    prev_row = df_bt.iloc[i-1]
                    prev_h = prev_row[macd_hist_col] if macd_hist_col in prev_row.index and not pd.isna(prev_row[macd_hist_col]) else 0
                    if prev_h <= 0 and macd_h > 0 and cash > 0:
                        signal = 'BUY'
                    elif prev_h >= 0 and macd_h < 0 and shares > 0:
                        signal = 'SELL'
                        
        elif strategy_name == "종합 전략":
            buy_score = 0
            sell_score = 0
            
            if not pd.isna(row['RSI']):
                if row['RSI'] <= 30: buy_score += 1
                elif row['RSI'] >= 70: sell_score += 1
            
            if row['Golden'] == True: buy_score += 2
            elif row['Death'] == True: sell_score += 2
            
            if not pd.isna(row.get('MA20')) and not pd.isna(row.get('MA60')):
                if row['MA20'] > row['MA60']: buy_score += 1
                else: sell_score += 1
            
            if buy_score >= 2 and cash > 0:
                signal = 'BUY'
            elif sell_score >= 2 and shares > 0:
                signal = 'SELL'
        
        # --- 추가 전략 5가지 ---
        elif strategy_name == "볼린저 밴드 전략":
            if not pd.isna(row.get('BB_Lower')) and not pd.isna(row.get('BB_Upper')):
                if price <= row['BB_Lower'] and cash > 0:
                    signal = 'BUY'  # 하한 밴드 터치 → 매수
                elif price >= row['BB_Upper'] and shares > 0:
                    signal = 'SELL'  # 상한 밴드 터치 → 매도
        
        elif strategy_name == "MA 돌파 전략":
            if not pd.isna(row.get('MA20')):
                if i > 0:
                    prev_close = df_bt.iloc[i-1]['Close']
                    prev_ma20 = df_bt.iloc[i-1]['MA20'] if not pd.isna(df_bt.iloc[i-1].get('MA20')) else None
                    if prev_ma20 is not None:
                        # 종가가 MA20 위로 돌파 → 매수
                        if prev_close <= prev_ma20 and price > row['MA20'] and cash > 0:
                            signal = 'BUY'
                        # 종가가 MA20 아래로 이탈 → 매도
                        elif prev_close >= prev_ma20 and price < row['MA20'] and shares > 0:
                            signal = 'SELL'
        
        elif strategy_name == "거래량 급증 전략":
            if not pd.isna(row.get('Vol_MA20')) and row['Vol_MA20'] > 0:
                vol_ratio = row['Volume'] / row['Vol_MA20']
                is_bullish = row['Close'] > row['Open']  # 양봉
                is_bearish = row['Close'] < row['Open']  # 음봉
                if vol_ratio >= 2.0 and is_bullish and cash > 0:
                    signal = 'BUY'  # 거래량 2배 + 양봉 → 매수
                elif vol_ratio >= 2.0 and is_bearish and shares > 0:
                    signal = 'SELL'  # 거래량 2배 + 음봉 → 매도
        
        elif strategy_name == "터틀 트레이딩 전략":
            if not pd.isna(row.get('High_20')) and not pd.isna(row.get('Low_10')):
                if i > 0:
                    prev_high_20 = df_bt.iloc[i-1].get('High_20')
                    if not pd.isna(prev_high_20):
                        # 20일 최고가 돌파 → 매수
                        if price > prev_high_20 and cash > 0:
                            signal = 'BUY'
                        # 10일 최저가 이탈 → 매도
                        elif price < row['Low_10'] and shares > 0:
                            signal = 'SELL'
        
        elif strategy_name == "듀얼 모멘텀 전략":
            if not pd.isna(row.get('Mom_Short')) and not pd.isna(row.get('Mom_Long')):
                # 단기 + 장기 모멘텀 모두 양수 → 매수
                if row['Mom_Short'] > 0 and row['Mom_Long'] > 0 and cash > 0:
                    signal = 'BUY'
                # 단기 모멘텀이 음수로 전환 → 매도
                elif row['Mom_Short'] < 0 and shares > 0:
                    signal = 'SELL'
        
        # 매매 실행
        if signal == 'BUY' and cash > 0:
            shares = cash / price
            cash = 0
            trades.append({'Date': row['Date'], 'Type': '매수', 'Price': price, 'Shares': shares})
        elif signal == 'SELL' and shares > 0:
            cash = shares * price
            profit = cash - capital  # 총 수익
            trades.append({'Date': row['Date'], 'Type': '매도', 'Price': price, 'Shares': shares, 'Profit': profit})
            shares = 0
        
        # 포트폴리오 가치 기록
        portfolio_value = cash + (shares * price)
        portfolio_values.append(portfolio_value)
        buy_hold_values.append(buy_hold_shares * price)
    
    return portfolio_values, buy_hold_values, trades

if uploaded_file is not None:
    # CSV 파일 읽기
    try:
        # 파일 확장자에 따라 읽기 방식 분기
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date').reset_index(drop=True)
    except Exception as e:
        st.error(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
        st.stop()
    
    st.success(f"✅ 데이터 로드 완료! **{len(df)}개** 데이터 ({df['Date'].min().strftime('%Y-%m-%d')} ~ {df['Date'].max().strftime('%Y-%m-%d')})")
    
    # --- 기술 지표 보완 (혹시 없는 컬럼이 있으면 계산) ---
    if 'MA5' not in df.columns:
        df['MA5'] = df['Close'].rolling(window=5).mean()
    if 'MA10' not in df.columns:
        df['MA10'] = df['Close'].rolling(window=10).mean()
    if 'MA20' not in df.columns:
        df['MA20'] = df['Close'].rolling(window=20).mean()
    if 'MA60' not in df.columns:
        df['MA60'] = df['Close'].rolling(window=60).mean()
    
    if 'RSI' not in df.columns:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['RSI'] = 100 - (100 / (1 + rs))
    
    if 'MACD' not in df.columns:
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
    if 'Signal' not in df.columns:
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # MACD 히스토그램 (컬럼명이 MACD_His 또는 MACD_Hist일 수 있음)
    macd_hist_col = None
    for col_name in ['MACD_Hist', 'MACD_His', 'MACD_Histogram']:
        if col_name in df.columns:
            macd_hist_col = col_name
            break
    if macd_hist_col is None:
        df['MACD_Hist'] = df['MACD'] - df['Signal']
        macd_hist_col = 'MACD_Hist'
    
    if 'Golden' not in df.columns:
        df['Golden'] = (df['MA20'].shift(1) < df['MA60'].shift(1)) & (df['MA20'] > df['MA60'])
    if 'Death' not in df.columns:
        df['Death'] = (df['MA20'].shift(1) > df['MA60'].shift(1)) & (df['MA20'] < df['MA60'])
    
    if 'Change' not in df.columns:
        df['Change'] = df['Close'].pct_change()
    
    # Boolean 컬럼 변환 (문자열 'TRUE'/'FALSE' 처리)
    for col_name in ['Golden', 'Death']:
        if df[col_name].dtype == object:
            df[col_name] = df[col_name].str.upper().map({'TRUE': True, 'FALSE': False}).fillna(False)
    
    # --- 추가 기술 지표 계산 (백테스팅 전략용) ---
    # 볼린저 밴드 (20일 기준)
    if 'BB_Upper' not in df.columns:
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    
    # 터틀 트레이딩용 (20일 최고/최저, 10일 최저)
    if 'High_20' not in df.columns:
        df['High_20'] = df['High'].rolling(window=20).max()
        df['Low_10'] = df['Low'].rolling(window=10).min()
    
    # 거래량 이동평균 (20일)
    if 'Vol_MA20' not in df.columns:
        df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    
    # 듀얼 모멘텀용 수익률
    if 'Mom_Short' not in df.columns:
        df['Mom_Short'] = df['Close'].pct_change(periods=20)  # 단기 모멘텀 (20일)
        df['Mom_Long'] = df['Close'].pct_change(periods=60)   # 장기 모멘텀 (60일)
    
    # Adj Close 컬럼 처리
    adj_close_col = None
    for col_name in ['Adj Close', 'Adj_Close', 'AdjClose']:
        if col_name in df.columns:
            adj_close_col = col_name
            break
    
    # ============================================================
    # --- 3. 사이드바: 분석 설정 ---
    # ============================================================
    st.sidebar.header("⚙️ 분석 설정")
    
    # 기간 필터
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    
    date_range = st.sidebar.date_input(
        "분석 기간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtered = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)].copy()
    else:
        df_filtered = df.copy()
    
    # 차트 표시 옵션
    st.sidebar.subheader("📊 차트 옵션")
    show_ma = st.sidebar.checkbox("이동평균선 (MA) 표시", value=True)
    show_rsi = st.sidebar.checkbox("RSI 표시", value=True)
    show_macd = st.sidebar.checkbox("MACD 표시", value=True)
    show_volume = st.sidebar.checkbox("거래량 표시", value=True)
    
    # 백테스팅 옵션
    st.sidebar.subheader("🔬 백테스팅 설정")
    initial_capital = st.sidebar.number_input("초기 투자금 ($)", value=10000, min_value=1000, step=1000)
    backtest_strategy = st.sidebar.selectbox(
        "전략 선택",
        ["골든/데드크로스 전략", "RSI 전략", "MACD 전략", "종합 전략",
         "볼린저 밴드 전략", "MA 돌파 전략", "거래량 급증 전략",
         "터틀 트레이딩 전략", "듀얼 모멘텀 전략"]
    )
    
    if df_filtered.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        st.stop()
    
    # ============================================================
    # --- 4. 요약 지표 패널 ---
    # ============================================================
    st.markdown("### 📌 종합 요약 지표")
    
    latest = df_filtered.iloc[-1]
    prev = df_filtered.iloc[-2] if len(df_filtered) > 1 else latest
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # 현재가 & 변동
    current_price = latest['Close']
    price_change = latest['Change'] if not pd.isna(latest['Change']) else 0
    change_color = "#FF0000" if price_change >= 0 else "#2196F3"
    
    draw_custom_metric(col1, "현재가", f"${current_price:,.2f}", color="#FF0000",
                       help_text="가장 최근 종가입니다.")
    draw_custom_metric(col2, "변동률", f"{price_change:+.2%}", color=change_color,
                       help_text="전일 대비 변동률입니다.")
    draw_custom_metric(col3, "최고가", f"${df_filtered['High'].max():,.2f}",
                       help_text="선택 기간 내 최고가입니다.")
    draw_custom_metric(col4, "최저가", f"${df_filtered['Low'].min():,.2f}",
                       help_text="선택 기간 내 최저가입니다.")
    
    # RSI 상태
    rsi_val = latest['RSI']
    if not pd.isna(rsi_val):
        if rsi_val >= 70:
            rsi_status, rsi_color = "과매수 ⚠️", "#FF4B4B"
        elif rsi_val <= 30:
            rsi_status, rsi_color = "과매도 🔥", "#2CA02C"
        else:
            rsi_status, rsi_color = "중립", "#31333F"
        draw_custom_metric(col5, f"RSI ({rsi_status})", f"{rsi_val:.1f}", color=rsi_color,
                           help_text="14일 RSI. 70 이상 과매수(매도 고려), 30 이하 과매도(매수 고려)")
    else:
        draw_custom_metric(col5, "RSI", "N/A")
    
    # MACD 상태
    macd_val = latest['MACD']
    signal_val = latest['Signal']
    if not pd.isna(macd_val) and not pd.isna(signal_val):
        if macd_val > signal_val:
            macd_status, macd_color = "상승추세 📈", "#FF0000"
        else:
            macd_status, macd_color = "하락추세 📉", "#2196F3"
        draw_custom_metric(col6, f"MACD ({macd_status})", f"{macd_val:.2f}", color=macd_color,
                           help_text="MACD가 시그널 위에 있으면 상승추세, 아래면 하락추세")
    else:
        draw_custom_metric(col6, "MACD", "N/A")
    
    # 골든/데드크로스 정보
    st.markdown("")
    gc_col1, gc_col2, gc_col3, gc_col4 = st.columns(4)
    
    golden_dates = df_filtered[df_filtered['Golden'] == True]
    death_dates = df_filtered[df_filtered['Death'] == True]
    
    if not golden_dates.empty:
        last_golden = golden_dates.iloc[-1]['Date'].strftime('%Y-%m-%d')
        draw_custom_metric(gc_col1, "🔴 마지막 골든크로스", last_golden, color="#FF0000",
                           help_text="MA20이 MA60을 상향 돌파한 날 (매수 신호)")
    else:
        draw_custom_metric(gc_col1, "🔴 골든크로스", "해당 기간 없음", color="#999")
    
    if not death_dates.empty:
        last_death = death_dates.iloc[-1]['Date'].strftime('%Y-%m-%d')
        draw_custom_metric(gc_col2, "🔵 마지막 데드크로스", last_death, color="#2196F3",
                           help_text="MA20이 MA60을 하향 돌파한 날 (매도 신호)")
    else:
        draw_custom_metric(gc_col2, "🔵 데드크로스", "해당 기간 없음", color="#999")
    
    # 현재가 vs 이동평균 위치
    if not pd.isna(latest['MA20']):
        ma20_diff = ((current_price - latest['MA20']) / latest['MA20']) * 100
        ma20_color = "#FF0000" if ma20_diff > 0 else "#2196F3"
        draw_custom_metric(gc_col3, "현재가 vs MA20", f"{ma20_diff:+.2f}%", color=ma20_color,
                           help_text="현재가가 20일 이동평균 대비 얼마나 위/아래에 있는지")
    
    if not pd.isna(latest['MA60']):
        ma60_diff = ((current_price - latest['MA60']) / latest['MA60']) * 100
        ma60_color = "#FF0000" if ma60_diff > 0 else "#2196F3"
        draw_custom_metric(gc_col4, "현재가 vs MA60", f"{ma60_diff:+.2f}%", color=ma60_color,
                           help_text="현재가가 60일 이동평균 대비 얼마나 위/아래에 있는지")
    
    # ============================================================
    # --- 5. 종합 매매 추천 시스템 ---
    # ============================================================
    st.markdown("---")
    st.markdown("### 🤖 종합 매매 추천")
    
    # 점수 계산 (각 지표별 -2 ~ +2점)
    scores = {}
    explanations = {}
    
    # 1) RSI 기반
    if not pd.isna(rsi_val):
        if rsi_val <= 20:
            scores['RSI'] = 2
            explanations['RSI'] = f"RSI {rsi_val:.1f} → 극도의 과매도 구간! 강한 매수 신호"
        elif rsi_val <= 30:
            scores['RSI'] = 1
            explanations['RSI'] = f"RSI {rsi_val:.1f} → 과매도 구간, 반등 가능성"
        elif rsi_val >= 80:
            scores['RSI'] = -2
            explanations['RSI'] = f"RSI {rsi_val:.1f} → 극도의 과매수 구간! 강한 매도 신호"
        elif rsi_val >= 70:
            scores['RSI'] = -1
            explanations['RSI'] = f"RSI {rsi_val:.1f} → 과매수 구간, 조정 가능성"
        else:
            scores['RSI'] = 0
            explanations['RSI'] = f"RSI {rsi_val:.1f} → 중립 구간"
    
    # 2) MACD 기반
    if not pd.isna(macd_val) and not pd.isna(signal_val):
        macd_hist = latest[macd_hist_col] if not pd.isna(latest[macd_hist_col]) else macd_val - signal_val
        prev_macd_hist = prev[macd_hist_col] if macd_hist_col in prev.index and not pd.isna(prev[macd_hist_col]) else None
        
        if macd_val > signal_val:
            if prev_macd_hist is not None and prev_macd_hist <= 0 and macd_hist > 0:
                scores['MACD'] = 2
                explanations['MACD'] = "MACD 골든크로스 발생! 강한 매수 신호"
            else:
                scores['MACD'] = 1
                explanations['MACD'] = f"MACD({macd_val:.2f}) > 시그널({signal_val:.2f}) → 상승 추세"
        else:
            if prev_macd_hist is not None and prev_macd_hist >= 0 and macd_hist < 0:
                scores['MACD'] = -2
                explanations['MACD'] = "MACD 데드크로스 발생! 강한 매도 신호"
            else:
                scores['MACD'] = -1
                explanations['MACD'] = f"MACD({macd_val:.2f}) < 시그널({signal_val:.2f}) → 하락 추세"
    
    # 3) 이동평균 크로스
    if not pd.isna(latest.get('MA20')) and not pd.isna(latest.get('MA60')):
        if latest['Golden'] == True:
            scores['MA크로스'] = 2
            explanations['MA크로스'] = "오늘 골든크로스 발생! 중장기 상승 전환 신호"
        elif latest['Death'] == True:
            scores['MA크로스'] = -2
            explanations['MA크로스'] = "오늘 데드크로스 발생! 중장기 하락 전환 신호"
        elif latest['MA20'] > latest['MA60']:
            scores['MA크로스'] = 1
            explanations['MA크로스'] = "MA20 > MA60 → 상승 추세 유지"
        else:
            scores['MA크로스'] = -1
            explanations['MA크로스'] = "MA20 < MA60 → 하락 추세 유지"
    
    # 4) 가격 위치 (MA20 대비)
    if not pd.isna(latest.get('MA20')):
        price_vs_ma20 = ((current_price - latest['MA20']) / latest['MA20']) * 100
        if price_vs_ma20 > 5:
            scores['가격위치'] = -1
            explanations['가격위치'] = f"현재가가 MA20보다 {price_vs_ma20:.1f}% 위 → 단기 과열 가능"
        elif price_vs_ma20 < -5:
            scores['가격위치'] = 1
            explanations['가격위치'] = f"현재가가 MA20보다 {abs(price_vs_ma20):.1f}% 아래 → 반등 가능"
        else:
            scores['가격위치'] = 0
            explanations['가격위치'] = f"현재가가 MA20 근처 ({price_vs_ma20:+.1f}%) → 중립"
    
    # 5) 모멘텀 (최근 5일 방향성)
    if len(df_filtered) >= 5:
        recent_5 = df_filtered.tail(5)
        momentum = (recent_5.iloc[-1]['Close'] - recent_5.iloc[0]['Close']) / recent_5.iloc[0]['Close'] * 100
        if momentum > 3:
            scores['모멘텀'] = 1
            explanations['모멘텀'] = f"최근 5일 +{momentum:.1f}% 상승 → 단기 모멘텀 양호"
        elif momentum < -3:
            scores['모멘텀'] = -1
            explanations['모멘텀'] = f"최근 5일 {momentum:.1f}% 하락 → 단기 모멘텀 약세"
        else:
            scores['모멘텀'] = 0
            explanations['모멘텀'] = f"최근 5일 {momentum:+.1f}% → 방향성 불분명"
    
    # 종합 점수 계산
    total_score = sum(scores.values())
    max_possible = len(scores) * 2
    min_possible = len(scores) * -2
    
    # 추천 결정
    if total_score >= 3:
        recommendation = "🔴 강력 매수"
        rec_class = "signal-buy"
        rec_detail = "여러 기술 지표가 매수를 가리키고 있습니다. 적극적인 매수 진입을 고려해 보세요."
    elif total_score >= 1:
        recommendation = "🟠 매수 대기"
        rec_class = "signal-buy"
        rec_detail = "매수 신호가 우세하지만 확인이 필요합니다. 관망하며 추가 신호를 기다리세요."
    elif total_score <= -3:
        recommendation = "🔵 강력 매도"
        rec_class = "signal-sell"
        rec_detail = "여러 기술 지표가 매도를 가리키고 있습니다. 포지션 정리를 고려해 보세요."
    elif total_score <= -1:
        recommendation = "🟣 매도 대기"
        rec_class = "signal-sell"
        rec_detail = "매도 신호가 우세하지만 확인이 필요합니다. 손절라인을 설정해 두세요."
    else:
        recommendation = "⚪ 중립 (관망)"
        rec_class = "signal-neutral"
        rec_detail = "뚜렷한 방향이 없습니다. 추가 신호 발생 시까지 관망을 추천합니다."
    
    # 추천 표시
    st.markdown(f'<div class="{rec_class}">{recommendation}<br><span style="font-size:0.9rem; font-weight:normal;">{rec_detail}</span><br><span style="font-size:0.8rem; opacity:0.8;">종합 점수: {total_score} / {max_possible} (지표 {len(scores)}개 분석)</span></div>', unsafe_allow_html=True)
    
    # 세부 분석 표시
    with st.expander("📋 세부 분석 근거 보기"):
        for indicator, score in scores.items():
            score_emoji = "🟢" if score > 0 else "🔴" if score < 0 else "⚪"
            score_text = f"+{score}" if score > 0 else str(score)
            st.markdown(f'<div class="score-card"><strong>{score_emoji} {indicator}</strong> ({score_text}점) · {explanations[indicator]}</div>', unsafe_allow_html=True)
        
        st.markdown("")
        st.warning("⚠️ **주의**: 이 분석은 기술적 지표만을 기반으로 합니다. 실제 투자 결정 시 기업 실적, 시장 환경, 뉴스 등을 종합적으로 고려하세요. **투자의 책임은 본인에게 있습니다.**")
    
    # ============================================================
    # --- 6. 차트 시각화 ---
    # ============================================================
    st.markdown("---")
    st.markdown("### 📈 주가 및 보조지표 추이")
    
    # 서브플롯 구성
    rows = 1
    row_heights = [0.6]
    
    if show_rsi:
        rows += 1
        row_heights.append(0.13)
    if show_macd:
        rows += 1
        row_heights.append(0.13)
    if show_volume:
        rows += 1
        row_heights.append(0.14)
    
    # 비율 정규화
    total_h = sum(row_heights)
    row_heights = [h / total_h for h in row_heights]
    
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=row_heights
    )
    
    # 1행: 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=df_filtered['Date'], open=df_filtered['Open'],
        high=df_filtered['High'], low=df_filtered['Low'],
        close=df_filtered['Close'], name='주가',
        increasing_line_color='red', decreasing_line_color='blue'
    ), row=1, col=1)
    
    # 이동평균선
    if show_ma:
        ma_configs = [
            ('MA5', '#E377C2', 1, 'MA5'),
            ('MA10', '#FFD700', 1, 'MA10'),
            ('MA20', '#2CA02C', 1.5, 'MA20'),
            ('MA60', '#9467BD', 1.5, 'MA60'),
        ]
        for col_name, color, width, name in ma_configs:
            if col_name in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered['Date'], y=df_filtered[col_name],
                    name=name, line=dict(color=color, width=width)
                ), row=1, col=1)
    
    # 골든/데드크로스 신호
    buy_signals = df_filtered[df_filtered['Golden'] == True]
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals['Date'], y=buy_signals['Low'] * 0.98,
            mode='markers+text', name='매수신호 (골든크로스)',
            marker=dict(symbol='triangle-up', size=14, color='red'),
            text='매수', textposition='bottom center',
            textfont=dict(color='red', size=11, family='Arial Black')
        ), row=1, col=1)
    
    sell_signals = df_filtered[df_filtered['Death'] == True]
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals['Date'], y=sell_signals['High'] * 1.02,
            mode='markers+text', name='매도신호 (데드크로스)',
            marker=dict(symbol='triangle-down', size=14, color='blue'),
            text='매도', textposition='top center',
            textfont=dict(color='blue', size=11, family='Arial Black')
        ), row=1, col=1)
    
    current_row = 2
    
    # RSI 차트
    if show_rsi:
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'], y=df_filtered['RSI'],
            name='RSI', line=dict(color='orange', width=2)
        ), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="blue", row=current_row, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.05, row=current_row, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="blue", opacity=0.05, row=current_row, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
        current_row += 1
    
    # MACD 차트
    if show_macd:
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'], y=df_filtered['MACD'],
            name='MACD', line=dict(color='blue', width=1.5)
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'], y=df_filtered['Signal'],
            name='Signal', line=dict(color='orange', width=1.5)
        ), row=current_row, col=1)
        
        hist_colors = ['red' if val >= 0 else 'blue' for val in df_filtered[macd_hist_col]]
        fig.add_trace(go.Bar(
            x=df_filtered['Date'], y=df_filtered[macd_hist_col],
            name='MACD Hist', marker_color=hist_colors, opacity=0.7
        ), row=current_row, col=1)
        fig.update_yaxes(title_text="MACD", row=current_row, col=1)
        current_row += 1
    
    # 거래량 차트
    if show_volume:
        vol_colors = ['red' if df_filtered.iloc[i]['Close'] >= df_filtered.iloc[i]['Open'] else 'blue'
                      for i in range(len(df_filtered))]
        fig.add_trace(go.Bar(
            x=df_filtered['Date'], y=df_filtered['Volume'],
            name='거래량', marker_color=vol_colors, opacity=0.5
        ), row=current_row, col=1)
        fig.update_yaxes(title_text="거래량", row=current_row, col=1)
    
    fig.update_layout(
        height=500 + (rows * 100),
        showlegend=True,
        xaxis_rangeslider_visible=False,
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(tickformat="%Y-%m-%d")
    st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # --- 7. 백테스팅 시뮬레이션 (요약 비교표 포함) ---
    # ============================================================
    st.markdown("---")
    
    # --- 전략별 백테스팅 요약 비교표 (백테스팅 섹션 상단으로 이동) ---
    st.markdown("#### 📊 전략별 백테스팅 요약 결과")
    all_strategies = [
        "골든/데드크로스 전략", "RSI 전략", "MACD 전략", "종합 전략",
        "볼린저 밴드 전략", "MA 돌파 전략", "거래량 급증 전략",
        "터틀 트레이딩 전략", "듀얼 모멘텀 전략"
    ]
    
    summary_results = []
    for strat in all_strategies:
        p_vals, b_vals, t_list = run_backtest(df_filtered, strat, initial_capital, macd_hist_col)
        if p_vals:
            final_p = p_vals[-1]
            final_b = b_vals[-1]
            strat_ret = ((final_p - initial_capital) / initial_capital) * 100
            bh_ret = ((final_b - initial_capital) / initial_capital) * 100
            diff = strat_ret - bh_ret
            summary_results.append({
                "전략명": strat,
                "전략 수익율(%)": strat_ret,
                "매수.보유 수익율(Buy&Hold)": bh_ret,
                "초과수익율": diff,
                "총거래 회수": len(t_list)
            })
            
    if summary_results:
        df_summary = pd.DataFrame(summary_results).sort_values(by="전략 수익율(%)", ascending=False)
        
        # 포맷팅: 소수점 2자리 + % 기호 적용
        fmt_cols = ["전략 수익율(%)", "매수.보유 수익율", "초과수익율"]
        
        # 스타일링을 위한 함수
        def highlight_max(s):
            is_max = s == s.max()
            return ['background-color: rgba(255, 65, 108, 0.2); font-weight: bold' if v else '' for v in is_max]

        st.dataframe(
            df_summary.style.format({c: "{:+.2f}%" for c in fmt_cols})
            .apply(highlight_max, subset=["전략 수익율(%)", "초과수익율"]),
            use_container_width=True, hide_index=True
        )

    st.markdown("### 📊 백테스팅 시뮬레이션")
    st.caption(f"전략: **{backtest_strategy}** · 초기 투자금: **${initial_capital:,}**")
    
    # 백테스팅 실행 (상세 차트용)
    portfolio_values, buy_hold_values, trades = run_backtest(df_filtered, backtest_strategy, initial_capital, macd_hist_col)
    
    # 결과 계산
    final_portfolio = portfolio_values[-1]
    final_buyhold = buy_hold_values[-1]
    strategy_return = ((final_portfolio - initial_capital) / initial_capital) * 100
    buyhold_return = ((final_buyhold - initial_capital) / initial_capital) * 100
    
    # 결과 표시
    bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
    
    s_color = "#FF0000" if strategy_return >= 0 else "#2196F3"
    b_color = "#FF0000" if buyhold_return >= 0 else "#2196F3"
    diff_return = strategy_return - buyhold_return
    d_color = "#FF0000" if diff_return >= 0 else "#2196F3"
    
    draw_custom_metric(bt_col1, f"📌 {backtest_strategy} 수익률", f"{strategy_return:+.2f}%", color=s_color)
    draw_custom_metric(bt_col2, "📌 매수-보유 수익률", f"{buyhold_return:+.2f}%", color=b_color)
    draw_custom_metric(bt_col3, "📌 전략 vs 매수보유", f"{diff_return:+.2f}%p", color=d_color,
                       help_text="양수면 전략이 더 좋은 성과, 음수면 단순 보유가 더 좋은 성과")
    draw_custom_metric(bt_col4, "📌 총 거래 횟수", f"{len(trades)}회")
    
    # 백테스팅 차트
    fig_bt = go.Figure()
    fig_bt.add_trace(go.Scatter(
        x=df_filtered['Date'], y=portfolio_values,
        name=f'{backtest_strategy}', line=dict(color='#FF416C', width=2),
        fill='tozeroy', fillcolor='rgba(255,65,108,0.1)'
    ))
    fig_bt.add_trace(go.Scatter(
        x=df_filtered['Date'], y=buy_hold_values,
        name='매수-보유 전략', line=dict(color='#4158D0', width=2, dash='dash'),
        fill='tozeroy', fillcolor='rgba(65,88,208,0.05)'
    ))
    
    # 매매 시점 표시
    for trade in trades:
        color = 'red' if trade['Type'] == '매수' else 'blue'
        symbol = 'triangle-up' if trade['Type'] == '매수' else 'triangle-down'
        idx = df_filtered[df_filtered['Date'] == trade['Date']].index
        if len(idx) > 0:
            idx_pos = idx[0] - df_filtered.index[0]
            if 0 <= idx_pos < len(portfolio_values):
                fig_bt.add_trace(go.Scatter(
                    x=[trade['Date']], y=[portfolio_values[idx_pos]],
                    mode='markers', name=trade['Type'],
                    marker=dict(symbol=symbol, size=12, color=color),
                    showlegend=False
                ))
    
    fig_bt.update_layout(
        height=400,
        title=f"💰 포트폴리오 가치 변화 (${initial_capital:,} 시작)",
        yaxis_title="포트폴리오 가치 ($)",
        showlegend=True,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bt, use_container_width=True)
    
    # 거래 내역 표시
    if trades:
        with st.expander(f"📝 거래 내역 ({len(trades)}건)"):
            df_trades = pd.DataFrame(trades)
            df_trades['Date'] = pd.to_datetime(df_trades['Date']).dt.strftime('%Y-%m-%d')
            df_trades['Price'] = df_trades['Price'].apply(lambda x: f"${x:,.2f}")
            df_trades['Shares'] = df_trades['Shares'].apply(lambda x: f"{x:,.4f}")
            st.dataframe(df_trades, use_container_width=True, hide_index=True)
    
    # ============================================================
    # --- 8. 데이터 테이블 ---
    # ============================================================
    st.markdown("---")
    st.markdown("### 📋 최근 데이터")
    
    # 표시할 컬럼 선택
    display_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'RSI', 'MACD', 'Signal', 'Change']
    available_cols = [c for c in display_cols if c in df_filtered.columns]
    
    df_disp = df_filtered.sort_values(by='Date', ascending=False).head(20).copy()
    df_disp = df_disp[available_cols]
    
    # 한글화
    rename_map = {
        'Date': '날짜', 'Open': '시가', 'High': '고가', 'Low': '저가',
        'Close': '종가', 'Volume': '거래량', 'RSI': 'RSI',
        'MACD': 'MACD', 'Signal': '시그널', 'Change': '변동률'
    }
    df_disp.rename(columns=rename_map, inplace=True)
    
    # 색상 함수
    def color_change(val):
        if pd.isna(val): return ''
        return f'color: {"red" if val > 0 else "blue" if val < 0 else "black"}'
    
    fmt_dict = {
        '날짜': lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x),
        '시가': '${:,.2f}', '고가': '${:,.2f}', '저가': '${:,.2f}', '종가': '${:,.2f}',
        '거래량': '{:,.0f}'
    }
    if '변동률' in df_disp.columns:
        fmt_dict['변동률'] = '{:.2%}'
    if 'RSI' in df_disp.columns:
        fmt_dict['RSI'] = '{:.1f}'
    if 'MACD' in df_disp.columns:
        fmt_dict['MACD'] = '{:.2f}'
    if '시그널' in df_disp.columns:
        fmt_dict['시그널'] = '{:.2f}'
    
    change_cols = [c for c in ['변동률'] if c in df_disp.columns]
    st.dataframe(
        df_disp.style.map(color_change, subset=change_cols).format(fmt_dict),
        use_container_width=True, hide_index=True
    )
    
    # ============================================================
    # --- 9. 엑셀 다운로드 ---
    # ============================================================
    st.markdown("---")
    dcol1, dcol2 = st.columns(2)
    
    # CSV 다운로드
    with dcol1:
        csv_buffer = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 분석 데이터 다운로드 (.csv)",
            data=csv_buffer,
            file_name=f"google_stock_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # 엑셀 다운로드
    with dcol2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered.sort_values(by='Date', ascending=False).to_excel(
                writer, index=False, sheet_name='Stock Data'
            )
            if trades:
                pd.DataFrame(trades).to_excel(writer, index=False, sheet_name='Trades')
        st.download_button(
            label="📥 분석 데이터 다운로드 (.xlsx)",
            data=output.getvalue(),
            file_name=f"google_stock_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # ============================================================
    # --- 10. 투자 가이드 ---
    # ============================================================
    with st.expander("📖 기술적 지표 해설 가이드"):
        st.markdown("""
        ### 📊 지표별 상세 가이드
        
        #### 1. 이동평균선 (Moving Average)
        - **MA5/MA10**: 단기 추세 (5일/10일 평균가)
        - **MA20**: 중기 추세 (약 1달). 주가가 이 위에 있으면 상승 추세
        - **MA60**: 장기 추세 (약 3달). 기관투자자들이 주로 참고
        - **골든크로스**: MA20이 MA60을 상향 돌파 → 📈 **매수 신호**
        - **데드크로스**: MA20이 MA60을 하향 돌파 → 📉 **매도 신호**
        
        #### 2. RSI (상대강도지수)
        - **범위**: 0 ~ 100
        - **30 이하**: 과매도 구간 → 반등 가능성 (매수 고려) 🔵
        - **70 이상**: 과매수 구간 → 조정 가능성 (매도 고려) 🔴
        - **50 근처**: 중립, 방향성 판단 어려움
        
        #### 3. MACD (이동평균수렴확산)
        - **MACD > 시그널**: 상승 추세 📈
        - **MACD < 시그널**: 하락 추세 📉
        - **히스토그램**: MACD와 시그널의 차이. 양(+)이면 상승 모멘텀
        
        #### 4. 거래량 (Volume)
        - 주가 상승 + 거래량 증가 = 강한 상승 추세 확인
        - 주가 상승 + 거래량 감소 = 상승세 약화 가능
        
        ---
        ### 🔬 백테스팅 전략 가이드
        
        #### 5. 볼린저 밴드 전략
        - **매수**: 주가가 하한 밴드(MA20 - 2σ) 아래로 내려갈 때
        - **매도**: 주가가 상한 밴드(MA20 + 2σ) 위로 올라갈 때
        - **특징**: 역추세 전략. 과매수/과매도 구간에서 평균 회귀를 노림
        
        #### 6. MA 돌파 전략
        - **매수**: 종가가 MA20 위로 돌파하는 순간
        - **매도**: 종가가 MA20 아래로 이탈하는 순간
        - **특징**: 추세 전환 초기를 포착. 신호가 비교적 빈번
        
        #### 7. 거래량 급증 전략
        - **매수**: 거래량이 20일 평균의 2배 이상이면서 양봉(종가 > 시가)일 때
        - **매도**: 거래량이 20일 평균의 2배 이상이면서 음봉일 때
        - **특징**: 기관/세력의 대량 매수/매도를 포착하는 전략
        
        #### 8. 터틀 트레이딩 전략
        - **매수**: 주가가 20일 최고가를 돌파할 때
        - **매도**: 주가가 10일 최저가를 이탈할 때
        - **특징**: 전설적인 추세 추종 전략. 큰 추세에서 높은 수익을 기대
        
        #### 9. 듀얼 모멘텀 전략
        - **매수**: 단기(20일) + 장기(60일) 수익률이 모두 양수일 때
        - **매도**: 단기 모멘텀이 음수로 전환될 때
        - **특징**: 상승 모멘텀이 확인된 종목에만 투자하는 보수적 전략
        
        ---
        ⚠️ **투자 주의사항**: 기술적 분석은 과거 데이터 기반의 통계적 도구입니다. 
        100% 정확한 예측은 불가능하며, 반드시 기본적 분석(실적, 산업 동향)과 
        함께 사용하세요. **투자의 최종 결정과 책임은 투자자 본인에게 있습니다.**
        """)

else:
    # 파일 미업로드 시 안내
    st.markdown("---")
    st.info("👆 위에서 CSV 파일을 업로드하면 분석이 시작됩니다!")
    
    with st.expander("📋 CSV 파일 형식 예시"):
        st.markdown("""
        CSV 파일에는 아래 컬럼들이 포함되어야 합니다:
        
        **필수 컬럼:**
        | 컬럼명 | 설명 | 예시 |
        |--------|------|------|
        | Date | 날짜 | 2026-03-03 |
        | Open | 시가 | 298.59 |
        | High | 고가 | 303.94 |
        | Low | 저가 | 296.71 |
        | Close | 종가 | 303.58 |
        | Volume | 거래량 | 35437900 |
        
        **선택 컬럼 (없으면 자동 계산):**
        - MA5, MA10, MA20, MA60 (이동평균)
        - RSI (상대강도지수)
        - MACD, Signal, MACD_Hist (MACD 관련)
        - Golden, Death (골든/데드크로스)
        - Change (변동률)
        """)
