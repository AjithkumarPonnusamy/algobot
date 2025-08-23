import json
from datetime import datetime
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.indicators.bep import bep, round_to_50
from src.dataaggregators.strikeFinder import strike_value
from src.connections.cache import r
from src.connections.connectTel import send_telegram_message
from src.connections.connectDB import conn

class NiftyOTMStrategy():
    def __init__(self, feed, quantity=75, underlying_symbol="13"):
        """
        Initialize the Options Strategy
        """
        self.feed = feed
        self.quantity = quantity
        self.underlying_symbol = underlying_symbol  # security ID for underlying

        # State
        self.under = None
        self.subscribed = False

        # Strike IDs
        self.atm_ce_id = self.atm_pe_id = None
        self.otm_ce_id = self.otm_pe_id = None

        # LTPs
        self.atm_ce_ltp = self.atm_pe_ltp = None
        self.otm_ce_ltp = self.otm_pe_ltp = None

        # BEPs
        self.atm_bep = self.otm_bep = None

        # OHLC Builders
        self.nifty_5 = OHLCBuilder("nifty",interval_minutes=5,db_conn=conn)
        self.atm_ce_1 = OHLCBuilder("atm_ce",interval_minutes=1,db_conn=conn)
        self.atm_ce_3 = OHLCBuilder("atm_ce",interval_minutes=3)
        self.atm_pe_1 = OHLCBuilder("atm_pe",interval_minutes=1,db_conn=conn)
        self.atm_pe_3 = OHLCBuilder("atm_pe",interval_minutes=3)

        #OHLC Logger
        self.nifty_5_ohlc = None
        self.atm_ce_1_ohlc = None
        self.atm_ce_3_ohlc = None
        self.atm_pe_1_ohlc = None
        self.atm_pe_3_ohlc = None
        self.nifty_5_lct = None    
        self.atm_ce_1_lct =None
        self.atm_pe_1_lct = None             #last candle time

        # Redis pubsub
        self.pubsub = r.pubsub()

    # ------------------------ Orders ------------------------
    def place_order(self, security_id):
        """Place a market order"""
        try:
            order_response = self.feed.dhan.place_order(
                security_id=str(security_id),
                exchange_segment=self.feed.dhan.NSE_FNO,
                transaction_type=self.feed.dhan.BUY,
                quantity=self.quantity,
                order_type=self.feed.dhan.MARKET,
                product_type=self.feed.dhan.INTRA,
                price=0,
            )
            msg = f"✅ Order placed: {order_response}"
            send_telegram_message(msg)
            print(msg)
            return order_response
        except Exception as e:
            error_msg = f"❌ Order failed for {security_id}: {e}"
            print(error_msg)
            send_telegram_message(error_msg)
            return None

    # ------------------------ Subscription ------------------------
    def assign_underlying(self, candle):
        """Set underlying strike based on OHLC close"""
        if candle:
            close_price = candle.get("close")
            if close_price:
                self.under = round_to_50(int(close_price))
                print(f"[Strategy] Underlying updated → {self.under}")

    def subscribe_options(self):
        """Subscribe to ATM & OTM option strikes once underlying is known"""
        if self.under and not self.subscribed:
            try:
                atm = self.under + 100
                ce_otm_val, pe_otm_val = atm + 100, atm - 100
                self.otm_ce_id, self.otm_pe_id = strike_value(ce_otm_val, pe_otm_val, self.feed.expiry_date)

                ce_atm_val, pe_atm_val = atm, atm - 50
                self.atm_ce_id, self.atm_pe_id = strike_value(ce_atm_val, pe_atm_val, self.feed.expiry_date)

                print(f"[Strategy] OTM → CE: {self.otm_ce_id}, PE: {self.otm_pe_id}")
                print(f"[Strategy] ATM → CE: {self.atm_ce_id}, PE: {self.atm_pe_id}")
                self.subscribed = True
            except Exception as e:
                print(f"[Strategy Error] Option subscription failed: {e}")

    # ------------------------ Tick Processing ------------------------
    def process_underlying_tick(self, sec_id, ltp):
        """Handle Nifty (underlying) ticks"""
        if sec_id == self.underlying_symbol and ltp:
            self.nifty_5.add_tick(ltp)
            candle = self.nifty_5.get_first_candle()
            if candle:
                self.assign_underlying(candle)

    def process_options_tick(self, sec_id, ltp):
        """Handle option ticks"""
        if not self.subscribed:
            self.subscribe_options()

        if sec_id == self.otm_ce_id: self.otm_ce_ltp = ltp
        elif sec_id == self.otm_pe_id: self.otm_pe_ltp = ltp
        elif sec_id == self.atm_ce_id:
            self.atm_ce_ltp = ltp
            self.atm_ce_1.add_tick(ltp)
            self.atm_ce_3.add_tick(ltp)
        elif sec_id == self.atm_pe_id:
            self.atm_pe_ltp = ltp
            self.atm_pe_1.add_tick(ltp)
            self.atm_pe_3.add_tick(ltp)

        # BEPs
        if self.otm_ce_ltp and self.otm_pe_ltp:
            self.otm_bep = bep(self.otm_ce_ltp, self.otm_pe_ltp)
            # print(self.otm_bep)
        if self.atm_ce_ltp and self.atm_pe_ltp:
            self.atm_bep = bep(self.atm_ce_ltp, self.atm_pe_ltp)
            # print(self.atm_bep)

    def execute_strategy_logic(self):
        if self.atm_ce_1_ohlc['close'] > self.otm_bep:
            self.place_order(self.atm_ce_id)
        pass

    def save_OHLC(self):
        self.nifty_5_ohlc = self.nifty_5.get_last_candle()
        self.atm_ce_1_ohlc = self.atm_ce_1.get_last_candle()
        self.atm_ce_3_ohlc = self.atm_ce_3.get_last_candle()
        self.atm_pe_1_ohlc = self.atm_ce_1.get_last_candle()
        self.atm_pe_3_ohlc = self.atm_ce_3.get_last_candle()
        if self.nifty_5_ohlc is not None:
            candle_time = self.nifty_5_ohlc['time']
            if candle_time != self.nifty_5_lct:
                close_value = self.nifty_5_ohlc # or just use price if you want dict
                # send_telegram_message(f"order triggered at close 1minute {close_value}")
                self.nifty_5.save_to_db(close_value)
                self.nifty_5_lct = candle_time
        
        if self.atm_ce_1_ohlc is not None:
            candle_time = self.atm_ce_1_ohlc['time']
            if candle_time != self.atm_ce_1_lct:
                close_value = self.atm_ce_1_ohlc # or just use price if you want dict
                # send_telegram_message(f"order triggered at close 1minute {close_value}")
                self.atm_ce_1.save_to_db(close_value)
                self.atm_ce_1_lct = candle_time
        
        if self.atm_pe_1_ohlc is not None:
            candle_time = self.atm_pe_1_ohlc['time']
            if candle_time != self.atm_pe_1_lct:
                close_value = self.atm_pe_1_ohlc # or just use price if you want dict
                # send_telegram_message(f"order triggered at close 1minute {close_value}")
                self.atm_pe_1.save_to_db(close_value)
                self.atm_pe_1_lct = candle_time

    def process_tick(self, sec_id, ltp, ltt):
        """Main dispatcher for ticks"""
        self.process_underlying_tick(sec_id, ltp)
        self.process_options_tick(sec_id, ltp)
        self.save_OHLC()
        self.execute_strategy_logic()

    # ------------------------ Run ------------------------
    def run_strategy(self):
        print(f"[Strategy] Running | Expiry: {self.feed.expiry_date}, Qty: {self.quantity}")
        self.pubsub.subscribe("ticks")
        print("[Strategy] Listening to Redis ticks...")

        try:
            for msg in self.pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        self.process_tick(data["sec_id"], data["ltp"], data["ltt"])
                        
                    except Exception as e:
                        print(f"[Strategy Error] {e}")
        except KeyboardInterrupt:
            print("[Strategy] Stopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Unsubscribe & cleanup"""
        try:
            self.pubsub.unsubscribe("ticks")
            self.pubsub.close()
            print("[Strategy] Clean exit ✅")
        except Exception as e:
            print(f"[Strategy Error] Cleanup failed: {e}")

    def get_status(self):
        """Current strategy state"""
        return {
            "underlying": self.under,
            "subscribed": self.subscribed,
            "ATM": {"CE": self.atm_ce_id, "PE": self.atm_pe_id, "BEP": self.atm_bep},
            "OTM": {"CE": self.otm_ce_id, "PE": self.otm_pe_id, "BEP": self.otm_bep},
        }

    def reset_subscription(self):
        """
        Reset subscription status (useful for testing or restarting)
        """
        self.subscribed = False
        self.otm_ce_id = None
        self.otm_pe_id = None
        self.last_ce_ltp = None
        self.last_pe_ltp = None
        print("[Strategy] Subscription reset")


# Usage example
if __name__ == "__main__":
    # Create strategy instance
    strategy = NiftyOTMStrategy(
        base_strike=25000,
        expiry_date="2025-08-21",
        quantity=75
    )
    
    # Print initial status
    print(f"[Strategy] Initial status: {strategy.get_status()}")
    
    # Start the strategy
    strategy.run_strategy()
