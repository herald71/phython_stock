import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import os
import time
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 프로그램 명칭 : S&P 500 수익률 분석기 PRO
# 주요 기능     : S&P 500 종목들의 기간별 수익률을 분석하고 시각화합니다.
# 작성자        : Antigravity AI
# ============================================================

# --- 1. 페이지 설정 (브라우저 탭에 표시될 정보) ---
st.set_page_config(
    page_title="S&P 500 수익률 분석기 PRO",
    page_icon="🇺🇸",
    layout="wide"  # 화면을 넓게 사용하도록 설정합니다.
)

# --- 2. 디자인 꾸미기 (CSS) ---
# 대시보드를 더 고급스럽게 만들기 위해 스타일을 적용합니다.
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa; /* 배경색을 아주 연한 회색으로 */
    }
    .stMetric {
        background-color: white; /* 지표 카드 배경을 흰색으로 */
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); /* 부드러운 그림자 효과 */
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #0d6efd; /* 기본 버튼 색상을 파란색으로 */
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 상수 정의 및 환경 설정 ---
CSV_FILE = 'sp500_tickers_detailed.csv'  # 종목 정보가 담긴 기본 파일
DATA_DIR = 'data/sp500'                  # 각 종목의 가격 데이터(.csv)가 저장될 디렉토리

# 데이터 저장 폴더가 없으면 새로 생성합니다.
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 4. 데이터 로딩 함수 ---
# @st.cache_data를 사용하여 이미 읽은 데이터는 캐시에 저장해 속도를 높입니다.
@st.cache_data
def load_info_data():
    """S&P 500 종목 기본 정보(티커, 회사명, 섹터 등)를 불러옵니다."""
    if not os.path.exists(CSV_FILE):
        return None
    try:
        df = pd.read_csv(CSV_FILE)
        return df
    except Exception as e:
        st.error(f"CSV 파일을 읽는 중 오류 발생: {e}")
        return None

# 종목 정보를 불러와 df_info에 저장합니다.
df_info = load_info_data()

# --- 5. 주요 로직 함수들 ---

def run_update_data(df_info):
    """
    각 종목의 과거 가격 데이터를 최신으로 업데이트하는 함수입니다.
    FinanceDataReader를 사용해 S&P 500 주식 데이터를 수집합니다.
    """
    progress_bar = st.progress(0) # 진행률 표시줄
    status_text = st.empty()      # 상태 메시지 표시 공간
    
    total_items = len(df_info)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 작업 시작 시간
    start_time = time.time()
    
    for idx, row in df_info.iterrows():
        ticker, name = row['Ticker'], row['Company']
        if pd.isna(ticker):
            continue
            
        file_path = f"{DATA_DIR}/{ticker}.csv"
        need_download = False
        start_date_download = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d") # 기본 2년치
        end_date_download = today_str
        existing_df = None

        # 이미 파일이 있다면 마지막 날짜 이후의 데이터만 추가로 받습니다. (증분 업데이트)
        if os.path.exists(file_path):
            try:
                existing_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                if not existing_df.empty:
                    last_date = existing_df.index[-1]
                    next_date = last_date + timedelta(days=1)
                    # 내일 날짜가 오늘보다 작거나 같으면 업데이트 필요
                    if next_date.date() < datetime.now().date():
                        start_date_download = next_date.strftime("%Y-%m-%d")
                        need_download = True
            except:
                need_download = True
        else:
            need_download = True

        if need_download:
            status_text.text(f"📥 데이터를 가져오는 중: {name} ({ticker}) [{idx+1}/{total_items}]")
            try:
                # FinanceDataReader로 주식 정보 조회
                new_df = fdr.DataReader(ticker, start_date_download, end_date_download)
                if not new_df.empty:
                    if existing_df is not None and not existing_df.empty:
                        # 기존 데이터와 새 데이터를 합치고 중복을 제거합니다.
                        combined_df = pd.concat([existing_df, new_df])
                        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                        combined_df.to_csv(file_path)
                    else:
                        new_df.to_csv(file_path)
                # API 호출 사이의 짧은 대기 (과부하 방지)
                time.sleep(0.05)
            except Exception as e:
                st.warning(f"⚠️ {name}({ticker}) 다운로드 실패: {e}")
        
        # 진행률 업데이트
        progress_bar.progress((idx + 1) / total_items)
        
    end_time = time.time()
    status_text.success(f"✅ 모든 데이터가 최신 상태로 업데이트되었습니다! (소요 시간: {int(end_time - start_time)}초)")
    time.sleep(3)
    status_text.empty()
    progress_bar.empty()

