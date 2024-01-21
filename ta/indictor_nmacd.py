# %%
from pandas_ta import sma, ema, wma, cross
from ta.algo import fixed_cross
import numpy as np
import pandas as pd
from random import Random

nmacd_ma_type_map = {
    "ema": ema,
    "wma": wma,
    "sma": sma,
}


def nmacd_signals(
    series: pd.Series,
    fast: int = 12,
    slow: int = 21,
    signal: int = 9,
    normalize: int = 50,
    ma_type: str = "ema",
    **kwargs
) -> pd.Series:
    """normalized MACD Signal Line
    算法为 tradingview 的 NMACD , 作者: glaz

    pine:
        study("Normalized MACD",shorttitle='N MACD')
        sma = input(12,title='Fast MA')
        lma = input(21,title='Slow MA')
        tsp = input(9,title='Trigger')
        np = input(50,title='Normalize')
        h=input(true,title='Histogram')
        docol = input(false,title="Color Change")
        dofill=input(false,title="Fill")
        type = input(1,minval=1,maxval=3,title="1=Ema, 2=Wma, 3=Sma")

        sh = type == 1 ? ema(close,sma)
         : type == 2 ? wma(close, sma)
         : sma(close, sma)

        lon=type == 1 ? ema(close,lma)
         : type == 2 ? wma(close, lma)
         : sma(close, lma)

        ratio = min(sh,lon)/max(sh,lon)
        Mac = (iff(sh>lon,2-ratio,ratio)-1)
        MacNorm = ((Mac-lowest(Mac, np)) /(highest(Mac, np)-lowest(Mac, np)+.000001)*2)- 1
        MacNorm2 = iff(np<2,Mac,MacNorm)
        Trigger = wma(MacNorm2, tsp)
        Hist = (MacNorm2-Trigger)
        Hist2 = Hist>1?1:Hist<-1?-1:Hist
        swap=Hist2>Hist2[1]?green:red
        swap2 = docol ? MacNorm2 > MacNorm2[1] ? #0094FF : #FF006E : red
        plot(h?Hist2:na,color=swap,style=columns,title='Hist',histbase=0)
        plot(MacNorm2,color=swap2,title='MacNorm')
        plot(dofill?MacNorm2:na,color=MacNorm2>0?green:red,style=columns)
        plot(Trigger,color=yellow,title='Trigger')
        hline(0)
    """
    fast_ma = nmacd_ma_type_map[ma_type](series, length=fast)
    slow_ma = nmacd_ma_type_map[ma_type](series, length=slow)

    ratios = np.minimum(fast_ma, slow_ma) / np.maximum(fast_ma, slow_ma)
    # mac代表快线与慢线的比值, 0-1之间， 正值表示快线大于慢线，负值表示快线小于慢线
    mac = pd.Series(np.where(fast_ma > slow_ma, 2 - ratios, ratios) - 1, index=series.index)
    mac_rolling_min = mac.rolling(normalize).min()
    mac_rolling_max = mac.rolling(normalize).max()

    mac_norm = (
        (mac - mac_rolling_min) / (mac_rolling_max - mac_rolling_min + 0.0000001) * 2
    ) - 1

    # 二选一
    mac_norm2 = mac if normalize < 2 else mac_norm
    trigger = wma(mac_norm2, length=signal)
    hist = mac_norm2 - trigger
    hist2 = pd.Series(np.where(hist > 1, 1, np.where(hist < -1, -1, hist)), index=series.index)
    signal = cross(mac_norm2, trigger, above=True) +  fixed_cross(mac_norm2, trigger, above=False) * -1
    df = pd.DataFrame(index=series.index, columns=["mac", "hist", "mac_norm", "trigger", "signal"])
    df["mac"] = mac
    df["hist"] = hist2
    df["mac_norm"] = mac_norm2
    df["trigger"] = trigger
    df["signal"] = signal

    return df


def test_nmacd_signals():
    # random pandas dataframe with seed 20230119
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    randint = Random(20230119).randint
    series1 = pd.Series([randint(0, 100) for _ in range(120)])
    signals = nmacd_signals(series1, fast=12, slow=21, signal=9, normalize=50, ma_type="ema")
    print(signals)
    observed = signals.iloc[116].reset_index(drop=True).squeeze()[:4]
    expect = pd.Series([0.044699,  0.151160,  0.750026,  0.598865])
    assert pd.Series.equals(expect.round(3), observed.round(3))



# %%
if __name__ == "__main__":
    test_nmacd_signals()
    
# %%
