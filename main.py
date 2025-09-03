import threading
from datetime import datetime,time

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
# import threading
# import time
# from datetime import datetime
# from src.utils.base import DhanFeedHandler
# from src.strategies.nifty_atm import NiftyATMStrategy
# from src.connections.connectDB import run_db_worker

# running_threads = []

# def start_trading():
#     """Start all worker threads"""
#     feed = DhanFeedHandler()
#     atm_strategy = NiftyATMStrategy(feed)

#     t1 = threading.Thread(target=feed.run_feed, daemon=True)
#     t2 = threading.Thread(target=atm_strategy.run_strategy, daemon=True)
#     t3 = threading.Thread(target=run_db_worker, daemon=True)

#     t1.start(); t2.start(); t3.start()

#     running_threads.extend([t1, t2, t3])
#     print("✅ Trading system started")

# def stop_trading():
#     """Stop trading gracefully"""
#     global running_threads
#     running_threads = []   # threads are daemons, will auto-exit when main exits
#     print("⏹ Trading system stopped")

# def scheduler():
#     """Auto start/stop between 9:15 and 3:15"""
#     start_time = datetime.strptime("09:15", "%H:%M").time()
#     end_time = datetime.strptime("15:15", "%H:%M").time()
#     started = False

#     while True:
#         now = datetime.now().time()
#         print("Waiting...")
        
#         if start_time <= now <= end_time:
#             if not started:
#                 start_trading()
#                 started = True
#         else:
#             if started:
#                 print("executed...")
#                 stop_trading()
#                 started = False


#         time.sleep(30)  # check every 30 sec


# if __name__ == "__main__":
#     scheduler()
