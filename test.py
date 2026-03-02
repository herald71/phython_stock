import FinanceDataReader as fdr
import requests

from bs4 import BeautifulSoup

def get_fundamentals(ticker):
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        aside = soup.find('div', id='aside')
        if not aside: return {}
        return {
            'PER': aside.find('em', id='_per').get_text() if aside.find('em', id='_per') else 'N/A',
            'EPS': aside.find('em', id='_eps').get_text() if aside.find('em', id='_eps') else 'N/A',
            'PBR': aside.find('em', id='_pbr').get_text() if aside.find('em', id='_pbr') else 'N/A',
        }
    except: return {}

# 삼성전자(005930) 예시
df = fdr.StockListing('KRX-DESC')
samsung = df[df['Code'] == '005930']
ticker = '005930'

# 기본 정보 가져오기 (KRX-DESC)
sector = samsung['Sector'].values[0]
industry = samsung['Industry'].values[0]

# 투자 지표 가져오기 (Naver)
funds = get_fundamentals(ticker)

# 결과 출력
print(f"삼성전자 업종: {sector}")
print(f"삼성전자 주요상품: {industry}")
print(f"삼성전자 EPS: {funds.get('EPS')}원")
print(f"삼성전자 PER: {funds.get('PER')}배")
print(f"삼성전자 PBR: {funds.get('PBR')}배")
