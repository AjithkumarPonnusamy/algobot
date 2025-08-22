import json
from datetime import datetime
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.indicators.bep import bep, round_to_50
from src.dataaggregators.strikeFinder import strike_value
from src.connections.cache import r
from src.connections.connectTel import send_telegram_message
from src.connections.connectDB import conn

class NiftyATMStrategy():
    def __init__(self, feed, quantity=150, underlying_symbol="13"):
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

        # LTPs
        self.atm_ce_ltp = self.atm_pe_ltp = None

        # BEPs
        self.atm_bep = None

        # store entry price if in trade
        self.position = {
            "CE": None,
            "PE": None
        }  

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
    def place_order(self, security_id,price = None ,side="BUY",order_type="MARKET",quantity=None):
        """Place a market order"""
        try:
            qty = quantity if quantity is not None else self.quantity
            order_response = self.feed.dhan.place_order(
                security_id=str(security_id),
                exchange_segment=self.feed.dhan.NSE_FNO,
                transaction_type=self.feed.dhan.BUY if side.upper() == "BUY" else self.feed.dhan.SELL,
                quantity=qty,
                order_type=self.feed.dhan.MARKET if order_type.upper() == "MARKET" else self.feed.dhan.LIMIT,
                product_type=self.feed.dhan.INTRA,
                price=price if order_type.upper() == "LIMIT" else 0,  # price only for LIMIT
            )
            msg = f"✅ {side.upper()} {order_type.upper()} order placed: {order_response} | Qty: {qty}"
            send_telegram_message(msg)
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
                atm = self.under 
                
                ce_atm_val, pe_atm_val = atm - 50, atm 
                self.atm_ce_id, self.atm_pe_id = strike_value(ce_atm_val, pe_atm_val, self.feed.expiry_date)
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

        if sec_id == self.atm_ce_id:
            self.atm_ce_ltp = ltp
            # print(self.atm_ce_1_ohlc['close'])
            self.atm_ce_1.add_tick(ltp)
            self.atm_ce_3.add_tick(ltp)
        elif sec_id == self.atm_pe_id:
            self.atm_pe_ltp = ltp
            self.atm_pe_1.add_tick(ltp)
            self.atm_pe_3.add_tick(ltp)

        if self.atm_ce_ltp and self.atm_pe_ltp:
            self.atm_bep = bep(self.atm_ce_ltp, self.atm_pe_ltp)
            # print(self.atm_bep)


    def save_OHLC(self):
        self.nifty_5_ohlc = self.nifty_5.get_last_candle()
        self.atm_ce_1_ohlc = self.atm_ce_1.get_last_candle()
        self.atm_ce_3_ohlc = self.atm_ce_3.get_last_candle()
        self.atm_pe_1_ohlc = self.atm_ce_1.get_last_candle()
        self.atm_pe_3_ohlc = self.atm_ce_3.get_last_candle()
        if self.nifty_5_ohlc is not None:
            candle_time = self.nifty_5_ohlc['time']
            if candle_time != self.nifty_5_lct:
                close_value = self.nifty_5_ohlc 
                self.nifty_5.save_to_db(close_value)
                self.nifty_5_lct = candle_time
        
        if self.atm_ce_1_ohlc is not None:
            candle_time = self.atm_ce_1_ohlc['time']
            if candle_time != self.atm_ce_1_lct:
                close_value = self.atm_ce_1_ohlc
                self.atm_ce_1.save_to_db(close_value)
                self.atm_ce_1_lct = candle_time
        
        if self.atm_pe_1_ohlc is not None:
            candle_time = self.atm_pe_1_ohlc['time']
            if candle_time != self.atm_pe_1_lct:
                close_value = self.atm_pe_1_ohlc 
                self.atm_pe_1.save_to_db(close_value)
                self.atm_pe_1_lct = candle_time

    
    def execute_strategy_logic(self):
        if self.atm_ce_1_ohlc is not None:
            ce_close = self.atm_ce_1_ohlc['close']
             # Entry condition
            if ce_close > self.atm_bep and self.position["CE"] is None:
                self.place_order(price=pe_close,order_type="Limit",side="Buy",security_id=self.atm_ce_id)
                self.position["CE"] = {
                    "entry": ce_close,
                    "target1": ce_close + 15,
                    "target2": ce_close + 30,
                    "hit_t1": False
                }
                print(f"[STRATEGY] Entered CE at {ce_close}")

            # Target checks
            elif self.position["CE"] is not None:
                entry_data = self.position["CE"]

                # First Target
                if not entry_data["hit_t1"] and ce_close >= entry_data["target1"]:
                    sell_qty = entry_data["quantity"] // 2
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 1 at {ce_close} (+15) → Sell {sell_qty}")
                        self.place_order(
                            price=ce_close,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_ce_id,
                            quantity=sell_qty
                        )
                        entry_data["quantity"] -= sell_qty
                    entry_data["hit_t1"] = True

                # Second Target -> Exit
                if ce_close >= entry_data["target2"]:
                    sell_qty = entry_data["quantity"]
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 2 at {ce_close} (+30) → Exit {sell_qty}")
                        self.place_order(
                            price=ce_close,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_ce_id,
                            quantity=sell_qty
                        )
                    self.position["CE"] = None

                 # Exit condition - falls below BEP
                if ce_close < self.atm_bep and self.position["CE"] is not None:
                    sell_qty = entry_data["quantity"]
                    if sell_qty > 0:
                        print(f"[STOPLOSS] CE hit Stop Loss at {ce_close} → Exit {sell_qty}")
                        self.place_order(
                        price=ce_close,
                        order_type="Market",   # better for stop loss exit
                        side="Sell",
                        security_id=self.atm_ce_id,
                        quantity=sell_qty
                        )
                    self.position["CE"] = None

        # ✅ PE Logic
        if self.atm_pe_1_ohlc is not None:
            pe_close = self.atm_pe_1_ohlc['close']

            # Entry condition
            if pe_close > self.atm_bep and self.position["PE"] is None:
                self.place_order(price=pe_close,order_type="Limit",side="Buy",security_id=self.atm_pe_id)
                self.position["PE"] = {
                    "entry": pe_close,
                    "target1": pe_close + 15,
                    "target2": pe_close + 30,
                    "hit_t1": False
                }
                print(f"[STRATEGY] Entered PE at {pe_close}")

            # Exit condition - falls below BEP
            elif pe_close < self.atm_bep and self.position["PE"] is not None:
                print(f"[STRATEGY] Exited PE at {pe_close} (below BEP)")
                self.place_order(price=pe_close,order_type="Limit",side="Sell",security_id=self.atm_pe_id)
                self.position["PE"] = None

            # Target checks
            elif self.position["PE"] is not None:
                entry_data = self.position["PE"]

                # First Target
                if not entry_data["hit_t1"] and pe_close >= entry_data["target1"]:
                    print(f"[TARGET] PE hit Target 1 at {pe_close} (+15)")
                    self.place_order(price=pe_close,order_type="Limit",side="Sell",security_id=self.atm_pe_id)
                    entry_data["hit_t1"] = True

                # Second Target -> Exit
                if pe_close >= entry_data["target2"]:
                    self.exit_position(self.atm_pe_id, int(pe_close))
                    print(f"[TARGET] PE hit Target 2 at {pe_close} (+30) → EXIT")
                    self.place_order(price=pe_close,order_type="Limit",side="Sell",security_id=self.atm_ce_id)
                    self.position["PE"] = None


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
        }

    def reset_subscription(self):
        """
        Reset subscription status (useful for testing or restarting)
        """
        self.subscribed = False
        self.last_ce_ltp = None
        self.last_pe_ltp = None
        print("[Strategy] Subscription reset")


# Usage example
if __name__ == "__main__":
    # Create strategy instance
    strategy = NiftyATMStrategy(
        expiry_date="2025-08-21",
        quantity=75
    )
    
    # Print initial status
    print(f"[Strategy] Initial status: {strategy.get_status()}")
    
    # Start the strategy
    strategy.run_strategy()
