import FinanceDataReader as fdr
import sys

def test_listing(market):
    print(f"Testing market: {market}")
    try:
        df = fdr.StockListing(market)
        print(f"Success! {market} returned {len(df)} rows.")
        return True
    except Exception as e:
        print(f"Failed for {market}: {type(e).__name__}: {e}")
        return False

markets = ['KRX', 'KOSPI', 'KOSDAQ', 'KONEX', 'KRX-DESC']

for m in markets:
    test_listing(m)
    print("-" * 20)
