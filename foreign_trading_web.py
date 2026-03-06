import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="종목별 외국인 매매동향", page_icon="📈", layout="wide")

# .env 파일 로드
load_dotenv()

# 프리미엄 스타일을 위한 커스텀 CSS
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        border-color: #0056b3;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 바로가기 및 타이틀 ---
st.markdown(
    """
    <div style="background-color: #ffffff; padding: 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 25px; border-left: 5px solid #007bff;">
        <span style="font-weight: bold; color: #555; margin-right: 10px;">🔗 바로가기:</span> 
        <a href="stock_dashboard.py" target="_self" style="text-decoration: none; color: #007bff; font-weight: 500;">📈 주식 데이터 조회기</a> <span style="color: #ccc; margin: 0 8px;">|</span>
        <a href="https://phythonstock-3ptq9ctv7bluf3euvtmkgr.streamlit.app/" target="_blank" style="text-decoration: none; color: #007bff; font-weight: 500;">📈 데이터 트레이더</a>
    </div>
    """, unsafe_allow_html=True
)

st.title("📈 종목별 외국인 매매동향 분석")

# --- API 설정 ---
BASE_URL = "https://openapi.koreainvestment.com:9443"
APP_KEY = os.getenv("KIS_APP_KEY", "")
APP_SECRET = os.getenv("KIS_APP_SECRET", "")

if not APP_KEY or not APP_SECRET:
    st.error("⚠️ API 키가 설정되지 않았습니다. `.env` 파일에 `KIS_APP_KEY`와 `KIS_APP_SECRET`을 확인해주세요.")
    st.stop()

# --- 토큰 관리 ---
TOKEN_FILE = ".kis_token.txt"

def get_access_token():
    if "kis_access_token" in st.session_state and "kis_token_expires" in st.session_state:
        if datetime.now() < st.session_state["kis_token_expires"]:
            return st.session_state["kis_access_token"]
            
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                saved_token, _, saved_expire = f.read().strip().split("|")
                expire_dt = datetime.fromisoformat(saved_expire)
                if datetime.now() < expire_dt:
                    st.session_state["kis_access_token"] = saved_token
                    st.session_state["kis_token_expires"] = expire_dt
                    return saved_token
        except: pass

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    
    try:
        resp = requests.post(url, json=body, timeout=10)
        data = resp.json()
        if resp.status_code != 200:
            st.error("토큰 발급 실패")
            st.stop()
        
        token = data["access_token"]
        expire_dt = datetime.now() + timedelta(hours=23)
        st.session_state["kis_access_token"] = token
        st.session_state["kis_token_expires"] = expire_dt
        with open(TOKEN_FILE, "w") as f:
            f.write(f"{token}|{datetime.now().isoformat()}|{expire_dt.isoformat()}")
        return token
    except:
        st.error("토큰 발급 오류")
        st.stop()

def _headers(tr_id: str) -> dict:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token()}",
        "appkey": APP_KEY, "appsecret": APP_SECRET,
        "tr_id": tr_id, "custtype": "P",
    }

# --- 스타일링 헬퍼 ---
def style_dataframe(df):
    if df.empty: return df
    
    def color_negative_positive(val):
        if pd.isna(val) or not isinstance(val, (int, float)): return ''
        if val > 0: return 'color: #d63031; font-weight: bold;'
        if val < 0: return 'color: #0984e3; font-weight: bold;'
        return 'color: #2d3436;'

    format_dict = {}
    for col in df.columns:
        if "등락률" in col or "보유비율" in col:
            format_dict[col] = "{:+.2f}%" if "등락률" in col else "{:.2f}%"
        elif any(k in col for k in ["전일대비", "가", "지수", "수량", "금액", "순매수", "순매도"]):
            format_dict[col] = "{:+,}" if "전일대비" in col or "순매수" in col or "순매도" in col else "{:,.0f}"

    subset_colors = [c for c in df.columns if any(k in c for k in ["전일대비", "등락률", "순매수", "순매도"])]
    numeric_cols = df.select_dtypes(include=['number']).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    return df.style.map(color_negative_positive, subset=subset_colors).format(format_dict, na_rep="-")

# --- 데이터 조회 ---
@st.cache_data(ttl=300)
def get_stock_foreign_trend(stock_code: str, period: str) -> pd.DataFrame:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code, "FID_PERIOD_DIV_CODE": period, "FID_ORG_ADJ_PRC": "0"}
    
    try:
        resp = requests.get(url, headers=_headers("FHKST01010900"), params=params, timeout=10)
        data = resp.json()
        if data.get("rt_cd") != "0": return pd.DataFrame()
        rows = data.get("output", [])
        if not rows: return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        col_map = {
            "stck_bsop_date": "날짜", 
            "stck_clpr": "종가", 
            "prdy_vrss": "전일대비", 
            "frgn_ntby_qty": "외국인순매수수량",
            "frgn_hldn_rate": "외국인보유비율(%)"
        }
        target_cols = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=target_cols)
        
        if "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
        
        for col in df.columns:
            if col != "날짜":
                df[col] = pd.to_numeric(df[col], errors="coerce")
                
        return df[[c for c in col_map.values() if c in df.columns]]
    except: return pd.DataFrame()

# --- 메인 화면 구성 ---
st.divider()
c1, c2 = st.columns([2, 1])
with c1:
    s_code = st.text_input("종목코드 6자리 (예: 삼성전자 005930)", "005930")
with c2:
    period_map = {"일간": "D", "주간": "W", "월간": "M"}
    sel_period = st.selectbox("데이터 주기", options=["일간", "주간", "월간"], index=0)

if st.button("분석 실행"):
    if len(s_code) == 6 and s_code.isdigit():
        with st.spinner(f'[{s_code}] 매매 데이터 조회 중...'):
            df = get_stock_foreign_trend(s_code, period_map[sel_period])
            if not df.empty:
                st.success(f"✅ **[{s_code}]** 분석 결과")
                st.markdown(f"[🔗 네이버증권 상세보기](https://finance.naver.com/item/main.naver?code={s_code})")
                st.dataframe(style_dataframe(df), use_container_width=True, hide_index=True)
            else:
                st.error("데이터를 찾을 수 없습니다. 종목코드를 확인하십시오.")
    else:
        st.warning("올바른 6자리 숫자를 입력하세요.")

st.divider()
st.caption("본 프로그램은 교육 및 참고용이며, 투자 결과에 대한 책임은 본인에게 있습니다. | v1.3")