def calculate_returns(df_info, mode, period_days, start_date, end_date, target_sector):
    """
    선택한 모드와 기간에 맞춰 모든 종목의 수익률을 계산합니다.
    """
    results = []
    
    # 분석 시작일과 종료일 설정
    if mode == "최근 일수 기준":
        calc_start_date = pd.Timestamp(datetime.now() - timedelta(days=period_days))
        calc_end_date = pd.Timestamp(datetime.now())
    else:
        calc_start_date = pd.Timestamp(start_date)
        calc_end_date = pd.Timestamp(end_date)
    
    for _, row in df_info.iterrows():
        ticker = row['Ticker']
        sector = row.get('Sector', 'Unknown')
        
        # 섹터 필터 적용
        if target_sector != "전체 섹터" and str(sector) != target_sector:
            continue
            
        file_path = f"{DATA_DIR}/{ticker}.csv"
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                # 기간 내 데이터만 필터링
                df_filtered = df[(df.index >= calc_start_date) & (df.index <= calc_end_date)]
                
                if len(df_filtered) >= 2: # 최소 시작일과 종료일 데이터가 있어야 함
                    start_price = df_filtered.iloc[0]['Close']
                    end_price = df_filtered.iloc[-1]['Close']
                    
                    if start_price > 0:
                        # 수익률 공식: ((종료가 - 시작가) / 시작가) * 100
                        return_rate = ((end_price - start_price) / start_price) * 100
                        results.append({
                            '티커': ticker,
                            '종목명': row['Company'],
                            '섹터': sector,
                            '시작일가': round(start_price, 2),
                            '종료일가': round(end_price, 2),
                            '수익률(%)': round(return_rate, 2)
                        })
            except:
                continue
                    
    return pd.DataFrame(results)

# --- 6. 사이드바 (사용자 입력 설정) ---
with st.sidebar:
    st.title("⚙️ 분석 설정")
    
    if df_info is None:
        st.error(f"❌ '{CSV_FILE}' 파일이 없습니다.")
        st.stop()
        
    # 데이터 업데이트 단추
    if st.button("🔄 데이터 최신화 (Yahoo Finance)"):
        run_update_data(df_info)
        
    st.divider()
    
    # 1) 분석 기간 선택 방식 (라디오 버튼)
    analysis_mode = st.radio("분석 모드", ["최근 일수 기준", "직접 날짜 지정"])
    
    if analysis_mode == "최근 일수 기준":
        # 슬라이더로 기간 선택
        period_days = st.select_slider(
            "분석 기간 (일)",
            options=[1, 7, 30, 90, 180, 365, 730],
            value=30
        )
        start_date, end_date = None, None
    else:
        # 달력으로 날짜 선택
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("종료일", datetime.now())
        period_days = 0
        
    # 2) 섹터 필터 선택
    sectors = ["전체 섹터"] + sorted(df_info['Sector'].dropna().unique().tolist())
    target_sector = st.selectbox("S&P 500 섹터 필터", sectors)
    
    # 3) 분석 실행 버튼
    analyze_btn = st.button("🚀 수익률 분석 시작", type="primary")

# --- 7. 메인 화면 ---
st.title("🇺🇸 S&P 500 수익률 분석기 PRO")
st.markdown("전 세계 자본의 중심, S&P 500 기업들의 수익률을 한눈에 분석하세요.")

