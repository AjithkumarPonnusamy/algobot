import psycopg2
import redis
import json
from connections.cache import r
# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="test",
    user="postgres",
    password="ak"
)

cursor = conn.cursor()

def save_to_db(strategy_id,symbol,candle):
    query = """
        INSERT INTO candle_hist (strategy_id,symbol, time, open, high, low, close)
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

pubsub = r.pubsub()
pubsub.subscribe("ohlc_channel")

print("DB Worker listening to Redis...")

for message in pubsub.listen():
    if message["type"] == "message":
        data = json.loads(message["data"])
        save_to_db(data["strategy_id"], data["symbol"], data["candle"])






