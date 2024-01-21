# %%
import pandas as pd
import random
import numpy as np
from contextlib import contextmanager


@contextmanager
def np_seed(seed=None):
    if seed:
        rs = np.random.RandomState(np.random.MT19937(np.random.SeedSequence(seed)))
    else:
        rs = np.random.RandomState()
    savedState = rs.get_state()
    try:
        yield rs
    finally:
        # restore state
        rs.set_state(savedState)       # Reset the state

def positive_norm(randstate, max, length):
    ret = randstate.normal(0, 1, length)
    ret = np.where(ret > 5, 5, np.where(ret < -5, -5, ret))
    return (ret + 5) / 10 * max

def get_fake_ohlcv(length=120, max_volitility=0.3, base_point=100, *, seed=20230119):
    with np_seed(seed) as rs:
        # 每日振幅
        volitility_rates = positive_norm(rs, max_volitility, length)
        # 每日涨跌比例
        day_diff_rate = (rs.random(length) -0.5) * 2* volitility_rates
        # 最高最低比例(分配剩余振幅)
        split_rates = rs.random(length)
    # 汇总涨跌幅
    day_diff = day_diff_rate.cumsum() * base_point
    # 每日收盘价
    close = base_point + day_diff
    open = np.roll(close, 1)
    open[0] = base_point
    left_volitility = abs(close - open) / day_diff_rate
    high = np.maximum(open, close) + left_volitility * split_rates
    low = np.minimum(open, close) - left_volitility * (1 - split_rates)
    
    df = pd.DataFrame(
        {
            "time": pd.date_range("2021-01-01", periods=length, freq="1d"),
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": [random.randint(0, 100) for _ in range(length)],
        }
    )

    return df

# %%