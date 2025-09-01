import threading
from src.utils.base import DhanFeedHandler
from src.strategies.nifty_otm import NiftyOTMStrategy
from src.strategies.nifty_atm import NiftyATMStrategy
from src.connections.connectDB import run_db_worker

if __name__ == "__main__":
    feed = DhanFeedHandler()
    # otm_strategy = NiftyOTMStrategy(feed)
    atm_strategy = NiftyATMStrategy(feed)

    t1 = threading.Thread(target=feed.run_feed, daemon=True)
    # t2 = threading.Thread(target=otm_strategy.run_strategy, daemon=True)
    t3 = threading.Thread(target=atm_strategy.run_strategy, daemon=True)
    t4 = threading.Thread(target=run_db_worker,daemon=True)
    t1.start()
    # t2.start()
    t3.start()
    t4.start()
    
    # Keep main thread alive
    t1.join()    
    # t2.join()
    t3.join()
    t4.join()

