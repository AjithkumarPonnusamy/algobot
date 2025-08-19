import pandas as pd
df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master-detailed.csv",low_memory=False)
# Filter for NIFTY Futures
# print(df.columns)

def strike_value(underly,expy_date):

    ce_strike = df[
        (df['UNDERLYING_SYMBOL'].str.upper() == 'NIFTY') &
        (df['INSTRUMENT'].str.upper().str.contains('OPTIDX'))&
        (df['STRIKE_PRICE'] == underly)&
        (df['SM_EXPIRY_DATE'] == expy_date)&
        (df['OPTION_TYPE'] == 'CE')
    ]

    pe_strike = df[
        (df['UNDERLYING_SYMBOL'].str.upper() == 'NIFTY') &
        (df['INSTRUMENT'].str.upper().str.contains('OPTIDX'))&
        (df['STRIKE_PRICE'] == underly)&
        (df['SM_EXPIRY_DATE'] == expy_date)&
        (df['OPTION_TYPE'] == 'PE')
    ] 
    

    ce = ce_strike[[
        'SECURITY_ID'
    ]]

    pe = pe_strike[[
        'SECURITY_ID'
    ]]
    ce_dict = ce.to_dict(orient="records")[0] if not ce.empty else None
    pe_dict = pe.to_dict(orient="records")[0] if not pe.empty else None
    stk = {
    'CE': ce_dict,
    'PE': pe_dict
    }
    ce_id = str(stk["CE"]["SECURITY_ID"])
    pe_id = str(stk["PE"]["SECURITY_ID"])
    print(ce_id)
    
   
    
    return [ce_id,pe_id]


def get_strikes(exp, underlying_price):
    """
    Get 20 CE and 20 PE strikes around the underlying price for a given expiry.
    Returns SECURITY_IDs as a list.
    """
    # Filter NIFTY option instruments for the given expiry
    ce_pe_df = df[
        (df['UNDERLYING_SYMBOL'].str.upper() == 'NIFTY') &
        (df['INSTRUMENT'].str.upper().str.contains('OPTIDX')) &
        (df['SM_EXPIRY_DATE'] == exp)
    ]

    # Define lower and upper strike bounds
    lower_strike = underlying_price - 20 * 50  # Assuming strike interval is 50
    upper_strike = underlying_price + 20 * 50

    strikes_df = ce_pe_df[
        (ce_pe_df['STRIKE_PRICE'] >= lower_strike) &
        (ce_pe_df['STRIKE_PRICE'] <= upper_strike)
    ]

    # Convert SECURITY_ID column to a list
    strike_ids = strikes_df['SECURITY_ID'].tolist()
    return strike_ids


if __name__ == "__main__":
    # strike_value(24600,"2025-08-21")
    print(get_strikes("2025-08-21", 24900))
