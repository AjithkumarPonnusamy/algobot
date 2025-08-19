
def bep(ce_strike,pe_strike):
    
    val = round(float(ce_strike+pe_strike)/2.0,2)
    return val

def round_to_50(n):
    return round(n / 50) * 50

if __name__ == '__main__':
    bep()

    