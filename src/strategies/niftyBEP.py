import json
import redis
from datetime import datetime
from dhanhq import marketfeed
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.indicators.bep import bep, round_to_50
from src.dataaggregators.strikeFinder import strike_value
from src.connections.cache import r
from src.connections.connectTel import send_telegram_message
from src.utils.base import DhanFeedHandler


class OptionsStrategy():
    def __init__(self,feed, base_strike=25000, expiry_date="2025-08-21", quantity=75):
        """
        Initialize the Options Strategy
        
        Args:
            base_strike (int): Base strike price
            expiry_date (str): Options expiry date
            quantity (int): Order quantity
        """
        self.feed = feed
        # Configuration
        self.base_strike = base_strike
        self.expiry_date = expiry_date
        self.quantity = quantity
        
        # State variables
        self.otm_ce_id = None
        self.otm_pe_id = None
        self.last_ce_ltp = None
        self.last_pe_ltp = None
        self.under = base_strike
        self.subscribed = False
        
        # OHLC builders
        self.ohlc_builders = {}
        
        # Redis pubsub
        self.pubsub = r.pubsub()
        
        # Initialize OTM strikes
        if self.under is not None:
            self.otm = self.under + 100
    
    def add_symbol(self, symbol):
        """
        Add a new symbol dynamically while strategy is running.
        """
        if symbol in self.ohlc_builders:
            print(f"[Strategy] Symbol {symbol} already exists.")
            return
        
        self.ohlc_builders[symbol] = {}
        for tf in self.timeframes:
            self.ohlc_builders[symbol][tf] = OHLCBuilder(symbol, interval_minutes=tf, db_conn=self.db_conn)
        print(f"[Strategy] Added new symbol: {symbol} with timeframes {self.timeframes}m")

    def place_order(self, security_id):
        """
        Place market order for given security ID
        
        Args:
            security_id (str): Security ID to place order for
            
        Returns:
            dict: Order response
        """
        try:
            order_response = self.feed.dhan.place_order(
                security_id=str(security_id),          
                exchange_segment=self.feed.dhan.NSE_FNO,
                transaction_type=self.feed.dhan.BUY,
                quantity=self.quantity,
                order_type=self.feed.dhan.MARKET,
                product_type=self.feed.dhan.INTRA,
                price=0
            )
            
            message = f"Order placed at {order_response}"
            send_telegram_message(message)
            print(f"[Order] {message}")
            return order_response
            
        except Exception as e:
            error_msg = f"Error placing order for {security_id}: {str(e)}"
            print(f"[Order Error] {error_msg}")
            send_telegram_message(error_msg)
            return None
    
    def assign_underlying(self, first_candle):
        """
        Assign underlying price based on candle close
        
        Args:
            first_candle (dict): First candle data with 'close' key
        """
        if first_candle is not None:
            close_price = first_candle.get('close')
            if close_price:
                self.under = round_to_50(int(close_price))
                print(f"[Strategy] Updated underlying to: {self.under}")
    
    def subscribe_options(self):
        """
        Subscribe to option strikes based on current underlying
        """
        if self.under is not None and not self.subscribed:
            try:
                strike_values = strike_value(self.under + 100, self.expiry_date)
                self.otm_ce_id, self.otm_pe_id = strike_values
                
                print(f"[Strategy] CE ID: {self.otm_ce_id} || PE ID: {self.otm_pe_id}")
                
                # Publish subscription request if needed
                # r.publish("subscribe_queue", json.dumps([self.otm_ce_id, self.otm_pe_id]))
                
                self.subscribed = True
                print(f"[Strategy] Subscribed to CE: {self.otm_ce_id}, PE: {self.otm_pe_id}")
                
            except Exception as e:
                print(f"[Strategy Error] Failed to subscribe options: {str(e)}")
    
    def process_underlying_tick(self, sec_id, ltp, ltt):
        """
        Process tick data for underlying (Nifty)
        
        Args:
            sec_id (str): Security ID
            ltp (float): Last traded price
            ltt (str): Last trade time
        """
        if sec_id == '13' and ltp is not None:
            # Add tick to 5-minute candle
            self.candle5.add_tick(ltp)
            last_candle = self.candle5.get_first_candle()
            
            if last_candle:
                self.assign_underlying(first_candle=last_candle)
                # print(f"[Strategy] Current 5-min candle: {last_candle}")
    
    def process_options_tick(self, sec_id, ltp, ltt):
        """
        Process tick data for options
        
        Args:
            sec_id (str): Security ID
            ltp (float): Last traded price
            ltt (str): Last trade time
        """
        print(f"[Strategy] Options tick for {sec_id}: {ltp} at {ltt}")
        
        # Update option LTPs
        if self.otm_ce_id == sec_id and ltp is not None:
            self.last_ce_ltp = ltp
            print(f"[Strategy] CE LTP updated: {ltp}")
            
        elif self.otm_pe_id == sec_id and ltp is not None:
            self.last_pe_ltp = ltp
            print(f"[Strategy] PE LTP updated: {ltp}")
        
        # Calculate BEP when both option prices are available
        if self.last_ce_ltp is not None and self.last_pe_ltp is not None:
            breakeven_price = bep(ce_strike=self.last_ce_ltp, pe_strike=self.last_pe_ltp)
            self.place_order(security_id=sec_id)
            print(f"[Strategy] Breakeven Price: {breakeven_price}")
            
            # Add your strategy logic here
            # self.execute_strategy_logic(breakeven_price)
    
    def execute_strategy_logic(self, breakeven_price):
        """
        Execute main strategy logic based on breakeven price
        
        Args:
            breakeven_price (float): Calculated breakeven price
        """
        # Implement your strategy logic here
        # Example: Place orders based on conditions
        pass
    
    def process_tick(self, sec_id, ltp, ltt):
        """
        Main tick processing method
        
        Args:
            sec_id (str): Security ID
            ltp (float): Last traded price
            ltt (str): Last trade time
        """
        # Process underlying tick
        self.process_underlying_tick(sec_id, ltp, ltt)
        
        # Subscribe to options if not already done
        self.subscribe_options()
        
        # Process options tick
        self.process_options_tick(sec_id, ltp, ltt)
    
    def run_strategy(self):
        """
        Main method to run the strategy
        """
        print("[Strategy] Starting options strategy...")
        print(f"[Strategy] Base strike: {self.base_strike}, Expiry: {self.expiry_date}")
        
        self.pubsub.subscribe("ticks")
        print("[Strategy] Subscribed to live ticks from Redis...")
        
        try:
            for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        sec_id = data["sec_id"]
                        ltp = data["ltp"]
                        ltt = data["ltt"]
                        
                        self.process_tick(sec_id, ltp, ltt)
                        
                    except json.JSONDecodeError as e:
                        print(f"[Strategy Error] Bad JSON message: {message['data']}")
                    except KeyError as e:
                        print(f"[Strategy Error] Missing key in message: {e}")
                    except Exception as e:
                        print(f"[Strategy Error] Unexpected error: {str(e)}")
                        
        except KeyboardInterrupt:
            print("[Strategy] Strategy stopped by user")
        except Exception as e:
            print(f"[Strategy Error] Fatal error: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        Cleanup resources when stopping the strategy
        """
        try:
            self.pubsub.unsubscribe("ticks")
            self.pubsub.close()
            print("[Strategy] Cleanup completed")
        except Exception as e:
            print(f"[Strategy Error] Error during cleanup: {str(e)}")
    
    def get_status(self):
        """
        Get current strategy status
        
        Returns:
            dict: Current strategy status
        """
        return {
            "underlying": self.under,
            "subscribed": self.subscribed,
            "otm_ce_id": self.otm_ce_id,
            "otm_pe_id": self.otm_pe_id,
            "last_ce_ltp": self.last_ce_ltp,
            "last_pe_ltp": self.last_pe_ltp,
            "base_strike": self.base_strike,
            "expiry_date": self.expiry_date
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
    strategy = OptionsStrategy(
        base_strike=25000,
        expiry_date="2025-08-21",
        quantity=75
    )
    
    # Print initial status
    print(f"[Strategy] Initial status: {strategy.get_status()}")
    
    # Start the strategy
    strategy.run_strategy()
