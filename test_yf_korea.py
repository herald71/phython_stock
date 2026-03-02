import yfinance as yf
import pandas as pd
import os
import certifi

# SSL Fix
def setup_ssl():
    import shutil
    import tempfile
    temp_dir = tempfile.gettempdir()
    dest_cert = os.path.join(temp_dir, "python_stock_cacert.pem")
    if not os.path.exists(dest_cert):
        shutil.copy2(certifi.where(), dest_cert)
    os.environ['SSL_CERT_FILE'] = dest_cert
    os.environ['REQUESTS_CA_BUNDLE'] = dest_cert

setup_ssl()

def test_yf_korea(ticker):
    print(f"--- Testing yfinance for {ticker} ---")
    try:
        yt = yf.Ticker(ticker)
        info = yt.info
        print(f"Name: {info.get('longName')}")
        print(f"PER: {info.get('trailingPE')}")
        print(f"PBR: {info.get('priceToBook')}")
        print(f"EPS: {info.get('trailingEps')}")
    except Exception as e:
        print(f"Failed: {e}")

test_yf_korea("005930.KS") # 삼성전자 KOSPI
test_yf_korea("066970.KQ") # 엘앤에프 KOSDAQ
