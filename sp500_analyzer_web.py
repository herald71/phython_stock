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
import concurrent.futures
import threading
import toml
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

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

# 구글 드라이브 관련 설정
GOOGLE_DRIVE_FOLDER_ID = '13STM_0_Gn4FfMUR_6tjjvIA8VyUTwtbH'
CACHE_DIR = DATA_DIR  # 기존 데이터 디렉토리를 캐시로 사용

# --- 4. 구글 드라이브 서비스 생성 (쓰레드 세이프) ---
thread_local = threading.local()

@st.cache_resource
def get_google_creds():
    """구글 인증 정보를 한 번만 생성하여 캐싱합니다."""
    try:
        # 1. st.secrets 확인
        google_secrets = None
        if "google_drive" in st.secrets:
            google_secrets = st.secrets["google_drive"]
        else:
            # 2. st.secrets에 없을 경우 직접 toml 파일 로드 시도 (경로 문제 대비)
            possible_paths = [
                ".streamlit/secrets.toml",
                os.path.join(os.getcwd(), ".streamlit/secrets.toml")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        all_secrets = toml.load(path)
                        google_secrets = all_secrets.get("google_drive")
                        if google_secrets:
                            break
                    except:
                        continue
        
        if not google_secrets:
            st.error("❌ 설정에서 'google_drive' 섹션을 찾을 수 없습니다. (.streamlit/secrets.toml 확인 필요)")
            return None
        
        # 필수 필드 추출 (안전하게)
        creds_dict = {
            "client_id": google_secrets.get("client_id"),
            "client_secret": google_secrets.get("client_secret"),
            "refresh_token": google_secrets.get("refresh_token"),
            "token_uri": google_secrets.get("token_uri", "https://oauth2.googleapis.com/token")
        }

        # 필수 필드 누락 여부 확인
        missing_fields = [k for k, v in creds_dict.items() if not v]
        if missing_fields:
            st.error(f"❌ 구글 드라이브 인증 정보 중 다음 필드가 누락되었습니다: {', '.join(missing_fields)}")
            st.info("💡 .streamlit/secrets.toml 파일의 필드명(client_id, client_secret, refresh_token)을 확인해 주세요.")
            return None

        from google.oauth2.credentials import Credentials
        return Credentials.from_authorized_user_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive.file'])
    except Exception as e:
        st.error(f"❌ 구글 인증 생성 중 예외 발생: {e}")
        return None

def get_drive_service():
    """각 쓰레드별로 별도의 드라이브 서비스 객체를 생성하여 SSL 오류를 방지합니다."""
    if not hasattr(thread_local, "service"):
        creds = get_google_creds()
        if creds:
            thread_local.service = build('drive', 'v3', credentials=creds)
        else:
            thread_local.service = None
    return thread_local.service

def download_file_from_drive(file_name, use_cache=True):
    """구글 드라이브에서 파일을 다운로드합니다."""
    local_path = os.path.join(CACHE_DIR, file_name)
    
    if use_cache and os.path.exists(local_path):
        with open(local_path, 'rb') as f:
            return io.BytesIO(f.read())

    service = get_drive_service()
    if not service: return None

    try:
        query = f"name = '{file_name}' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if not files: return None
            
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        with open(local_path, 'wb') as f:
            f.write(fh.read())
            
        fh.seek(0)
        return fh
    except: return None

def upload_file_to_drive(file_name, df):
    """DataFrame을 CSV로 변환하여 구글 드라이브와 로컬 캐시에 업로드/저장합니다."""
    local_path = os.path.join(CACHE_DIR, file_name)
    df.to_csv(local_path)
    
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=True)
    csv_buffer.seek(0)
    upload_raw_file_to_drive(file_name, csv_buffer, "text/csv")

