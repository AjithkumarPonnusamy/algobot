# import psycopg2
import json
import redis
from dhanhq import marketfeed
from dhanhq import dhanhq
from src.dataaggregators.candleAggregator import OHLCBuilder
import os
from dotenv import load_dotenv
load_dotenv(".env")
# import threading

# Redis connection
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Dhan API details

client_id = os.getenv("CLIENT_ID")
access_token = os.getenv("ACCESS_TOKEN")

# Instruments to subscribe
instruments = [(marketfeed.IDX, "13", marketfeed.Ticker),
               (marketfeed.MCX, "450134", marketfeed.Ticker),
               (marketfeed.NSE_FNO, "44472", marketfeed.Ticker)]  # Example: Nifty Index
version = "v2"
dhan = dhanhq(client_id,access_token)
# def save_tick_to_db(security_id, ltp):
#     cursor.execute(
#         "INSERT INTO ticks (security_id, ltp) VALUES (%s, %s)",
#         (security_id, ltp)
#     )
nifty = OHLCBuilder("Nifty",interval_minutes=5)
fir = nifty.get_first_candle()
las = nifty.get_last_candle()


sym = str(44473)
data = marketfeed.DhanFeed(client_id, access_token, instruments, "v2")
def run_feed():
    print("[Feed] Starting Dhan feed...")    
    while True:
        data.run_forever()
        res = data.get_data()
        # print(res)
        if res and res.get("LTP"):
            tick_data = {
            "sec_id": str(res["security_id"]),
            "ltp": float(res["LTP"]),
            "ltt": str(res["LTT"])
        }
        nifty.save_to_db(las)
        # Publish JSON string
        r.publish("ticks", json.dumps(tick_data))

# sub_instruments = [(marketfeed.IDX, "51", marketfeed.Ticker)]
# data.subscribe_symbols(sub_instruments)

if __name__ == "__main__":
    run_feed()