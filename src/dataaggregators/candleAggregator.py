from datetime import datetime, timedelta

class OHLCBuilder:
    def __init__(self,symbol, interval_minutes,db_conn=None):
        self.interval = timedelta(minutes=interval_minutes)
        self.tf = str(interval_minutes)
        self.symbol = symbol
        self.db_conn = db_conn
        self.current_candle = None
        self.current_time = None
        self.ohlc_list = []

    def _get_candle_start_time(self, timestamp):
        interval_seconds = self.interval.total_seconds()
        timestamp_seconds = timestamp.timestamp()
        candle_start_timestamp = timestamp_seconds - (timestamp_seconds % interval_seconds)
        
        return datetime.fromtimestamp(candle_start_timestamp)

    def add_tick(self, ltp, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()

        timestamp = timestamp.replace(second=0, microsecond=0)
        candle_time = self._get_candle_start_time(timestamp)

        # Start a new candle
        if self.current_time != candle_time:
            if self.current_candle:
                self.current_candle["final"] = True
                self.ohlc_list.append(self.current_candle)
                # print("✅ Candle closed:", self.current_candle)
            self.current_time = candle_time
            self.current_candle = {
                "symbol":self.symbol,
                "time": candle_time,
                "open": ltp,
                "high": ltp,
                "low": ltp,
                "close": ltp,
                "final": False 
            }
        else:
            # Update existing candle
            self.current_candle["high"] = max(self.current_candle["high"], ltp)
            self.current_candle["low"] = min(self.current_candle["low"], ltp)
            self.current_candle["close"] = ltp

    def get_last_candle(self):
        return self.ohlc_list[-1] if self.ohlc_list else None
    
    def get_first_candle(self):
        return self.ohlc_list[0] if self.ohlc_list else None

    def get_all_ohlc(self):
        return self.ohlc_list

    def save_to_db(self, ohlc_row):
        if not ohlc_row or not self.db_conn:
            return
        try:
            with self.db_conn.cursor() as cur:
                # print(ohlc_row)
                cur.execute(
                    """
                    INSERT INTO candle_hist (symbol, time, open, high, low, close,timeframe)
                    VALUES (%s, %s, %s, %s, %s, %s,%s)
                    """,
                    (
                        ohlc_row["symbol"],
                        ohlc_row["time"],
                        ohlc_row["open"],
                        ohlc_row["high"],
                        ohlc_row["low"],
                        ohlc_row["close"],
                        self.tf
                    )
                )
                self.db_conn.commit()
        except Exception as e:
            print(f"Error saving to DB: {e}")
            self.db_conn.rollback()