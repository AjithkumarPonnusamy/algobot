from multiprocessing import Process
from src.utils.base import run_feed
from src.strategies.niftyBEP import run_strategy

if __name__ == "__main__":
    Process(target=run_feed).start()
    Process(target=run_strategy).start()

