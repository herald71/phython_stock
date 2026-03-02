import streamlit as st
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import os
import time
import plotly.express as px
import plotly.graph_objects as go
import io
import json
import concurrent.futures
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# ============================================================
# 프로그램 명칭 : 코스피 200 수익률 분석기 (웹 버전)
# 주요 기능     : KOSPI 200 종목들의 기간별 수익률을 분석하고 시각화합니다.
# 작성자        : Antigravity AI
# ============================================================

# --- 1. 페이지 설정 (브라우저 탭에 표시될 정보) ---
st.set_page_config(
    page_title="코스피 200 수익률 분석기 PRO",
    page_icon="📊",
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
CSV_FILE = 'KOSPI200_with_KSIC_2026.csv'
GOOGLE_DRIVE_FOLDER_ID = '1Bkzmh-jlcOnmgOzS3I8fJyHmwsta_oAG'
CACHE_DIR = 'cache_data'

# 로컬 캐시 폴더 생성
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# OAuth2 인증 정보 (보안을 위해 .streamlit/secrets.toml 사용)
# 로컬 테스트 시에는 .streamlit/secrets.toml 파일에 정보를 넣으세요.
try:
    CLIENT_ID = st.secrets["google_drive"]["client_id"]
    CLIENT_SECRET = st.secrets["google_drive"]["client_secret"]
    REFRESH_TOKEN = st.secrets["google_drive"]["refresh_token"]
except:
    # Secrets가 설정되지 않은 경우 초기값 (사용자 안내용)
    CLIENT_ID = None
    CLIENT_SECRET = None
    REFRESH_TOKEN = None

# --- 4. 구글 드라이브 서비스 생성 (싱글톤 패턴) ---
@st.cache_resource
def get_drive_service_singleton():
    """구글 드라이브 서비스 객체를 한 번만 생성하여 재사용합니다."""
    creds_data = None
    
    # 1. Streamlit Secrets 확인
    try:
        if "google_drive" in st.secrets:
            creds_data = st.secrets["google_drive"]
    except:
        pass

    # 2. 로컬 변수 사용
    if creds_data is None:
        creds_data = {
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN, "token_uri": "https://oauth2.googleapis.com/token"
        }

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(creds_data, scopes=['https://www.googleapis.com/auth/drive.file'])
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"구글 서비스 생성 실패: {e}")
        return None

# 전역 서비스 객체 (최초 1회 생성)
drive_service = get_drive_service_singleton()

def download_file_from_drive(file_name, use_cache=True):
    """구글 드라이브에서 파일을 다운로드합니다. 싱글톤 서비스를 사용하여 오버헤드를 줄입니다."""
    local_path = os.path.join(CACHE_DIR, file_name)
    
    if use_cache and os.path.exists(local_path):
        with open(local_path, 'rb') as f:
            return io.BytesIO(f.read())

    if not drive_service: return None

    try:
        query = f"name = '{file_name}' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if not files: return None
            
        file_id = files[0]['id']
        request = drive_service.files().get_media(fileId=file_id)
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
    # 1. 로컬 캐시 저장
    local_path = os.path.join(CACHE_DIR, file_name)
    df.to_csv(local_path, encoding='utf-8-sig') # 한글 깨짐 방지 위해 utf-8-sig 사용
    
    # 2. 구글 드라이브 업로드
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=True, encoding='utf-8-sig')
    csv_buffer.seek(0)
    upload_raw_file_to_drive(file_name, csv_buffer, "text/csv")


