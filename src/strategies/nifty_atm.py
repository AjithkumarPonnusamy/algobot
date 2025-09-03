import json
from datetime import datetime
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.indicators.bep import bep, round_to_50
from src.dataaggregators.strikeFinder import strike_value
from src.connections.cache import r
from src.connections.connectTel import send_telegram_message

class NiftyATMStrategy():
    def __init__(self, feed, quantity=150, underlying_symbol="13"):
        """
        Initialize the Options Strategy
        """
        self.feed = feed
        self.quantity = quantity
        self.underlying_symbol = underlying_symbol  # security ID for underlying
        self.strategy_id = "ST002"

        # State
        # self.under = None
        self.under = 24550
        self.subscribed = False

        # Strike IDs
        self.atm_ce_id = self.atm_pe_id = self.atm_ce_id_bep = self.atm_pe_id_bep = None

        # LTPs
        self.atm_ce_ltp = self.atm_pe_ltp = self.atm_ce_strike_ltp = None

        # BEPs
        self.atm_bep = None

        # store entry price if in trade
        self.position = {
            "CE": None,
            "PE": None
        }  

        # OHLC Builders
        self.nifty_5 = OHLCBuilder("nifty",interval_minutes=5)
        self.atm_ce_1 = OHLCBuilder("atm_ce",interval_minutes=1)
        self.atm_ce_3 = OHLCBuilder("atm_ce",interval_minutes=3)
        self.atm_pe_1 = OHLCBuilder("atm_pe",interval_minutes=1)
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
            msg = f"✅ {side.upper()} {order_type.upper()} order placed: {order_response} at {price}| Qty: {qty}"
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
       
        if candle and self.under == None:
            close_price = candle.get("close")
            if close_price:
                self.under = round_to_50(int(close_price))
                print(f"[Strategy] Underlying updated for {self.strategy_id} → {self.under}")
                


    def subscribe_options(self):
        """Subscribe to ATM & OTM option strikes once underlying is known"""
        if self.under and not self.subscribed:
            try:
                atm = self.under 
                ce_atm_val, pe_atm_val = atm - 50, atm 
                self.atm_ce_id_bep, self.atm_pe_id_bep = strike_value(ce_atm_val, pe_atm_val, self.feed.expiry_date)
                print(f"[Strategy] ATM → CE bep: {self.atm_ce_id_bep}, PE bep: {self.atm_pe_id_bep}")
                ce_atm_val,pe_atm_val = atm, atm
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

        if sec_id == self.atm_ce_id_bep:
            self.atm_ce_ltp = ltp
            # print(self.atm_ce_1_ohlc['close'])
        elif sec_id == self.atm_pe_id_bep:
            self.atm_pe_ltp = ltp
            self.atm_pe_1.add_tick(ltp)
            self.atm_pe_3.add_tick(ltp)
        elif sec_id == self.atm_ce_id:
            self.atm_ce_strike_ltp = ltp
            self.atm_ce_1.add_tick(ltp)
            self.atm_ce_3.add_tick(ltp)
        # elif sec_id == self.atm_pe_id:
        #     self.atm_pe_1.add_tick(ltp)
        #     self.atm_pe_3.add_tick(ltp)
        #     print(f"Adding ticks : {self.atm_pe_1}")

        if self.atm_ce_ltp and self.atm_pe_ltp:
            self.atm_bep = bep(self.atm_ce_ltp, self.atm_pe_ltp)
        #     print(self.atm_ce_ltp)

    def serialize_candle(self,candle):
        """Convert datetime inside candle to string for JSON"""
        safe_candle = candle.copy()
        if isinstance(safe_candle.get("time"), datetime):
            safe_candle["time"] = safe_candle["time"].isoformat()
        return safe_candle

    def save_OHLC(self):
        self.nifty_5_ohlc = self.nifty_5.get_last_candle()
        self.atm_ce_1_ohlc = self.atm_ce_1.get_last_candle()
        self.atm_ce_3_ohlc = self.atm_ce_3.get_last_candle()
        self.atm_pe_1_ohlc = self.atm_pe_1.get_last_candle()
        self.atm_pe_3_ohlc = self.atm_pe_3.get_last_candle()
        if self.nifty_5_ohlc is not None:
            candle_time = self.nifty_5_ohlc['time']
            if candle_time != self.nifty_5_lct:
                data = {
                    "strategy_id":self.strategy_id,
                    "symbol": "nifty_5m",
                    "candle": self.serialize_candle(self.nifty_5_ohlc)
                }
                r.publish("ohlc_channel", json.dumps(data))
                self.nifty_5_lct = candle_time
        
        if self.atm_ce_1_ohlc is not None:
            candle_time = self.atm_ce_1_ohlc['time']
            if candle_time != self.atm_ce_1_lct:
               data = {
                   "strategy_id":self.strategy_id,
                    "symbol": "atm_ce_1m",
                    "candle": self.serialize_candle(self.atm_ce_1_ohlc)
                }
               r.publish("ohlc_channel", json.dumps(data))
               self.atm_ce_1_lct = candle_time
        
        if self.atm_pe_1_ohlc is not None:
            candle_time = self.atm_pe_1_ohlc['time']
            if candle_time != self.atm_pe_1_lct:
                data = {
                    "strategy_id":self.strategy_id,
                    "symbol": "atm_pe_1m",
                    "candle": self.serialize_candle(self.atm_pe_1_ohlc)
                }
                r.publish("ohlc_channel", json.dumps(data))
                self.atm_pe_1_lct = candle_time
    
    def execute_strategy_logic(self):
        if self.atm_ce_1_ohlc is not None:
           
            ce_close = self.atm_ce_1_ohlc['close']
            ce_low = self.atm_ce_1_ohlc['low']
            ce_high = self.atm_ce_1_ohlc['high']
            ce_final = self.atm_ce_1_ohlc['final']
            ce_ltp = self.atm_ce_strike_ltp
             # Entry condition
            if ce_low <= self.atm_bep and ce_close > self.atm_bep and self.position["CE"] is None:
                self.place_order(price=ce_close,order_type="Limit",side="Buy",security_id=self.atm_ce_id)
                self.position["CE"] = {
                    "strategy_id" : self.strategy_id,
                    "entry": ce_close,
                    "target1": ce_close + 15,
                    "target2": ce_close + 30,
                    "hit_t1": False,
                    "quantity": self.quantity
                }
                r.publish("strategy_exec", json.dumps(self.position["CE"]))
                print(f"[STRATEGY] Entered CE at {ce_close}")

            # Target checks
            elif self.position["CE"] is not None:
                entry_data = self.position["CE"]
                
                # First Target
                if not entry_data["hit_t1"] and ce_ltp >= entry_data["target1"]:
                    sell_qty = entry_data["quantity"] / 2
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 1 at {ce_ltp} (+15) → Sell {sell_qty}")
                        self.place_order(
                            price=ce_ltp,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_ce_id,
                            quantity=sell_qty
                        )
                        entry_data["quantity"] -= sell_qty
                    entry_data["hit_t1"] = True

                # Second Target -> Exit
                if ce_ltp >= entry_data["target2"]:
                    sell_qty = entry_data["quantity"]
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 2 at {ce_ltp} (+30) → Exit {sell_qty}")
                        self.place_order(
                            price=ce_ltp,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_ce_id,
                            quantity=sell_qty
                        )
                    self.position["CE"] = None

                # ✅ Exit condition
                if entry_data["quantity"] > 0:
                    exit_reason = None
                    exit_price = None
                    order_type = None

                    # 🔹 1. Stoploss check → only on finalized candle
                    if self.atm_ce_1_ohlc and ce_final:
                        ce_close = self.atm_ce_1_ohlc["close"]
                        ce_high = self.atm_ce_1_ohlc["high"]

                        if ce_close < self.atm_bep and ce_high > self.atm_bep:
                            exit_price = ce_close
                            order_type = "Market"  # force exit
                            exit_reason = f"[STOPLOSS] CE breached BEP {self.atm_bep} → Exit {sell_qty} @ {ce_close}"

                    # 🔹 2. T1 reversal check → works live (tick-based)
                    if exit_reason is None and entry_data["hit_t1"] and ce_ltp <= entry_data["entry"]:
                        exit_price = entry_data["entry"]
                        order_type = "Limit"
                        exit_reason = f"[REVERSAL] CE reversed after T1 → Exit {sell_qty} @ {exit_price}"

                    # 🔹 Execute exit if any condition is triggered
                    if exit_reason:
                        sell_qty = entry_data["quantity"]
                        print(exit_reason)
                        send_telegram_message(exit_reason)

                        self.place_order(
                            price=exit_price,
                            order_type=order_type,
                            side="Sell",
                            security_id=self.atm_ce_id,
                            quantity=sell_qty
                        )

                        self.position["CE"] = None

                #  # Exit condition - falls below BEP
                # if (ce_close < self.atm_bep and ce_high > self.atm_bep) or (entry_data["hit_t1"] and self.atm_ce_strike_ltp <=  entry_data["entry"]):
                #     sell_qty = entry_data["quantity"]
                #     if sell_qty > 0:
                #         # ✅ Decide exit type and price
                #         if ce_close < self.atm_bep and ce_high > self.atm_bep:
                #             exit_price = ce_close
                #             order_type = "Market"   # Stoploss → use market for sure exit
                #         else:
                #             exit_price = entry_data["entry"]
                #             order_type = "Limit"    # T1 reversal → use limit at entry price
                #         print(f"[STOPLOSS] CE hit Stop Loss at {ce_close} → Exit {sell_qty}")
                #         send_telegram_message(f"[STOPLOSS] CE hit Stop Loss at {ce_close} → Exit {sell_qty}")
                #         self.place_order(
                #         price=exit_price,
                #         order_type=order_type,   # better for stop loss exit
                #         side="Sell",
                #         security_id=self.atm_ce_id,
                #         quantity=sell_qty
                #         )
                #     self.position["CE"] = None

        # ✅ PE Logic
        if self.atm_pe_1_ohlc is not None:
            pe_close = self.atm_pe_1_ohlc['close']
            pe_low = self.atm_pe_1_ohlc['low']
            pe_high = self.atm_pe_1_ohlc['high']
            # Entry condition
            if pe_close > self.atm_bep and pe_low <= self.atm_bep and self.position["PE"] is None:
                self.place_order(price=pe_close,order_type="Limit",side="Buy",security_id=self.atm_pe_id)
                self.position["PE"] = {
                    "strategy_id" : self.strategy_id,
                    "entry": pe_close,
                    "target1": pe_close + 15,
                    "target2": pe_close + 30,
                    "hit_t1": False,
                    "quantity": self.quantity
                }
                r.publish("strategy_exec", json.dumps(self.position["PE"]))
                print(f"[STRATEGY] Entered PE at {pe_close}")

            

            # Target checks
            elif self.position["PE"] is not None:
                entry_data = self.position["PE"]

                # First Target
                if not entry_data["hit_t1"] and pe_close >= entry_data["target1"]:
                    sell_qty = entry_data["quantity"] / 2
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 1 at {pe_close} (+15) → Sell {sell_qty}")
                        self.place_order(
                            price=pe_close,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_pe_id,
                            quantity=sell_qty
                        )
                        entry_data["quantity"] -= sell_qty
                    entry_data["hit_t1"] = True

               # Second Target -> Exit
                if pe_close >= entry_data["target2"]:
                    sell_qty = entry_data["quantity"]
                    if sell_qty > 0:
                        print(f"[TARGET] CE hit Target 2 at {pe_close} (+30) → Exit {sell_qty}")
                        self.place_order(
                            price=pe_close,
                            order_type="Limit",
                            side="Sell",
                            security_id=self.atm_pe_id,
                            quantity=sell_qty
                        )
                    self.position["PE"] = None

                 # Exit condition - falls below BEP
                if pe_close < self.atm_bep and pe_high > self.atm_bep:
                    sell_qty = entry_data["quantity"]
                    if sell_qty > 0:
                        print(f"[STOPLOSS] PE hit Stop Loss at {pe_close} → Exit {sell_qty}")
                        send_telegram_message(f"[STOPLOSS] PE hit Stop Loss at {pe_close} → Exit {sell_qty}")
                        self.place_order(
                        price=pe_close,
                        order_type="Market",   # better for stop loss exit
                        side="Sell",
                        security_id=self.atm_pe_id,
                        quantity=sell_qty
                        )
                    self.position["PE"] = None

    def process_tick(self, sec_id, ltp, ltt):
        """Main dispatcher for ticks"""
        # print(f"{sec_id} : {ltp}")
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