def upload_raw_file_to_drive(file_name, content_buffer, mime_type="text/csv"):
    """일반 바이너리 데이터를 구글 드라이브에 업로드합니다."""
    service = get_drive_service()
    if not service: return

    try:
        query = f"name = '{file_name}' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        media = MediaIoBaseUpload(content_buffer, mimetype=mime_type, resumable=True)
        
        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {'name': file_name, 'parents': [GOOGLE_DRIVE_FOLDER_ID]}
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    except Exception as e:
        st.error(f"구글 드라이브 파일 업로드 오류 ({file_name}): {e}")

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
    구글 드라이브 동기화 및 슈퍼 패스트 체크가 적용되었습니다.
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
                # 마지막 업데이트로부터 2시간이 지나지 않았으면 건너뜀
                if datetime.now() - last_sync_time < timedelta(hours=2):
                    status_text.success(f"✨ 이미 최근에 업데이트되었습니다! (마지막: {last_sync_time.strftime('%H:%M')})")
                    time.sleep(2)
                    status_text.empty()
                    return
        except:
            pass

    progress_bar = st.progress(0)
    total_items = len(df_info)
    
    # 작업 시작 시간
    start_time = time.time()
    
    for idx, row in df_info.iterrows():
        ticker, name = row['Ticker'], row['Company']
        if pd.isna(ticker):
            continue
            
        file_name = f"{ticker}.csv"
        need_download = False
        start_date_download = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")
        end_date_download = today_str
        existing_df = None

        # 구글 드라이브에서 파일 확인 및 다운로드
        file_buffer = download_file_from_drive(file_name)
        if file_buffer:
            try:
                existing_df = pd.read_csv(file_buffer, index_col=0, parse_dates=True)
                if not existing_df.empty:
                    last_date = existing_df.index[-1]
                    # 마지막 데이터 날짜가 오늘이거나 그 이전이면 업데이트 시도 (어제 종가 반영 등)
                    if last_date.date() <= datetime.now().date():
                        # 마지막 날짜부터 다시 받아와서 중복 제거(keep='last') 로직으로 최신 종가 갱신
                        start_date_download = last_date.strftime("%Y-%m-%d")
                        need_download = True
            except:
                need_download = True
        else:
            need_download = True

        if need_download:
            status_text.text(f"📥 데이터를 가져오는 중: {name} ({ticker}) [{idx+1}/{total_items}]")
            
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    # 데이터 다운로드 시도
                    new_df = fdr.DataReader(ticker, start_date_download, end_date_download)
                    
                    if not new_df.empty:
                        if existing_df is not None and not existing_df.empty:
                            combined_df = pd.concat([existing_df, new_df])
                            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                            upload_file_to_drive(file_name, combined_df)
                        else:
                            upload_file_to_drive(file_name, new_df)
                        
                        success = True
                        break # 성공시 루프 탈출
                    else:
                        # 데이터가 비어있는 경우 (장 마감 직후 등)
                        success = True
                        break
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        # 에러 발생 시 잠시 대기 후 재시도
                        wait_time = (attempt + 1) * 2
                        status_text.text(f"⚠️ {ticker} 재시도 중... ({attempt + 1}/{max_retries}) - {wait_time}초 대기")
                        time.sleep(wait_time)
                    else:
                        st.warning(f"⚠️ {name}({ticker}) 최종 다운로드 실패: {e}")
            
            # 다음 요청을 위해 아주 짧게 대기
            if success:
                time.sleep(0.05)
        
        progress_bar.progress((idx + 1) / total_items)
        
    # --- 동기화 결과 기록 (슈퍼 패스트용 - 2시간 주기) ---
    new_sync_info = {"last_sync_time": datetime.now().isoformat()}
    sync_info_json = json.dumps(new_sync_info)
    sync_buffer = io.BytesIO(sync_info_json.encode('utf-8'))
    upload_raw_file_to_drive(sync_info_file, sync_buffer, "application/json")

    end_time = time.time()
    status_text.success(f"✅ 모든 데이터가 최신 상태로 업데이트되었습니다! (소요 시간: {int(end_time - start_time)}초)")
    time.sleep(3)
    status_text.empty()
    progress_bar.empty()

@st.cache_data(show_spinner=False)
def calculate_returns(df_info, mode, period_days, start_date, end_date, target_sector):
    """
    모든 종목의 수익률을 계산합니다 (병렬 처리 + 결과 캐싱 적용).
    """
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
        
        # 캐시 활용 (로컬에 있으면 로드, 없으면 드라이브에서 시도)
        file_buffer = download_file_from_drive(file_name, use_cache=True)
        if not file_buffer: return None
        
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
        except: return None
        return None

    results = []
    # S&P 500은 종목이 많으므로 병렬 처리로 속도 개선
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(process_stock, row): row for _, row in filtered_info.iterrows()}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
                    
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