# --- 4. 데이터 로딩 함수 ---
# @st.cache_data를 사용하여 이미 읽은 데이터는 캐시에 저장해 속도를 높입니다.
@st.cache_data
def load_info_data():
    """KOSPI 200 종목 기본 정보(종목코드, 업종 등)를 불러옵니다."""
    if not os.path.exists(CSV_FILE):
        return None
    try:
        df = pd.read_csv(CSV_FILE)
        # 종목코드를 6자리 문자열(예: 005930)로 맞춥니다.
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
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
    오늘 이미 업데이트를 완료했다면 슈퍼 패스트 모드로 즉시 종료합니다.
    """
    status_text = st.empty()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sync_info_file = "last_sync_info.json"

    # --- 슈퍼 패스트 체크 ---
    status_text.info("🚀 동기화 상태 확인 중 (슈퍼 패스트)...")
    sync_info_buffer = download_file_from_drive(sync_info_file)
    if sync_info_buffer:
        try:
            sync_info = json.loads(sync_info_buffer.getvalue().decode('utf-8'))
            if sync_info.get("last_sync_date") == today_str:
                status_text.success(f"✨ 이미 최신 상태입니다! (마지막 동기화: {today_str})")
                time.sleep(2)
                status_text.empty()
                return
        except:
            pass

    progress_bar = st.progress(0)
    total_items = len(df_info)
    raw_today_str = datetime.now().strftime("%Y%m%d")
    
    for idx, row in df_info.iterrows():
        code, name = row['종목코드'], row['종목명']
        if pd.isna(code) or str(code).lower() == 'nan':
            continue
            
        file_name = f"{code}.csv"
        need_download = False
        start_date_download = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        end_date_download = raw_today_str
        existing_df = None

        # 구글 드라이브에서 파일 확인 및 다운로드
        file_buffer = download_file_from_drive(file_name)
        if file_buffer:
            try:
                existing_df = pd.read_csv(file_buffer, index_col=0, parse_dates=True)
                if not existing_df.empty:
                    last_date = existing_df.index[-1]
                    next_date = last_date + timedelta(days=1)
                    if next_date.date() <= datetime.now().date():
                        start_date_download = next_date.strftime("%Y%m%d")
                        need_download = True
            except:
                need_download = True
        else:
            need_download = True

        if need_download:
            status_text.text(f"📥 데이터를 가져오는 중: {name} ({idx+1}/{total_items})")
            try:
                time.sleep(0.1)
                new_df = stock.get_market_ohlcv_by_date(start_date_download, end_date_download, code)
                if not new_df.empty:
                    if existing_df is not None and not existing_df.empty:
                        combined_df = pd.concat([existing_df, new_df])
                        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                        upload_file_to_drive(file_name, combined_df)
                    else:
                        upload_file_to_drive(file_name, new_df)
            except Exception as e:
                st.warning(f"⚠️ {name}({code}) 다운로드 실패: {e}")
        
        progress_bar.progress((idx + 1) / total_items)
    
    # --- 동기화 결과 기록 (슈퍼 패스트용) ---
    new_sync_info = {"last_sync_date": today_str}
    sync_info_json = json.dumps(new_sync_info)
    
    # BytesIO 객체로 변환하여 업로드
    sync_buffer = io.BytesIO(sync_info_json.encode('utf-8'))
    
    # upload_file_to_drive 함수가 DataFrame을 받으므로 JSON 업로드를 위해 별도 처리 필요하지만
    # 기존 업로드 함수를 범용으로 수정하여 사용
    upload_raw_file_to_drive(sync_info_file, sync_buffer, "application/json")

    status_text.success("✅ 모든 데이터가 최신 상태로 업데이트되었습니다!")
    time.sleep(2)
    status_text.empty()
    progress_bar.empty()

def upload_raw_file_to_drive(file_name, content_buffer, mime_type="text/csv"):
    """DataFrame이 아닌 일반 바이너리 데이터를 구글 드라이브에 업로드합니다 (싱글톤 공유)."""
    if not drive_service: return

    try:
        query = f"name = '{file_name}' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        media = MediaIoBaseUpload(content_buffer, mimetype=mime_type, resumable=True)
        
        if files:
            file_id = files[0]['id']
            drive_service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {'name': file_name, 'parents': [GOOGLE_DRIVE_FOLDER_ID]}
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    except Exception as e:
        st.error(f"구글 드라이브 파일 업로드 오류 ({file_name}): {e}")

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
    if target_sector != "전체 업종":
        filtered_info = df_info[df_info['KRX_업종'] == target_sector]

    def process_stock(row):
        code, name, sector = row['종목코드'], row['종목명'], row.get('KRX_업종', '')
        file_name = f"{code}.csv"
        
        # 캐시 활용 및 서비스 오버헤드 제거
        file_buffer = download_file_from_drive(file_name, use_cache=True)
        if not file_buffer: return None
        
        try:
            df = pd.read_csv(file_buffer, index_col=0, parse_dates=True)
            df_filtered = df[(df.index >= calc_start_date) & (df.index <= calc_end_date)]
            
            if len(df_filtered) >= 1:
                start_price = df_filtered.iloc[0]['종가']
                end_price = df_filtered.iloc[-1]['종가']
                if start_price > 0:
                    return {
                        '종목코드': code, '종목명': name, 'KRX_업종': sector,
                        '시작일가': int(start_price), '종료일가': int(end_price),
                        '수익률(%)': round(((end_price - start_price) / start_price) * 100, 2)
                    }
        except: return None
        return None

    results = []
    # 병렬 처리로 속도 대폭 개선 (최대 30개 동시 처리)
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_stock = {executor.submit(process_stock, row): row for _, row in filtered_info.iterrows()}
        for future in concurrent.futures.as_completed(future_to_stock):
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
    if st.button("🔄 데이터 최신화 (1일 1회 권장)"):
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
        
    # 2) 업종 필터 선택
    sectors = ["전체 업종"] + sorted(df_info['KRX_업종'].dropna().unique().tolist())
    target_sector = st.selectbox("KRX 업종 필터", sectors)
    
    # 3) 분석 실행 버튼
    analyze_btn = st.button("🚀 수익률 분석 시작", type="primary")

# --- 7. 메인 화면 ---
st.title("📉 코스피 200 수익률 분석기 PRO")
st.markdown("정확한 데이터를 바탕으로 시장의 흐름을 한눈에 파악하세요.")

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
                label=f"🥇 기간별 수익률 1위: {best_stock['종목명']}", 
                value=f"{best_stock['수익률(%)']}%", 
                delta=f"{best_stock['종료일가'] - best_stock['시작일가']}원"
            )
            
            # 테이블로 데이터 시각화
            # 종목명에 네이버 증권 링크 추가
            top_10['상세페이지'] = top_10['종목코드'].apply(lambda x: f"https://finance.naver.com/item/main.naver?code={x}")
            
            st.dataframe(
                top_10[['상세페이지', '종목명', 'KRX_업종', '시작일가', '종료일가', '수익률(%)']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                    "시작일가": st.column_config.NumberColumn(format="%d"),
                    "종료일가": st.column_config.NumberColumn(format="%d"),
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
                label=f"⚠️ 기간별 하락 1위: {worst_stock['종목명']} ({worst_stock['종목코드']})", 
                value=f"{worst_stock['수익률(%)']}%", 
                delta=f"{worst_stock['종료일가'] - worst_stock['시작일가']}원"
            )
            
            # 테이블로 데이터 시각화
            bottom_10['상세페이지'] = bottom_10['종목코드'].apply(lambda x: f"https://finance.naver.com/item/main.naver?code={x}")
            
            st.dataframe(
                bottom_10[['상세페이지', '종목명', 'KRX_업종', '시작일가', '종료일가', '수익률(%)']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                    "시작일가": st.column_config.NumberColumn(format="%d"),
                    "종료일가": st.column_config.NumberColumn(format="%d"),
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
                    color_discrete_map={'상승': '#ef5350', '하락': '#0d6efd'},
                    barmode='overlay'
                )
                # 0% 기준선 추가
                fig_dist.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="0%")
                st.plotly_chart(fig_dist, use_container_width=True)
                
            with col_chart2:
                if target_sector == "전체 업종":
                    st.subheader("🏢 업종별 평균 수익률")
                    sector_avg = df_results.groupby('KRX_업종')['수익률(%)'].mean().sort_values(ascending=False).reset_index()
                    sector_avg['구분'] = sector_avg['수익률(%)'].apply(lambda x: '상승' if x >= 0 else '하락')
                    fig_sector = px.bar(
                        sector_avg.head(10), 
                        x='수익률(%)', 
                        y='KRX_업종', 
                        orientation='h', 
                        color='구분',
                        color_discrete_map={'상승': '#ef5350', '하락': '#0d6efd'}
                    )
                    st.plotly_chart(fig_sector, use_container_width=True)
                else:
                    st.subheader(f"📈 {target_sector} 내 수익률 순위")
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
                df_results['상세페이지'] = df_results['종목코드'].apply(lambda x: f"https://finance.naver.com/item/main.naver?code={x}")
                # 상세 데이터프레임에서도 수익률 형식을 예쁘게 보여줍니다.
                st.dataframe(
                    df_results.sort_values(by='수익률(%)', ascending=False), 
                    use_container_width=True,
                    column_config={
                        "상세페이지": st.column_config.LinkColumn("링크", display_text="🔗"),
                        "수익률(%)": st.column_config.NumberColumn(format="%.2f%%")
                    }
                )
        else:
            st.error("❌ 분석 결과가 없습니다. 기간 내 데이터가 있는지, 또는 선택한 업종에 종목이 포함되어 있는지 다시 한번 확인해 주세요.")

else:
    # 버튼을 누르기 전 초기 안내 화면
    st.info("💡 왼쪽 사이드바에서 원하는 분석 조건을 설정한 후 **'수익률 분석 시작'** 버튼을 클릭해 주세요.")
    
    # 현재 상태 요약 정보 (메트릭 카드)
    col1, col2, col3 = st.columns(3)
    col1.metric("총 분석 대상", f"{len(df_info)}개 종목")
    # 파일 수정 시간을 이용해 마지막 업데이트 일시 표시
    last_upd = datetime.fromtimestamp(os.path.getmtime(CSV_FILE)).strftime('%Y-%m-%d') if os.path.exists(CSV_FILE) else "없음"
    col2.metric("종목 리스트 업데이트", last_upd)
    col3.metric("데이터 출처", "KRX (한국거래소)")

st.divider()
# 하단 저작권 표시
st.caption("© 2026 KOSPI 200 Analyzer Web PRO | Professional Stock Analysis Tool")
