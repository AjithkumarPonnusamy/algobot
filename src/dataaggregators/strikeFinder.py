import pandas as pd
from src.utils.base import data
df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master-detailed.csv",low_memory=False)
# Filter for NIFTY Futures
# print(df.columns)
def strike_value(underly,expy_date):

    nifty_futures = df[
        (df['UNDERLYING_SYMBOL'].str.upper() == 'NIFTY') &
        (df['INSTRUMENT'].str.upper().str.contains('OPTIDX'))&
        (df['STRIKE_PRICE'] == underly)&
        (df['SM_EXPIRY_DATE'] == expy_date)
    ]

    # Show relevant columns
    nifty_futures_filtered = nifty_futures[[
        'SECURITY_ID', 'SYMBOL_NAME', 'DISPLAY_NAME', 'SM_EXPIRY_DATE', 'EXCH_ID','OPTION_TYPE'
    ]].sort_values(by='SM_EXPIRY_DATE')
    # data.subscribe_symbols()
    return nifty_futures_filtered



if __name__ == "__main__":
    strike_value(24600,"2025-08-21")
