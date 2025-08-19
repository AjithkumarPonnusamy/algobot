import threading
from src.utils.base import DhanFeedHandler
from src.strategies.niftyBEP import OptionsStrategy

if __name__ == "__main__":
    feed = DhanFeedHandler()
    strategy = OptionsStrategy(feed)

    t1 = threading.Thread(target=feed.run_feed, daemon=True)
    t2 = threading.Thread(target=strategy.run_strategy, daemon=True)

    t1.start()
    t2.start()

    # Keep main thread alive
    t1.join()
    t2.join()
