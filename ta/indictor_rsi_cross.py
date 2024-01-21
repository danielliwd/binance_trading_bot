# %%
from pandas_ta import sma, ema, wma, rsi, cross, macd
from ta.algo import fixed_cross
import numpy as np
import pandas as pd
from random import Random



def rsi_cross_signals(
    series: pd.Series,
    rsi_length: int = 21,
    sma_length: int = 55,
    **kwargs
) -> pd.Series:
    rsi_series = rsi(series, length=rsi_length)
    rsi_sma = sma(rsi_series, length=sma_length)
    signal = cross(rsi_series, rsi_sma, above=True) +  fixed_cross(rsi_series, rsi_sma, above=False) * -1
    df = pd.DataFrame(index=series.index, columns=["rsi", "ma", "signal"])
    df["rsi"] = rsi_series
    df["ma"] = rsi_sma
    df["signal"] = signal

    return df


def test_rsi_cross_signals():
    # random pandas dataframe with seed 20230119
    randint = Random(20230119).randint
    series1 = pd.Series([randint(0, 100) for _ in range(120)])
    signals = rsi_cross_signals(series1)
    print(signals)



if __name__ == "__main__":
    test_rsi_cross_signals()
    
# %%
