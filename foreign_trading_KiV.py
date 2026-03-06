"""
한국투자증권 API - 외국인 매매동향 분석 프로그램
Korea Investment & Securities - Foreign Trading Trend Analysis

필요 패키지 설치:
    pip install requests pandas tabulate colorama python-dotenv

사용법:
    1. .env 파일에 API 키 설정 (또는 직접 입력)
    2. python foreign_trading_KiV.py
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import init, Fore, Style
from dotenv import load_dotenv

# colorama 초기화
init(autoreset=True)

# .env 파일 로드
load_dotenv()

# ─────────────────────────────────────────────────────────────
#  설정 (Config)
# ─────────────────────────────────────────────────────────────
BASE_URL = "https://openapi.koreainvestment.com:9443"  # 실전
# BASE_URL = "https://openapivts.koreainvestment.com:29443"  # 모의

APP_KEY    = os.getenv("KIS_APP_KEY",    "YOUR_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET", "YOUR_APP_SECRET")
ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO", "YOUR_ACCOUNT_NO")   # 예: "12345678-01"

# ─────────────────────────────────────────────────────────────
#  토큰 관리
# ─────────────────────────────────────────────────────────────
_access_token: str = ""
_token_expires: datetime = datetime.min
TOKEN_FILE = ".kis_token.txt"

def get_access_token() -> str:
    """OAuth 액세스 토큰 발급 / 재사용 (.kis_token.txt 공유)"""
    global _access_token, _token_expires

    if _access_token and datetime.now() < _token_expires:
        return _access_token

    # 2. 로컬 파일 확인 (웹 앱과 공유)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                saved_token, saved_time, saved_expire = f.read().strip().split("|")
                expire_dt = datetime.fromisoformat(saved_expire)
                if datetime.now() < expire_dt:
                    _access_token = saved_token
                    _token_expires = expire_dt
                    return _access_token
        except:
            pass # 파일 파싱 실패시 재발급

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey":     APP_KEY,
        "appsecret":  APP_SECRET,
    }
    
    try:
        resp = requests.post(url, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[{Fore.RED}오류{Style.RESET_ALL}] 토큰 발급 통신 오류: {e}")
        return ""

    if "access_token" not in data:
        print(f"[{Fore.RED}오류{Style.RESET_ALL}] 토큰 발급 실패: {data}")
        return ""

    _access_token  = data["access_token"]
    _token_expires = datetime.now() + timedelta(hours=23)
    print(Fore.GREEN + "✔ 새로운 액세스 토큰 발급 완료")
    
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(f"{_access_token}|{datetime.now().isoformat()}|{_token_expires.isoformat()}")
    except:
        pass
        
    return _access_token


def _headers(tr_id: str) -> dict:
    return {
        "content-type":  "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token()}",
        "appkey":        APP_KEY,
        "appsecret":     APP_SECRET,
        "tr_id":         tr_id,
        "custtype":      "P",
    }


# ─────────────────────────────────────────────────────────────
#  1. 지수별 외국인 매매동향  (FHKST01010900)
#     - KOSPI / KOSDAQ / KOSPI200 등
# ─────────────────────────────────────────────────────────────
INDEX_CODE_MAP = {
    "1": ("0001", "KOSPI"),
    "2": ("1001", "KOSDAQ"),
    "3": ("2001", "KOSPI200"),
    "4": ("4001", "KRX100"),
}


def get_index_foreign_trend(index_code: str = "0001", period: str = "D") -> pd.DataFrame:
    """
    지수별 외국인 매매동향 조회
    index_code : 0001=KOSPI, 1001=KOSDAQ, 2001=KOSPI200, 4001=KRX100
    period     : D=일, W=주, M=월
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    params = {
        "FID_COND_MRKT_DIV_CODE": "U",          # 업종
        "FID_INPUT_ISCD":         index_code,
        "FID_PERIOD_DIV_CODE":    period,
        "FID_ORG_ADJ_PRC":        "0",
    }
    resp = requests.get(url, headers=_headers("FHKST01010900"), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        print(Fore.RED + f"[오류] {data.get('msg1')}")
        return pd.DataFrame()

    rows = data.get("output", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 컬럼 선택 및 이름 변경
    col_map = {
        "stck_bsop_date": "날짜",
        "bstp_nmix_prpr": "지수",
        "bstp_nmix_prdy_vrss": "전일대비",
        "prdy_vrss_sign": "등락부호",
        "frgn_ntby_qty": "외국인순매수수량",
        "frgn_ntby_tr_pbmn": "외국인순매수금액(백만)",
        "frgn_seln_vol": "외국인매도수량",
        "frgn_shnu_vol": "외국인매수수량",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 날짜 포맷
    if "날짜" in df.columns:
        df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

    # 숫자 변환
    for col in ["지수", "전일대비", "외국인순매수수량", "외국인순매수금액(백만)", "외국인매도수량", "외국인매수수량"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[list(col_map.values()) if all(v in df.columns for v in col_map.values()) else df.columns]


# ─────────────────────────────────────────────────────────────
#  2. 종목별 외국인 매매동향  (FHKST01010300)
# ─────────────────────────────────────────────────────────────

def get_stock_foreign_trend(stock_code: str, period: str = "D") -> pd.DataFrame:
    """
    종목별 외국인 매매동향 조회
    stock_code : 6자리 종목코드 (예: 005930 = 삼성전자)
    period     : D=일, W=주, M=월
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD":         stock_code,
        "FID_PERIOD_DIV_CODE":    period,
        "FID_ORG_ADJ_PRC":        "0",
    }
    resp = requests.get(url, headers=_headers("FHKST01010300"), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        print(Fore.RED + f"[오류] {data.get('msg1')}")
        return pd.DataFrame()

    rows = data.get("output2", [])
    if not rows:
        rows = data.get("output", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    col_map = {
        "stck_bsop_date": "날짜",
        "stck_clpr":      "종가",
        "prdy_vrss":      "전일대비",
        "prdy_vrss_sign": "등락부호",
        "frgn_ntby_qty":  "외국인순매수",
        "frgn_hldn_qty":  "외국인보유수량",
        "frgn_hldn_rate": "외국인보유비율(%)",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    if "날짜" in df.columns:
        df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

    for col in ["종가", "전일대비", "외국인순매수", "외국인보유수량", "외국인보유비율(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ─────────────────────────────────────────────────────────────
#  3. 외국인 순매수 상위 종목 검색  (FHKST03010200)
# ─────────────────────────────────────────────────────────────

def get_top_foreign_buy(market: str = "J", top_n: int = 20) -> pd.DataFrame:
    """
    외국인 순매수 상위 종목 조회
    market : J=KOSPI, Q=KOSDAQ
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/ranking/foreign-net-buy"
    params = {
        "FID_COND_MRKT_DIV_CODE": market,
        "FID_COND_SCR_DIV_CODE":  "20170",
        "FID_INPUT_ISCD":         "0000",
        "FID_DIV_CLS_CODE":       "0",
        "FID_BLNG_CLS_CODE":      "0",
        "FID_TRGT_CLS_CODE":      "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1":      "",
        "FID_INPUT_PRICE_2":      "",
        "FID_VOL_CNT":            "",
        "FID_INPUT_DATE_1":       "",
    }
    resp = requests.get(url, headers=_headers("FHKST03010200"), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        print(Fore.RED + f"[오류] {data.get('msg1')}")
        return pd.DataFrame()

    rows = data.get("output", [])[:top_n]
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    col_map = {
        "hts_kor_isnm":  "종목명",
        "mksc_shrn_iscd": "종목코드",
        "stck_prpr":      "현재가",
        "prdy_vrss":      "전일대비",
        "prdy_ctrt":      "등락률(%)",
        "frgn_ntby_qty":  "외국인순매수량",
        "frgn_ntby_tr_pbmn": "외국인순매수금액(백만)",
        "frgn_hldn_rate": "외국인보유비율(%)",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    for col in ["현재가", "전일대비", "등락률(%)", "외국인순매수량", "외국인순매수금액(백만)", "외국인보유비율(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.insert(0, "순위", range(1, len(df) + 1))
    return df


# ─────────────────────────────────────────────────────────────
#  4. 외국인 순매도 상위 종목 검색  (FHKST03010200)
# ─────────────────────────────────────────────────────────────

def get_top_foreign_sell(market: str = "J", top_n: int = 20) -> pd.DataFrame:
    """외국인 순매도 상위 종목 조회"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/ranking/foreign-net-buy"
    params = {
        "FID_COND_MRKT_DIV_CODE": market,
        "FID_COND_SCR_DIV_CODE":  "20171",   # 순매도
        "FID_INPUT_ISCD":         "0000",
        "FID_DIV_CLS_CODE":       "0",
        "FID_BLNG_CLS_CODE":      "0",
        "FID_TRGT_CLS_CODE":      "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1":      "",
        "FID_INPUT_PRICE_2":      "",
        "FID_VOL_CNT":            "",
        "FID_INPUT_DATE_1":       "",
    }
    resp = requests.get(url, headers=_headers("FHKST03010200"), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        print(Fore.RED + f"[오류] {data.get('msg1')}")
        return pd.DataFrame()

    rows = data.get("output", [])[:top_n]
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    col_map = {
        "hts_kor_isnm":      "종목명",
        "mksc_shrn_iscd":    "종목코드",
        "stck_prpr":         "현재가",
        "prdy_vrss":         "전일대비",
        "prdy_ctrt":         "등락률(%)",
        "frgn_ntby_qty":     "외국인순매도량",
        "frgn_ntby_tr_pbmn": "외국인순매도금액(백만)",
        "frgn_hldn_rate":    "외국인보유비율(%)",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    for col in ["현재가", "전일대비", "등락률(%)", "외국인순매도량", "외국인순매도금액(백만)", "외국인보유비율(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.insert(0, "순위", range(1, len(df) + 1))
    return df


# ─────────────────────────────────────────────────────────────
#  출력 헬퍼
# ─────────────────────────────────────────────────────────────

def print_header(title: str):
    print("\n" + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + f"  {title}")
    print("=" * 65)


def print_df(df: pd.DataFrame):
    if df.empty:
        print(Fore.YELLOW + "  데이터가 없습니다.")
        return
    print(tabulate(df, headers="keys", tablefmt="fancy_grid",
                   showindex=False, floatfmt=",.0f", numalign="right"))


def color_value(val) -> str:
    """양수=빨강, 음수=파랑으로 색상 표시"""
    try:
        num = float(str(val).replace(",", ""))
        if num > 0:
            return Fore.RED + f"{num:+,.0f}" + Style.RESET_ALL
        elif num < 0:
            return Fore.BLUE + f"{num:+,.0f}" + Style.RESET_ALL
        return f"{num:,.0f}"
    except (ValueError, TypeError):
        return str(val)


# ─────────────────────────────────────────────────────────────
#  CSV 저장
# ─────────────────────────────────────────────────────────────

def save_csv(df: pd.DataFrame, filename: str):
    path = os.path.join(os.path.dirname(__file__), filename)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(Fore.GREEN + f"  💾 저장 완료: {filename}")


# ─────────────────────────────────────────────────────────────
#  메인 메뉴
# ─────────────────────────────────────────────────────────────

def menu_index():
    print_header("지수별 외국인 매매동향")
    print("  1. KOSPI")
    print("  2. KOSDAQ")
    print("  3. KOSPI200")
    print("  4. KRX100")
    choice = input(Fore.YELLOW + "\n  지수 선택 (1~4): ").strip()
    code, name = INDEX_CODE_MAP.get(choice, ("0001", "KOSPI"))

    print("  기간 선택 → D=일간  W=주간  M=월간")
    period = input(Fore.YELLOW + "  기간 입력 [D]: ").strip().upper() or "D"

    print(Fore.CYAN + f"\n  [{name}] 외국인 매매동향 조회 중...")
    df = get_index_foreign_trend(code, period)
    print_header(f"{name} 외국인 매매동향 ({period})")
    print_df(df.head(30))

    save = input(Fore.YELLOW + "\n  CSV로 저장하시겠습니까? (y/n): ").strip().lower()
    if save == "y":
        save_csv(df, f"foreign_{name}_{period}_{datetime.now():%Y%m%d}.csv")


def menu_stock():
    print_header("종목별 외국인 매매동향")
    code = input(Fore.YELLOW + "  종목코드 입력 (예: 005930): ").strip().zfill(6)
    print("  기간 선택 → D=일간  W=주간  M=월간")
    period = input(Fore.YELLOW + "  기간 입력 [D]: ").strip().upper() or "D"

    print(Fore.CYAN + f"\n  [{code}] 외국인 매매동향 조회 중...")
    df = get_stock_foreign_trend(code, period)

    print_header(f"종목 [{code}] 외국인 매매동향 ({period})")
    print_df(df.head(30))

    save = input(Fore.YELLOW + "\n  CSV로 저장하시겠습니까? (y/n): ").strip().lower()
    if save == "y":
        save_csv(df, f"foreign_stock_{code}_{period}_{datetime.now():%Y%m%d}.csv")


def menu_top_buy():
    print_header("외국인 순매수 상위 종목")
    print("  1. KOSPI   2. KOSDAQ")
    mkt = input(Fore.YELLOW + "  시장 선택 [1]: ").strip()
    market = "Q" if mkt == "2" else "J"
    mkt_name = "KOSDAQ" if market == "Q" else "KOSPI"

    n = input(Fore.YELLOW + "  상위 몇 개? [20]: ").strip()
    top_n = int(n) if n.isdigit() else 20

    print(Fore.CYAN + f"\n  [{mkt_name}] 외국인 순매수 상위 {top_n}개 조회 중...")
    df = get_top_foreign_buy(market, top_n)

    print_header(f"{mkt_name} 외국인 순매수 상위 {top_n}개")
    print_df(df)

    save = input(Fore.YELLOW + "\n  CSV로 저장하시겠습니까? (y/n): ").strip().lower()
    if save == "y":
        save_csv(df, f"foreign_top_buy_{mkt_name}_{datetime.now():%Y%m%d}.csv")


def menu_top_sell():
    print_header("외국인 순매도 상위 종목")
    print("  1. KOSPI   2. KOSDAQ")
    mkt = input(Fore.YELLOW + "  시장 선택 [1]: ").strip()
    market = "Q" if mkt == "2" else "J"
    mkt_name = "KOSDAQ" if market == "Q" else "KOSPI"

    n = input(Fore.YELLOW + "  상위 몇 개? [20]: ").strip()
    top_n = int(n) if n.isdigit() else 20

    print(Fore.CYAN + f"\n  [{mkt_name}] 외국인 순매도 상위 {top_n}개 조회 중...")
    df = get_top_foreign_sell(market, top_n)

    print_header(f"{mkt_name} 외국인 순매도 상위 {top_n}개")
    print_df(df)

    save = input(Fore.YELLOW + "\n  CSV로 저장하시겠습니까? (y/n): ").strip().lower()
    if save == "y":
        save_csv(df, f"foreign_top_sell_{mkt_name}_{datetime.now():%Y%m%d}.csv")


def menu_multi_stock():
    """복수 종목 비교 조회"""
    print_header("복수 종목 외국인 보유비율 비교")
    raw = input(Fore.YELLOW + "  종목코드 입력 (쉼표 구분, 예: 005930,000660,035420): ").strip()
    codes = [c.strip().zfill(6) for c in raw.split(",") if c.strip()]

    results = []
    for code in codes:
        print(Fore.CYAN + f"  [{code}] 조회 중...", end="\r")
        df = get_stock_foreign_trend(code, "D")
        if not df.empty:
            latest = df.iloc[0].copy()
            latest["종목코드"] = code
            results.append(latest)
        time.sleep(0.3)   # Rate limit 방지

    if not results:
        print(Fore.RED + "  조회 결과 없음")
        return

    summary = pd.DataFrame(results)
    cols = ["종목코드", "날짜", "종가", "전일대비", "외국인순매수", "외국인보유비율(%)"]
    summary = summary[[c for c in cols if c in summary.columns]]

    print_header("복수 종목 외국인 현황 (최근 1일)")
    print_df(summary)


# ─────────────────────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────────────────────

MENU = {
    "1": ("지수별 외국인 매매동향",       menu_index),
    "2": ("종목별 외국인 매매동향",       menu_stock),
    "3": ("외국인 순매수 상위 종목",      menu_top_buy),
    "4": ("외국인 순매도 상위 종목",      menu_top_sell),
    "5": ("복수 종목 보유비율 비교",      menu_multi_stock),
    "0": ("종료",                         None),
}


def main():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════╗
║       한국투자증권 API - 외국인 매매동향 분석 시스템         ║
║       Korea Investment & Securities Foreign Trading          ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # API 키 확인
    if APP_KEY == "YOUR_APP_KEY":
        print(Fore.RED + "⚠  API 키가 설정되지 않았습니다.")
        print("   .env 파일을 생성하거나 코드 상단의 APP_KEY / APP_SECRET을 설정하세요.\n")
        print(Fore.WHITE + "   .env 예시:")
        print("   KIS_APP_KEY=PSxxxxxxxxxxxxxxxxxxxxxxxx")
        print("   KIS_APP_SECRET=xxxxxxxxxxxxxxxxxx...")
        print("   KIS_ACCOUNT_NO=12345678-01\n")
        return

    while True:
        print("\n" + "─" * 50)
        for k, (label, _) in MENU.items():
            icon = "🔴" if k == "0" else "📊"
            print(f"  {icon} [{k}] {label}")
        print("─" * 50)

        choice = input(Fore.YELLOW + "  메뉴 선택: ").strip()

        if choice == "0":
            print(Fore.GREEN + "\n  프로그램을 종료합니다. 안녕히 가세요! 👋\n")
            break
        elif choice in MENU:
            try:
                MENU[choice][1]()
            except requests.HTTPError as e:
                print(Fore.RED + f"\n  [HTTP 오류] {e}")
            except requests.ConnectionError:
                print(Fore.RED + "\n  [연결 오류] 네트워크 연결을 확인하세요.")
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\n  (메뉴로 돌아갑니다)")
            except Exception as e:
                print(Fore.RED + f"\n  [오류] {e}")
        else:
            print(Fore.RED + "  잘못된 입력입니다. 다시 선택하세요.")


if __name__ == "__main__":
    main()
