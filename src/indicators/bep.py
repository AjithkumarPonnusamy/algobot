import math
def bep(ce_strike,pe_strike):
    
    val = round(float(ce_strike+pe_strike)/2.0,2)
    return val

def round_to_50(n):
    return round(n / 50) * 50

def floor_to_50(value: float) -> int:
    return math.floor(value / 50) * 50

if __name__ == '__main__':
    print(round_to_50(24787.7500))
    print(floor_to_50(24740))

    