import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import os
import time
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from drive_memo_handler import DriveMemoHandler, show_memo_ui

# ============================================================
# 프로그램 명칭 : S&P 500 수익률 분석기 PRO
# 주요 기능     : S&P 500 종목들의 기간별 수익률을 분석하고 시각화합니다.
# 작성자        : Antigravity AI
# ============================================================



# --- 1. 페이지 설정 (브라우저 탭에 표시될 정보) ---
st.set_page_config(
    page_title="S&P 500 수익률 분석기 PRO",
    page_icon="💲",
    layout="wide"
)

# --- 바로가기 네비게이션 ---
st.markdown(
    "🔗 **바로가기:** "
    "[📈 주식 데이터 조회기](https://phythonstock-t6smhrjdovzwmwtr8hi6h7.streamlit.app/) · "
    "[� 주식 데이터 일괄 조회기](https://phythonstock-t8qh6heqss8nwnjwycjrcb.streamlit.app/) · "
    "[� KOSPI 200 분석기](https://phythonstock-if4pq46alnrqsyjwnej26f.streamlit.app) · "
    "**💲 S&P500 분석기**"
)

# --- 2. 디자인 꾸미기 (CSS) ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 상수 정의 및 환경 설정 ---
CSV_FILE = 'sp500_tickers_detailed.csv'
DATA_DIR = 'data/sp500'
GOOGLE_DRIVE_FOLDER_ID = '13STM_0_Gn4FfMUR_6tjjvIA8VyUTwtbH'
MEMO_FOLDER_ID = '1nv9imwPebStoOVJFWM5U6HIvAkib5xRY'  # 메모 데이터 저장소

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 4. 구글 드라이브 서비스 설정 (DriveMemoHandler 활용) ---
data_handler = DriveMemoHandler(GOOGLE_DRIVE_FOLDER_ID, cache_dir=DATA_DIR)


def download_file_from_drive(file_name, use_cache=True):
    """데이터 핸들러를 사용하여 파일을 다운로드합니다."""
    return data_handler.download_file(file_name, use_cache=use_cache)


def upload_raw_file_to_drive(file_name, content_buffer, mime_type="text/csv"):
    """데이터 핸들러를 사용하여 업로드합니다."""
    return data_handler.upload_file(file_name, content_buffer, mime_type=mime_type)


def upload_file_to_drive(file_name, df):
    """DataFrame을 CSV로 변환하여 구글 드라이브와 로컬 캐시에 업로드/저장합니다."""
    local_path = os.path.join(DATA_DIR, file_name)
    df.to_csv(local_path)

    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=True)
    csv_buffer.seek(0)
    upload_raw_file_to_drive(file_name, csv_buffer, "text/csv")


# --- 5. 데이터 로딩 함수 ---
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


df_info = load_info_data()


# --- 6. 주요 로직 함수들 ---

def _update_single_stock(ticker, name, today_str, idx, total_items):
    """
    개별 종목의 데이터를 업데이트하는 내부 함수 (병렬 처리용).
    결과: (ticker, success: bool, message: str)
    """
    file_name = f"{ticker}.csv"
    need_download = False
    start_date_download = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    end_date_download = today_str
    existing_df = None

    # 구글 드라이브/로컬 캐시에서 파일 확인
    file_buffer = download_file_from_drive(file_name)
    if file_buffer:
        try:
            existing_df = pd.read_csv(file_buffer, index_col=0, parse_dates=True)
            if not existing_df.empty:
                last_date = existing_df.index[-1]
                # 마지막 데이터 날짜가 오늘 이전이면 업데이트 필요
                if last_date.date() < datetime.now().date():
                    start_date_download = last_date.strftime("%Y-%m-%d")
                    need_download = True
                # 오늘 데이터가 있으면 업데이트 불필요
            else:
                need_download = True
        except Exception as e:
            logger.warning(f"{ticker} 캐시 파일 파싱 오류: {e}")
            need_download = True
    else:
        need_download = True

    if not need_download:
        return (ticker, True, "최신 상태")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            new_df = fdr.DataReader(ticker, start_date_download, end_date_download)

            if not new_df.empty:
                if existing_df is not None and not existing_df.empty:
                    combined_df = pd.concat([existing_df, new_df])
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                    upload_file_to_drive(file_name, combined_df)
                else:
                    upload_file_to_drive(file_name, new_df)

            return (ticker, True, "업데이트 완료")

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                time.sleep(wait_time)
            else:
                logger.warning(f"{name}({ticker}) 최종 다운로드 실패: {e}")
                return (ticker, False, f"실패: {e}")

    return (ticker, False, "알 수 없는 오류")


