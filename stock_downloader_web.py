import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import os
import time
import zipfile
import io
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# Program Name : stock_downloader_web.py
# Description  : Professional & Interactive Stock Downloader (Web Version)
# ============================================================

# --- Page Configuration ---
st.set_page_config(
    page_title="주식 데이터 다운로더 PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Premium Look ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #1976D2;
        color: white;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #1565C0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .download-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 2rem;
    }
    .status-success {
        color: #2E7D32;
        font-weight: bold;
    }
    .status-fail {
        color: #D32F2F;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Global Configuration ---
# 주요 지수 맵핑 테이블 (사용자가 '코스피'라고 입력해도 '^KS11'로 변환)
INDEX_MAP = {
    "코스피": "^KS11",
    "KOSPI": "^KS11",
    "코스닥": "^KQ11",
    "KOSDAQ": "^KQ11",
    "코스피200": "^KS200",
    "KOSPI200": "^KS200",
    "나스닥": "IXIC",
    "NASDAQ": "IXIC",
    "S&P500": "US500",
    "다우존스": "DJI",
    "다우": "DJI",
    "달러/원": "USD/KRW",
    "환율": "USD/KRW",
    "비트코인": "BTC/KRW",
}

# --- Data Caching ---
@st.cache_data(ttl=3600)
def get_stock_listing():
    """상장 종목 리스트를 가져와서 캐싱합니다."""
    try:
        df_krx = fdr.StockListing('KRX')
        # 종목명 -> 티커 맵핑 생성
        name_to_ticker = dict(zip(df_krx['Name'], df_krx['Code']))
        return name_to_ticker
    except:
        return {}

# --- Logic Functions ---

def download_stock_data(ticker, ticker_name, start_date, end_date):
    """Downloads stock data and returns a tuple (status, message, dataframe)"""
    ticker = str(ticker).strip()
    ticker_name = str(ticker_name).strip()
    
    # 지수 맵핑 처리
    if ticker in INDEX_MAP:
        ticker = INDEX_MAP[ticker]
    elif ticker_name in INDEX_MAP:
        ticker = INDEX_MAP[ticker_name]
    
    # 종목명으로 입력했을 경우 티커로 변환 시도 (숫자가 아닌 경우)
    if not ticker.isdigit() and len(ticker) > 0 and ticker not in INDEX_MAP.values():
        name_map = get_stock_listing()
        if ticker in name_map:
            ticker = name_map[ticker]
        elif ticker_name in name_map:
            ticker = name_map[ticker_name]

    try:
        # 데이터 시도
        df = fdr.DataReader(ticker, start=start_date, end=end_date)
        if df.empty:
            return "Failed", f"'{ticker}' 데이터를 찾을 수 없습니다 (No Data)", None
        
        return "Success", f"{len(df)}건 완료", df
    except Exception as e:
        error_msg = str(e)
        if "Expecting value" in error_msg:
            error_msg = "서버 응답 오류 (데이터 공급처 세션 만료 혹은 일시적 오류). 1~2분 후 다시 시도해 주세요."
        return "Failed", error_msg, None

def create_zip_and_summary(results_list):
    """Creates a ZIP file and a summary Excel file from the results"""
    zip_buffer = io.BytesIO()
    summary_data = []
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for res in results_list:
            ticker, name, status, msg, df = res
            summary_data.append({
                "티커": ticker,
                "종목명": name,
                "상태": status,
                "메시지": msg
            })
            
            if status == "Success" and df is not None:
                # Save individual excel to buffer then to zip
                excel_buffer = io.BytesIO()
                clean_sheet = f"{name}_{ticker}"[:31]
                df.to_excel(excel_buffer, sheet_name=clean_sheet)
                filename = f"{name}_{ticker}.xlsx"
                zip_file.writestr(filename, excel_buffer.getvalue())
        
        # Add summary file to ZIP
        summary_df = pd.DataFrame(summary_data)
        summary_buffer = io.BytesIO()
        summary_df.to_excel(summary_buffer, index=False)
        zip_file.writestr("download_summary.xlsx", summary_buffer.getvalue())
        
    return zip_buffer.getvalue(), summary_buffer.getvalue()

# --- Application Layout ---

st.title("🚀 Professional Stock Data Downloader")
st.markdown("전 세계 주식 데이터를 손쉽게 조회하고 엑셀 파일로 다운로드하세요.")

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ 기간 설정")
    
    period_option = st.selectbox(
        "조회 기간",
        ["1년", "3년", "5년", "10년", "직접 입력"],
        index=0
    )
    
    today = datetime.today()
    if period_option == "1년":
        default_start = today - timedelta(days=365)
    elif period_option == "3년":
        default_start = today - timedelta(days=365*3)
    elif period_option == "5년":
        default_start = today - timedelta(days=365*5)
    elif period_option == "10년":
        default_start = today - timedelta(days=365*10)
    else:
        default_start = today - timedelta(days=365)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", default_start)
    with col2:
        end_date = st.date_input("종료일", today)

    st.divider()
    st.info("💡 **Tip**: 엑셀 파일 업로드 시 '티커'와 '종목명' 컬럼이 포함되어야 합니다.")
    
    with st.expander("📈 주요 지수 심볼 안내"):
        st.markdown("""
        **한국 지수**
        - 코스피: `^KS11`
        - 코스닥: `^KQ11`
        - 코스피200: `^KS200`
        
        **글로벌 지수**
        - 나스닥: `IXIC`
        - S&P500: `US500`
        - 다우존스: `DJI`
        
        **기타**
        - 환율(USD/KRW): `USD/KRW`
        - 비트코인: `BTC/KRW`
        
        *한글로 '코스피'라고 입력해도 자동으로 변환됩니다!*
        """)

# --- Main Area: Input ---
input_mode = st.radio("📥 입력 방식 선택", ["엑셀/CSV 파일 업로드", "직접 입력"], horizontal=True)

download_list = []

if input_mode == "엑셀/CSV 파일 업로드":
    uploaded_file = st.file_uploader("파일을 선택하세요", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                ticker_df = pd.read_csv(uploaded_file)
            else:
                ticker_df = pd.read_excel(uploaded_file)
            
            t_col = next((c for c in ticker_df.columns if any(x in c.lower() for x in ['티커', 'ticker', 'symbol'])), None)
            n_col = next((c for c in ticker_df.columns if any(x in c.lower() for x in ['명', 'name'])), None)
            
            if t_col and n_col:
                for _, row in ticker_df.iterrows():
                    download_list.append((str(row[t_col]), str(row[n_col])))
                st.success(f"✅ {len(download_list)}개의 종목을 불러왔습니다.")
            else:
                st.error("❌ 파일에서 '티커'와 '종목명' 컬럼을 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")

else:
    direct_input = st.text_area(
        "종목 정보 입력",
        placeholder="005930,삼성전자; NVDA,엔비디아",
        help="티커와 이름을 쉼표(,)로 구분하고, 종목 간은 세미콜론(;)으로 구분하세요."
    )
    if direct_input:
        items = direct_input.split(';')
        for item in items:
            if ',' in item:
                t, n = item.split(',')
                download_list.append((t.strip(), n.strip()))
            elif item.strip():
                t = item.strip()
                download_list.append((t, t))
        if download_list:
            st.success(f"✅ {len(download_list)}개의 종목이 입력되었습니다.")

# --- Download Execution ---
if st.button("🚀 데이터 다운로드 시작") and download_list:
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    all_results = []
    success_count = 0
    fail_count = 0
    
    start_time_exec = time.time()
    
    # Progress UI setup
    results_display = []
    
    # Multithreading for download
    max_workers = min(10, os.cpu_count() or 1 * 2)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {
            executor.submit(download_stock_data, t, n, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")): (t, n) 
            for t, n in download_list
        }
        
        for i, future in enumerate(as_completed(future_to_stock)):
            t, n = future_to_stock[future]
            status, msg, df = future.result()
            
            all_results.append((t, n, status, msg, df))
            
            if status == "Success":
                success_count += 1
            else:
                fail_count += 1
            
            # Update Progress
            prog = (i + 1) / len(download_list)
            progress_bar.progress(prog)
            status_text.text(f"진행 중... ({i+1}/{len(download_list)}) - {n}")
            
            results_display.append({
                "티커": t,
                "종목명": n,
                "상태": "✅ 성공" if status == "Success" else "❌ 실패",
                "메시지": msg
            })

    elapsed_time = time.time() - start_time_exec
    
    # Final Summary
    st.divider()
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("총 종목", len(download_list))
    col_stat2.metric("성공", success_count)
    col_stat3.metric("실패", fail_count)
    
    st.info(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
    
    # Display results table
    st.subheader("📊 상세 결과")
    st.table(pd.DataFrame(results_display))
    
    # Prepare ZIP download
    with st.spinner("파일 압축 중..."):
        zip_data, summary_data = create_zip_and_summary(all_results)
        
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📁 전체 결과 압축파일(ZIP) 다운로드",
            data=zip_data,
            file_name=f"stock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
    with col_dl2:
        st.download_button(
            label="📊 다운로드 결과 요약(Excel) 다운로드",
            data=summary_data,
            file_name=f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.balloons()
elif not download_list and "button" in st.session_state:
    st.warning("⚠️ 다운로드할 종목 정보를 입력하거나 파일을 업로드해 주세요.")

# --- Footer ---
st.divider()
st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        © 2026 주식 데이터 다운로더 PRO Web v1.0 | Powered by FinanceDataReader & Streamlit
    </div>
    """, unsafe_allow_html=True)
