import psycopg2
import redis
import json
import threading
from src.connections.cache import r
# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="test",
    user="postgres",
    password="ak"
)

cursor = conn.cursor()

def save_ohlc(strategy_id,symbol,candle):
    query = """
        INSERT INTO market_data.ohlc_data (strategy_id,symbol, candle_time, open, high, low, close)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    cursor.execute(query, (
        strategy_id,
        symbol,
        candle["time"],
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
    ))
    conn.commit()   

def handle_strategy_execution(strategy_id,entry,target1,target2,hit_t1,quantity):
    query = """
        INSERT INTO trades.test (strategy_id,entry,target1,target2,hit_t1,quantity)
        VALUES (%s,%s,%s,%s,%s,%s)
"""
    cursor.execute(query,(
                strategy_id,
                   entry,
                      target1,
                         target2,
                            hit_t1,
                              quantity  ))
    conn.commit()

def run_db_worker():
    pubsub = r.pubsub()
    pubsub.subscribe("ohlc_channel","strategy_exec")

    print("DB Worker listening to Redis...")
    for message in pubsub.listen():
        if message["type"] == "message":
            # print(f"Message : {message}")
            channel = message["channel"]
            data = json.loads(message["data"])
            # print(f"data : {data}")
            # print(f"channel : {channel}")
            
            if channel == "ohlc_channel":
                save_ohlc(data["strategy_id"], data["symbol"], data["candle"])
            elif channel == "strategy_exec":
                handle_strategy_execution(data["strategy_id"],data["entry"],data["target1"],data["target2"],data["hit_t1"],data["quantity"])