def run_update_data(df_info):
    """
    각 종목의 과거 가격 데이터를 최신으로 업데이트합니다.
    병렬 처리 + ETA 표시 적용.
    """
    status_text = st.empty()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sync_info_file = "sp500_last_sync_info.json"

    # --- 슈퍼 패스트 체크 (2시간 간격) ---
    status_text.info("🚀 동기화 상태 확인 중 (슈퍼 패스트)...")
    sync_info_buffer = download_file_from_drive(sync_info_file)
    if sync_info_buffer:
        try:
            sync_info = json.loads(sync_info_buffer.getvalue().decode('utf-8'))
            last_sync_str = sync_info.get("last_sync_time")
            if last_sync_str:
                last_sync_time = datetime.fromisoformat(last_sync_str)
                if datetime.now() - last_sync_time < timedelta(hours=2):
                    status_text.success(f"✨ 이미 최근에 업데이트되었습니다! (마지막: {last_sync_time.strftime('%H:%M')})")
                    time.sleep(2)
                    status_text.empty()
                    return
        except Exception as e:
            logger.warning(f"동기화 정보 확인 중 오류: {e}")

    progress_bar = st.progress(0)
    total_items = len(df_info)
    start_time = time.time()
    completed = 0
    failed_list = []

    # 병렬 처리로 데이터 업데이트 (max_workers=8, Yahoo Finance API 제한 고려)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for idx, row in df_info.iterrows():
            ticker, name = row['Ticker'], row['Company']
            if pd.isna(ticker):
                completed += 1
                continue
            future = executor.submit(_update_single_stock, ticker, name, today_str, idx, total_items)
            futures[future] = (ticker, name)

        for future in concurrent.futures.as_completed(futures):
            completed += 1
            ticker, name = futures[future]
            result_ticker, success, message = future.result()

            if not success:
                failed_list.append(f"{name}({ticker})")

            # ETA 계산
            elapsed = time.time() - start_time
            if completed > 0:
                eta_seconds = int((elapsed / completed) * (total_items - completed))
                eta_str = f"(남은 시간: 약 {eta_seconds // 60}분 {eta_seconds % 60}초)" if eta_seconds > 60 else f"(남은 시간: 약 {eta_seconds}초)"
            else:
                eta_str = ""

            status_text.text(f"📥 업데이트 중: {completed}/{total_items} {eta_str}")
            progress_bar.progress(completed / total_items)

    # --- 동기화 결과 기록 ---
    new_sync_info = {"last_sync_time": datetime.now().isoformat()}
    sync_info_json = json.dumps(new_sync_info)
    sync_buffer = io.BytesIO(sync_info_json.encode('utf-8'))
    upload_raw_file_to_drive(sync_info_file, sync_buffer, "application/json")

    end_time = time.time()
    duration = int(end_time - start_time)

    if failed_list:
        status_text.warning(f"⚠️ 업데이트 완료 ({duration}초). 실패 종목 {len(failed_list)}개: {', '.join(failed_list[:5])}{'...' if len(failed_list) > 5 else ''}")
    else:
        status_text.success(f"✅ 모든 데이터가 최신 상태로 업데이트되었습니다! (소요 시간: {duration}초)")

    time.sleep(3)
    status_text.empty()
    progress_bar.empty()


def calculate_returns(df_info_hash, mode, period_days, start_date, end_date, target_sector):
    """
    모든 종목의 수익률을 계산합니다 (병렬 처리 적용).
    df_info_hash는 캐시 키용 해시값이며, 실제 데이터는 전역 df_info를 사용합니다.
    """
    global df_info

    # 분석 기간 설정
    if mode == "최근 일수 기준":
        calc_start_date = pd.Timestamp(datetime.now() - timedelta(days=period_days))
        calc_end_date = pd.Timestamp(datetime.now())
    else:
        calc_start_date = pd.Timestamp(start_date)
        calc_end_date = pd.Timestamp(end_date)

    filtered_info = df_info.copy()
    if target_sector != "전체 섹터":
        filtered_info = df_info[df_info['Sector'] == target_sector]

    def process_stock(row):
        ticker, name, sector = row['Ticker'], row['Company'], row.get('Sector', 'Unknown')
        file_name = f"{ticker}.csv"

        file_buffer = download_file_from_drive(file_name, use_cache=True)
        if not file_buffer:
            return None

        try:
            df = pd.read_csv(file_buffer, index_col=0, parse_dates=True)
            df_filtered = df[(df.index >= calc_start_date) & (df.index <= calc_end_date)]

            if len(df_filtered) >= 2:
                start_price = df_filtered.iloc[0]['Close']
                end_price = df_filtered.iloc[-1]['Close']
                if start_price > 0:
                    return {
                        '티커': ticker, '종목명': name, '섹터': sector,
                        '시작일가': round(start_price, 2), '종료일가': round(end_price, 2),
                        '수익률(%)': round(((end_price - start_price) / start_price) * 100, 2)
                    }
        except Exception as e:
            logger.warning(f"{ticker} 수익률 계산 오류: {e}")
            return None
        return None

    results = []
    # 병렬 처리 (max_workers=15로 제한)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_stock, row): row for _, row in filtered_info.iterrows()}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    return pd.DataFrame(results)


