# %%
from pandas_ta import cross, sma, rsi, above_value, above, below, above_value, below_value
import random
import pandas as pd


def fixed_cross(series_a, series_b, above=True, asint=True, offset=None, **kwargs):
    results = cross(
        series_a, series_b, above=above, asint=asint, offset=offset, **kwargs
    )
    x = 0
    if not asint:
        x = False
    results.loc[pd.isna(series_a)] = x
    results.loc[pd.isna(series_b)] = x

    return results


def test_fixed_cross():
    randint = random.Random(20230119).randint
    series1 = pd.Series([randint(0, 100) for _ in range(120)])
    series1_sma = sma(series1, length=55)
    print(pd.isna(series1_sma))
    result = fixed_cross(series1, series1_sma, above=False)
    # print(result)


def enhanced_signals(series_a: pd.Series, series_b: pd.Series, windows=8, **kwargs):
    """
    将两个信号叠加成一个更强的信号，针对信号前后出现问题，有一个windows参数，只要在windows内同时出现两个同向信号，则输出增加信号
    所有信号都只有三个值, 1, 0, -1, 代表 买，无信号，卖

    series_a series_b is signals with value 1 -1 or 0,
    0 means no signal
    1 means buy signal
    -1 means sell signal
    when there are tow same signals in a windows, then the the output signal is triggered

    说明: 
        只能用在两个点状信号， 比如 ma的cross
        不能用在持续信号,  特殊的如果两个都是持续信号, 可以设置 windows=1
    """
    def find_latest_nonzero(s):
        n = s[s != 0]
        if n.empty:
            return 0
        else:
            return n.iloc[-1]

    if windows == 1:
        win_a = series_a
        win_b = series_b
    else:
        win_a = series_a.rolling(windows).apply(find_latest_nonzero).fillna(0)
        win_b = series_b.rolling(windows).apply(find_latest_nonzero).fillna(0)
    enhanced1 = series_a * win_b
    enhanced2 = series_b * win_a
    enhanced = pd.Series(0, index=series_a.index)
    enhanced.loc[enhanced1 > 0 ] = series_a[enhanced1 > 0 ]
    enhanced.loc[enhanced2 > 0 ] = series_b[enhanced2 > 0 ]

    return enhanced

def test_enhanced_signal():
    from ta.fake_ohlcv import get_fake_ohlcv
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    ohlcv = get_fake_ohlcv(120)
    series1 = ohlcv.close
    print(series1)
    series1_sma = sma(series1, length=55)
    series1_sma_signal = above(series1, series1_sma+10) + below(series1, series1_sma-10) * -1
    series1_rsi = rsi(series1, length=21)
    series1_rsi_signal = above_value(series1_rsi, 55) + below_value(series1_rsi, 45) * -1
    enhanced = enhanced_signals(series1_sma_signal, series1_rsi_signal, windows=3)
    print(pd.DataFrame({"sma": series1_sma_signal, "rsi": series1_rsi_signal, "enhanced": enhanced}))

if __name__ == "__main__":
    test_enhanced_signal()

# %%
