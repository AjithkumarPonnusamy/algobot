import json
import redis
from dhanhq import marketfeed
from dhanhq import dhanhq
from src.dataaggregators.candleAggregator import OHLCBuilder
from src.dataaggregators.strikeFinder import get_strikes
import os
from dotenv import load_dotenv
from src.connections.cache import r

class DhanFeedHandler:
    def __init__(self, expiry_date="2025-09-09", strike_price=24900, interval_minutes=5):
        """
        Initialize the Dhan Feed Handler
        
        Args:
            expiry_date (str): Expiry date for options strikes
            strike_price (int): Strike price for options
            interval_minutes (int): Candle interval in minutes
        """
        load_dotenv(".env")
        self.expiry_date = expiry_date
        # Redis setup
        self.pubsub = r.pubsub()
        self.pubsub.subscribe("subscribe_queue")
        
        # Dhan credentials
        self.client_id = os.getenv("CLIENT_ID")
        self.access_token = os.getenv("ACCESS_TOKEN")
        
        # Initialize Dhan client
        self.dhan = dhanhq(self.client_id, self.access_token)
        
        # Get option strikes
        self.nse_fno_ids = get_strikes(self.expiry_date, strike_price)
        
        # Setup instruments
        self.instruments = self._setup_instruments()
        
        # Initialize OHLC builder
        self.nifty = OHLCBuilder("Nifty", interval_minutes=interval_minutes)
        self.first_candle = self.nifty.get_first_candle()
        self.last_candle = self.nifty.get_last_candle()
        
        # Initialize market feed
        self.version = "v2"
        self.data = marketfeed.DhanFeed(
            self.client_id, 
            self.access_token, 
            self.instruments, 
            self.version
        )
    
    def _setup_instruments(self):
        """
        Setup the instruments list for market feed
        
        Returns:
            list: List of instruments tuples
        """
        instruments = [
            (marketfeed.IDX, "13", marketfeed.Ticker),
            (marketfeed.NSE_FNO, "47252", marketfeed.Ticker),
            (marketfeed.NSE_FNO, "47253", marketfeed.Ticker)
        ]
        
        # Add option strikes to instruments
        for sid in self.nse_fno_ids:
            instruments.append((marketfeed.NSE_FNO, str(sid), marketfeed.Ticker))
        
        return instruments
    
    def process_tick_data(self, res):
        """
        Process incoming tick data and publish to Redis
        
        Args:
            res (dict): Raw tick data from Dhan feed
        """
        if res and res.get("LTP"):
            tick_data = {
                "sec_id": str(res["security_id"]),
                "ltp": float(res["LTP"]),
                "ltt": str(res["LTT"])
            }
            
            # Save candle data to database
            self.nifty.save_to_db(self.last_candle)
            
            # Publish tick data to Redis
            r.publish("ticks", json.dumps(tick_data))
    
    def run_feed(self):
        """
        Main method to run the market data feed
        """
        print("[Feed] Starting Dhan feed...")
        
        try:
            while True:
                self.data.run_forever()
                res = self.data.get_data()
                self.process_tick_data(res)
                
        except KeyboardInterrupt:
            print("[Feed] Feed stopped by user")
        except Exception as e:
            print(f"[Feed] Error in feed: {str(e)}")
        # finally:
        #     self._cleanup()
    
    def _cleanup(self):
        """
        Cleanup resources when stopping the feed
        """
        try:
            self.pubsub.unsubscribe("subscribe_queue")
            self.pubsub.close()
            print("[Feed] Cleanup completed")
        except Exception as e:
            print(f"[Feed] Error during cleanup: {str(e)}")
    
    def get_instruments_count(self):
        """
        Get the total number of instruments being tracked
        
        Returns:
            int: Number of instruments
        """
        return len(self.instruments)
    
    def get_option_strikes_count(self):
        """
        Get the number of option strikes being tracked
        
        Returns:
            int: Number of option strikes
        """
        return len(self.nse_fno_ids)


# Usage example
if __name__ == "__main__":
    # Create feed handler instance
    feed_handler = DhanFeedHandler(
        expiry_date="2025-08-21",
        strike_price=24900,
        interval_minutes=5
    )
    
    # Print some info
    print(f"Total instruments: {feed_handler.get_instruments_count()}")
    print(f"Option strikes: {feed_handler.get_option_strikes_count()}")
    
    # Start the feed
    feed_handler.run_feed()