# --- 7. 공통 UI 렌더링 함수 ---

def render_ranking_table(df_ranked, title, icon, label_prefix, is_sp500=True):
    """TOP 10 / BOTTOM 10 테이블을 렌더링하는 공통 함수."""
    st.subheader(title)

    if df_ranked.empty:
        st.warning("표시할 데이터가 없습니다.")
        return

    highlight = df_ranked.iloc[0]
    st.metric(
        label=f"{icon} {label_prefix}: {highlight['종목명']} ({highlight['티커']})",
        value=f"{highlight['수익률(%)']}%",
        delta=f"${round(highlight['종료일가'] - highlight['시작일가'], 2)}"
    )

    display_df = df_ranked.copy()
    display_df['상세페이지'] = display_df['티커'].apply(
        lambda x: f"https://finance.yahoo.com/quote/{x}"
    )

    st.dataframe(
        display_df[['상세페이지', '티커', '종목명', '섹터', '시작일가', '종료일가', '수익률(%)']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
            "시작일가": st.column_config.NumberColumn(format="$%.2f"),
            "종료일가": st.column_config.NumberColumn(format="$%.2f"),
            "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
        }
    )


def render_charts(df_results, top_10, target_sector):
    """수익률 분포 및 섹터별 차트를 렌더링하는 공통 함수."""
    st.divider()
    col_chart1, col_chart2 = st.columns(2)

    # 상승/하락 구분 컬럼 추가 (한 번만)
    df_results['구분'] = df_results['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
    color_map = {'상승': '#ef5350', '하락': '#0d6efd'}

    with col_chart1:
        st.subheader("📊 수익률 분포 현황")
        fig_dist = px.histogram(
            df_results,
            x="수익률(%)",
            nbins=40,
            color='구분',
            color_discrete_map=color_map,
            barmode='overlay'
        )
        fig_dist.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="0%")
        st.plotly_chart(fig_dist, use_container_width=True)

    with col_chart2:
        if target_sector == "전체 섹터":
            st.subheader("🏢 섹터별 평균 수익률")
            sector_avg = df_results.groupby('섹터')['수익률(%)'].mean().sort_values(ascending=False).reset_index()
            sector_avg['구분'] = sector_avg['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
            fig_sector = px.bar(
                sector_avg,
                x='수익률(%)',
                y='섹터',
                orientation='h',
                color='구분',
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_sector, use_container_width=True)
        else:
            st.subheader(f"📈 {target_sector} 내 수익률 순위")
            display_top = top_10.copy()
            display_top['구분'] = display_top['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
            fig_rank = px.bar(
                display_top,
                x='수익률(%)',
                y='종목명',
                orientation='h',
                color='구분',
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_rank, use_container_width=True)


# --- 8. 사이드바 (사용자 입력 설정) ---
with st.sidebar:
    st.title("⚙️ 분석 설정")

    if df_info is None:
        st.error(f"❌ '{CSV_FILE}' 파일이 없습니다.")
        st.stop()

    # 데이터 업데이트 버튼
    if st.button("🔄 데이터 최신화 (Yahoo Finance)"):
        run_update_data(df_info)

    st.divider()

    # 1) 분석 기간 선택 방식
    analysis_mode = st.radio("분석 모드", ["최근 일수 기준", "직접 날짜 지정"])

    if analysis_mode == "최근 일수 기준":
        period_days = st.select_slider(
            "분석 기간 (일)",
            options=[1, 7, 30, 90, 180, 365, 730],
            value=30
        )
        start_date, end_date = None, None
    else:
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

# --- 9. 메인 화면 ---
st.title("🇺🇸 S&P 500 수익률 분석기 PRO")
st.markdown("전 세계 자본의 중심, S&P 500 기업들의 수익률을 한눈에 분석하세요.")

# 메모 기능 (kospi와 동일)
show_memo_ui(MEMO_FOLDER_ID, default_file="dashboard_memo.txt")

# 분석 버튼 클릭 시 → 결과를 session_state에 저장
if analyze_btn:
    with st.spinner("데이터를 열심히 분석 중입니다... 잠시만 기다려 주세요!"):
        # 캐시 키용 해시값 생성 (DataFrame 대신 해시 가능한 값 사용)
        info_hash = hash(tuple(df_info['Ticker'].tolist()))
        df_results = calculate_returns(info_hash, analysis_mode, period_days, start_date, end_date, target_sector)
        # session_state에 저장하여 결과 유지
        st.session_state['sp500_results'] = df_results
        st.session_state['sp500_sector'] = target_sector

# 결과 표시 (session_state에서 불러오기)
if 'sp500_results' in st.session_state:
    df_results = st.session_state['sp500_results']
    target_sector_display = st.session_state.get('sp500_sector', target_sector)

    if not df_results.empty:
        # --- TOP 10 ---
        top_10 = df_results.sort_values(by='수익률(%)', ascending=False).head(10).copy()
        render_ranking_table(
            top_10,
            f"🏆 수익률 상위 TOP 10 종목 ({target_sector_display})",
            "🥇", "오늘의 수익률 1위"
        )

        # --- BOTTOM 10 ---
        st.divider()
        bottom_10 = df_results.sort_values(by='수익률(%)', ascending=True).head(10).copy()
        render_ranking_table(
            bottom_10,
            f"📉 수익률 하위 BOTTOM 10 종목 ({target_sector_display})",
            "⚠️", "오늘의 하락 1위"
        )

        # --- 그래프 ---
        render_charts(df_results, top_10, target_sector_display)

        # --- 전체 데이터 ---
        with st.expander("📄 전체 분석 데이터 상세보기"):
            display_all = df_results.copy()
            display_all['상세페이지'] = display_all['티커'].apply(
                lambda x: f"https://finance.yahoo.com/quote/{x}"
            )
            st.dataframe(
                display_all.sort_values(by='수익률(%)', ascending=False),
                use_container_width=True,
                column_config={
                    "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                    "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
                }
            )
    else:
        st.error("❌ 분석 결과가 없습니다. 기간 내 데이터가 있는지, 또는 선택한 섹터에 종목이 포함되어 있는지 다시 한번 확인해 주세요.")

else:
    # 초기 안내 화면
    st.info("💡 왼쪽 사이드바에서 원하는 분석 조건을 설정한 후 **'수익률 분석 시작'** 버튼을 클릭해 주세요.")

    # 현재 상태 요약 정보 (메트릭 카드)
    col1, col2, col3 = st.columns(3)
    col1.metric("총 분석 대상", f"{len(df_info)}개 종목")
    last_upd = datetime.fromtimestamp(os.path.getmtime(CSV_FILE)).strftime('%Y-%m-%d') if os.path.exists(CSV_FILE) else "없음"
    col2.metric("종목 리스트 업데이트", last_upd)
    col3.metric("데이터 출처", "Yahoo Finance (via FDR)")

    # 데이터 상태 요약
    col4, col5, col6 = st.columns(3)
    # 로컬 캐시 파일 수
    cached_files = len([f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]) if os.path.exists(DATA_DIR) else 0
    col4.metric("📁 로컬 캐시 파일", f"{cached_files}개")

    # 마지막 동기화 시간 확인
    sync_file_path = os.path.join(DATA_DIR, "sp500_last_sync_info.json")
    if os.path.exists(sync_file_path):
        try:
            with open(sync_file_path, 'r') as f:
                sync_data = json.load(f)
                last_sync = datetime.fromisoformat(sync_data.get("last_sync_time", ""))
                col5.metric("⏰ 마지막 동기화", last_sync.strftime('%m/%d %H:%M'))
        except Exception:
            col5.metric("⏰ 마지막 동기화", "정보 없음")
    else:
        col5.metric("⏰ 마지막 동기화", "미실행")

    col6.metric("🔄 업데이트 주기", "2시간 간격")

st.divider()
st.caption("© 2026 S&P 500 Analyzer Web PRO | Global Stock Analysis Tool Powered by Antigravity")
