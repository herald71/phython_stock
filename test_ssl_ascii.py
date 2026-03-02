import os
import certifi
import shutil
import tempfile
import yfinance as yf

# SSL 해결 시도: 비-한글 경로로 인증서 복사
def setup_ssl():
    try:
        # 시스템 임시 폴더 (보통 ASCII 경로)
        temp_dir = tempfile.gettempdir()
        root_cert = certifi.where()
        dest_cert = os.path.join(temp_dir, "cacert.pem")
        
        shutil.copy2(root_cert, dest_cert)
        
        os.environ['SSL_CERT_FILE'] = dest_cert
        os.environ['REQUESTS_CA_BUNDLE'] = dest_cert
        print(f"SSL cert moved to: {dest_cert}")
    except Exception as e:
        print(f"Setup SSL failed: {e}")

print("--- Testing yfinance with clean SSL path ---")
setup_ssl()

try:
    ticker = "AAPL"
    yt = yf.Ticker(ticker)
    print(f"Fetching info for {ticker}...")
    info = yt.info
    print(f"Success! PER: {info.get('trailingPE')}")
except Exception as e:
    print(f"yfinance failed: {e}")
