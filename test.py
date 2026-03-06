import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")

# access token은 별도 발급 필요
ACCESS_TOKEN = os.getenv("KIS_ACCESS_TOKEN")

BASE_URL = "https://openapi.koreainvestment.com:9443"
PATH = "/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate"
URL = BASE_URL + PATH

headers = {
    "Content-Type": "application/json",
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appKey": APP_KEY,
    "appSecret": APP_SECRET,
    "tr_id": "FHKST644100C0",
    "custtype": "P"
}

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_COND_SCR_DIV_CODE": "20171"
}

res = requests.get(URL, headers=headers, params=params)

print(res.json())