if analyze_btn:
    # 실행 중일 때 로딩 표시
    with st.spinner("데이터를 열심히 분석 중입니다... 잠시만 기다려 주세요!"):
        df_results = calculate_returns(df_info, analysis_mode, period_days, start_date, end_date, target_sector)
        
        if not df_results.empty:
            # --- 결과 표시: TOP 10 종목 ---
            st.subheader(f"🏆 수익률 상위 TOP 10 종목 ({target_sector})")
            top_10 = df_results.sort_values(by='수익률(%)', ascending=False).head(10)
            
            # 수익률 1위 종목을 돋보이게 표시 (메트릭 카드)
            best_stock = top_10.iloc[0]
            st.metric(
                label=f"🥇 오늘의 수익률 1위: {best_stock['종목명']} ({best_stock['티커']})", 
                value=f"{best_stock['수익률(%)']}%", 
                delta=f"${round(best_stock['종료일가'] - best_stock['시작일가'], 2)}"
            )
            
            # 테이블로 데이터 시각화
            # 종목명에 Yahoo Finance 링크 추가
            top_10['상세페이지'] = top_10['티커'].apply(lambda x: f"https://finance.yahoo.com/quote/{x}")
            
            st.dataframe(
                top_10[['상세페이지', '티커', '종목명', '섹터', '시작일가', '종료일가', '수익률(%)']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                    "시작일가": st.column_config.NumberColumn(format="$%.2f"),
                    "종료일가": st.column_config.NumberColumn(format="$%.2f"),
                    "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
                }
            )
            
            # --- 결과 표시: BOTTOM 10 종목 ---
            st.divider()
            st.subheader(f"📉 수익률 하위 BOTTOM 10 종목 ({target_sector})")
            bottom_10 = df_results.sort_values(by='수익률(%)', ascending=True).head(10)
            
            # 수익률 최하위 종목 표시 (메트릭 카드)
            worst_stock = bottom_10.iloc[0]
            st.metric(
                label=f"⚠️ 오늘의 하락 1위: {worst_stock['종목명']} ({worst_stock['티커']})", 
                value=f"{worst_stock['수익률(%)']}%", 
                delta=f"${round(worst_stock['종료일가'] - worst_stock['시작일가'], 2)}"
            )
            
            # 테이블로 데이터 시각화
            bottom_10['상세페이지'] = bottom_10['티커'].apply(lambda x: f"https://finance.yahoo.com/quote/{x}")
            
            st.dataframe(
                bottom_10[['상세페이지', '티커', '종목명', '섹터', '시작일가', '종료일가', '수익률(%)']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                    "시작일가": st.column_config.NumberColumn(format="$%.2f"),
                    "종료일가": st.column_config.NumberColumn(format="$%.2f"),
                    "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
                }
            )
            
            # --- 결과 표시: 그래프 시각화 (Plotly 사용) ---
            st.divider()
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📊 수익률 분포 현황")
                # 0% 기준으로 양수/음수 구분 컬럼 추가
                df_results['구분'] = df_results['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
                fig_dist = px.histogram(
                    df_results, 
                    x="수익률(%)", 
                    nbins=40, 
                    color='구분',
                    color_discrete_map={'상승': '#ef5350', '하락': '#0d6efd'}, # 상승: 빨간색, 하락: 파란색
                    barmode='overlay'
                )
                # 0% 기준선 추가
                fig_dist.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="0%")
                st.plotly_chart(fig_dist, use_container_width=True)
                
            with col_chart2:
                if target_sector == "전체 섹터":
                    st.subheader("🏢 섹터별 평균 수익률")
                    sector_avg = df_results.groupby('섹터')['수익률(%)'].mean().sort_values(ascending=False).reset_index()
                    # 0% 기준으로 색상 나누기 위해 '구분' 추가
                    sector_avg['구분'] = sector_avg['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
                    fig_sector = px.bar(
                        sector_avg, 
                        x='수익률(%)', 
                        y='섹터', 
                        orientation='h', 
                        color='구분',
                        color_discrete_map={'상승': '#ef5350', '하락': '#0d6efd'}
                    )
                    st.plotly_chart(fig_sector, use_container_width=True)
                else:
                    st.subheader(f"📈 {target_sector} 내 수익률 순위")
                    # 개별 종목 순위에서도 상위 10개 중 하락이 있을 수 있으니 색상 구분
                    top_10['구분'] = top_10['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
                    fig_rank = px.bar(
                        top_10, 
                        x='수익률(%)', 
                        y='종목명', 
                        orientation='h', 
                        color='구분',
                        color_discrete_map={'상승': '#ef5350', '하락': '#0d6efd'}
                    )
                    st.plotly_chart(fig_rank, use_container_width=True)
            
            # --- 결과 표시: 전체 원본 데이터 ---
            with st.expander("📄 전체 분석 데이터 상세보기"):
                df_results['상세페이지'] = df_results['티커'].apply(lambda x: f"https://finance.yahoo.com/quote/{x}")
                st.dataframe(
                    df_results.sort_values(by='수익률(%)', ascending=False), 
                    use_container_width=True,
                    column_config={
                        "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                        "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
                    }
                )
        else:
            st.error("❌ 분석 결과가 없습니다. 기간 내 데이터가 있는지, 또는 선택한 섹터에 종목이 포함되어 있는지 다시 한번 확인해 주세요.")

else:
    # 버튼을 누르기 전 초기 안내 화면
    st.info("💡 왼쪽 사이드바에서 원하는 분석 조건을 설정한 후 **'수익률 분석 시작'** 버튼을 클릭해 주세요.")
    
    # 현재 상태 요약 정보 (메트릭 카드)
    col1, col2, col3 = st.columns(3)
    col1.metric("총 분석 대상", f"{len(df_info)}개 종목")
    # 파일 수정 시간을 이용해 마지막 업데이트 일시 표시
    last_upd = datetime.fromtimestamp(os.path.getmtime(CSV_FILE)).strftime('%Y-%m-%d') if os.path.exists(CSV_FILE) else "없음"
    col2.metric("종목 리스트 업데이트", last_upd)
    col3.metric("데이터 출처", "Yahoo Finance (via FDR)")

st.divider()
# 하단 저작권 표시
st.caption("© 2026 S&P 500 Analyzer Web PRO | Global Stock Analysis Tool Powered by Antigravity")
