import FinanceDataReader as fdr
import pandas as pd

def test_listing(market):
    try:
        print(f"Testing market: {market}...")
        df = fdr.StockListing(market)
        print(f"Success! {market} has {len(df)} rows.")
        print(df.head(2))
        return True
    except Exception as e:
        print(f"Failed! {market} error: {e}")
        return False

markets = ['KRX-DESC', 'KRX', 'KOSPI', 'KOSDAQ', 'KONEX']
for m in markets:
    test_listing(m)
