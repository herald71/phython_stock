import requests
from bs4 import BeautifulSoup

def get_naver_fundamentals(ticker):
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # PER, EPS
        # Naver Finance 구조상 id="aside" 영역에 PER, EPS 등이 있음
        aside = soup.find('div', id='aside')
        if not aside:
            return None
            
        data = {}
        
        # PER, EPS 찾기
        per_tag = aside.find('em', id='_per')
        if per_tag:
            data['PER'] = per_tag.get_text()
        
        eps_tag = aside.find('em', id='_eps')
        if eps_tag:
            data['EPS'] = eps_tag.get_text()
            
        # PBR, BPS 찾기
        pbr_tag = aside.find('em', id='_pbr')
        if pbr_tag:
            data['PBR'] = pbr_tag.get_text()
            
        return data
        
    except Exception as e:
        print(f"Error scraping Naver Finance: {e}")
        return None

ticker = "005930" # 삼성전자
print(f"Fetching fundamentals for {ticker} from Naver Finance...")
fundamentals = get_naver_fundamentals(ticker)

if fundamentals:
    print("\nSamsung Electronics Fundamentals (Naver):")
    print(f"EPS: {fundamentals.get('EPS', 'N/A')}원")
    print(f"PER: {fundamentals.get('PER', 'N/A')}배")
    print(f"PBR: {fundamentals.get('PBR', 'N/A')}배")
else:
    print("Failed to fetch data from Naver Finance.")
