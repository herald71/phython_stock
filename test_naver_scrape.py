import requests
from bs4 import BeautifulSoup
import re

def get_naver_fundamental(ticker):
    print(f"--- Scraping Naver Finance for {ticker} ---")
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Naver main page has a section with id='_per' and '_pbr'
        # Let's find them
        fundamental = {}
        
        # Look for PER
        per_tag = soup.find('em', id='_per')
        if per_tag:
            fundamental['PER'] = per_tag.get_text()
            
        # Look for PBR
        pbr_tag = soup.find('em', id='_pbr')
        if pbr_tag:
            fundamental['PBR'] = pbr_tag.get_text()
            
        # Look for EPS, BPS
        # These are usually in a table with class 'aside_invest_info'
        aside = soup.find('div', class_='aside_invest_info')
        if aside:
            # find EPS
            # This is harder as it might not have an ID. Search for text "EPS"
            th = aside.find('th', string=re.compile('EPS'))
            if th:
                td = th.find_next_sibling('td')
                if td: fundamental['EPS'] = td.get_text().strip()
                
            th_bps = aside.find('th', string=re.compile('BPS'))
            if th_bps:
                td_bps = th_bps.find_next_sibling('td')
                if td_bps: fundamental['BPS'] = td_bps.get_text().strip()

        print(f"Found: {fundamental}")
        return fundamental
    except Exception as e:
        print(f"Scrape failed: {e}")
        return None

get_naver_fundamental("005930")
