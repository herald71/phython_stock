# ============================================================
# 프로그램명 : kospi200_with_ksic_improved.py
# 작성일자 : 2026-03-02
# 버전     : v1.2
# 설명     : 코스피200 구성종목 + GICS 섹터 + KSIC 대분류 CSV 생성 (위키백과 크롤링 적용)
# ============================================================

import pandas as pd
import requests

# ----------------------------------------------------------------
# 1. 위키백과에서 코스피200 구성종목 가져오기
# ----------------------------------------------------------------
print("위키백과에서 KOSPI 200 목록을 가져오는 중...")
url = "https://ko.wikipedia.org/wiki/%EC%BD%94%EC%8A%A4%ED%94%BC_200"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    response = requests.get(url, headers=headers)
    dfs = pd.read_html(response.text)
    
    df = None
    for temp_df in dfs:
        if "종목코드" in temp_df.columns and "회사명" in temp_df.columns:
            df = temp_df.copy()
            break

    if df is None:
        raise ValueError("KOSPI 200 표를 위키백과에서 찾을 수 없습니다.")

    # 컬럼 정리
    df = df.rename(columns={"회사명": "종목명", "GICS 섹터": "KRX_업종"})
    
    # 종목코드를 6자리 문자열로 변환 (0 채움)
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    
    print(f"총 {len(df)}개 종목 확인 완료.")

except Exception as e:
    print(f"웹 크롤링 오류 발생: {e}")
    exit(1)

# ----------------------------------------------------------------
# 2. KSIC 대분류 매핑 (GICS 섹터를 바탕으로 변환)
# ----------------------------------------------------------------
ksic_mapping = {
    # 제조업 (C)
    "산업재": "제조업",
    "소재": "제조업",
    "철강/소재": "제조업",
    "에너지": "제조업",
    
    # 금융 및 보험업 (K)
    "금융": "금융 및 보험업",

    # 정보통신업 (J)
    "정보기술": "정보통신업",
    "커뮤니케이션서비스": "정보통신업",

    # 도매 및 소매업 (G)
    "생활소비재": "도매 및 소매업",
    "경기소비재": "도매 및 소매업",

    # 건설업 (F)
    "건설": "건설업",

    # 보건업 및 사회복지 서비스업 (Q)
    "헬스케어": "보건업 및 사회복지 서비스업",
    
    # 전기, 가스 공급업 (D)
    "유틸리티": "전기, 가스, 증기 및 공기 조절 공급업",
}

def map_to_ksic(industry):
    if pd.isna(industry) or industry == "정보없음":
        return "기타"
    for key, value in ksic_mapping.items():
        if key in str(industry):
            return value
    return "기타"   # 매핑 안 된 업종은 전부 기타로

df["KSIC_대분류"] = df["KRX_업종"].apply(map_to_ksic)

# 필요한 컬럼만 추출
df = df[["종목코드", "종목명", "KRX_업종", "KSIC_대분류"]]

# ----------------------------------------------------------------
# 3. 결과 확인 & 저장
# ----------------------------------------------------------------
print("\n[업종별 분포]")
print(df["KSIC_대분류"].value_counts())

print("\n[매핑 실패 종목 Top 10]")
unmapped = df[df["KSIC_대분류"] == "기타"]
if len(unmapped) > 0:
    print(unmapped[["종목명", "KRX_업종"]].head(10))
else:
    print("모든 종목이 성공적으로 매핑되었습니다.")

df.to_csv("KOSPI200_with_KSIC_2026.csv", index=False, encoding="utf-8-sig")
print("\n✅ CSV 파일 생성 완료 : KOSPI200_with_KSIC_2026.csv")