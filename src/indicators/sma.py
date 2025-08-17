from talib import SMA
import numpy as np
from talib.abstract import *

inputs = [
        3879.85,3915.9,3859.9,3897.9,3968.15,4019.15,3990.6,3914.65,3826.55,3833.5,3771.35,
        3769.9,3649.25,3690.05,3736.25,3800.65,3856.2,3824.6,3814.9,3779
        ]
inputs_array = np.array(inputs)
# uses close prices (default)
output = SMA(inputs_array, timeperiod=5)

print(output)

# smaLength = 20
# smaLine = ta.sma(close, smaLength)
# plot(smaLine, color=color.blue, title="20 SMA")

# import pandas as pd
# data['SMA_20'] = data['Close'].rolling(window=20).mean()

def sma():
    pass
