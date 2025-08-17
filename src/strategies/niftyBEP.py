import json
import redis
from datetime import datetime
from dhanhq import marketfeed
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.indicators.bep import bep,round_to_50
from src.utils.base import data,dhan
from src.dataaggregators.strikeFinder import strike_value
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
ce = None
pe = None
candle = OHLCBuilder(symbol="nifty",interval_minutes=1)
candle5 = OHLCBuilder(symbol="Nifty",interval_minutes=5)
sub_instruments = [(marketfeed.IDX, "53", marketfeed.Ticker)]
data.subscribe_symbols(sub_instruments)
firstFive = candle5.get_first_candle()
if firstFive != None:
    firstFive = round_to_50(int(firstFive))

underly = 25000
otm = underly+100
def expy():
     exp = dhan.expiry_list(
        under_security_id=13,                       
        under_exchange_segment="IDX_I"
        )
     return exp

def place_order(id):
    try:
        ord = dhan.place_order(security_id=str(id),          
        exchange_segment=dhan.NSE_FNO,
        transaction_type=dhan.BUY,
        quantity=75,
        order_type=dhan.MARKET,
        product_type=dhan.INTRA,
        price=0)
        return ord
    except Exception as e:
        print(f"Error to place order: {e}")
   
def strategy_on_tick(sec_id, ltp,ltt):
    print(f"[Strategy] Tick for {sec_id}: {ltp} : {ltt}")
    if underly != None:
        val = strike_value(underly=underly,expy_date="2025-08-21")
        otm_val = strike_value(underly=otm,expy_date="2025-08-21")
        print(val)
        print("------------------")
        print(f"otm : {otm_val}")

def opt_tick(sec_id,ltp,ltt):
    global ce, pe 
    last_candle_time = None
    
    if sec_id == "450134" and ltp != None:
        ce = round(float(ltp), 2)
        # print(ltp)
        candle.add_tick(ltp=ltp)
        price = candle.get_last_candle()
        if price is not None:
            candle_time = price['time']
            if candle_time != last_candle_time:
                close_value = price
                # print(close_value)
                last_candle_time = candle_time
    elif sec_id == "44473" and ltp != None:
        pe = round(float(ltp), 2)
    if ce is not None and pe is not None:
        bep(ce,pe)
  
def run_strategy():    
    print("[Strategy] Subscribing to live ticks from Redis...")
    pubsub = r.pubsub()
    pubsub.subscribe("ticks")   
    
    for message in pubsub.listen():
        if message["type"] == "message":
            try:                
                data = json.loads(message["data"])
                # print(data)
                sec_id = data["sec_id"]
                ltp = data["ltp"]
                ltt = data["ltt"]
                strategy_on_tick(sec_id, ltp, ltt)                
                # place_order(47252)
                # opt_tick(sec_id,ltp,ltt)
                              
            except json.JSONDecodeError:
                print("[Error] Bad message:", message["data"])

if __name__ == "__main__":
    run_strategy()
