import asyncio
from engine.base_strategy import BaseStrategy
from engine.binance_engine import BinanceFutureEngine, BinanceOptions
from ta.indictor_nmacd import nmacd_signals
from ta.indictor_rsi_cross import rsi_cross_signals
from ta.algo import enhanced_signals
import pandas as pd


class NmacdRsiStrategy(BaseStrategy):
    async def on_tick(self, tick):
        print("---- tick -----", tick)
        # TODO: do not update here
        self.update_indicators()
        await asyncio.sleep(2)

    def update_indicators(self):
        nmacd_cross = nmacd_signals(self.hist["c"], fast=13, slow=21, signal=9, normalize=50)
        rsi_cross = rsi_cross_signals(self.hist["c"], rsi_length=21, sma_length=55)
        self.enhanced = enhanced_signals(nmacd_cross["signal"], rsi_cross["signal"], windows=8)
        df = pd.merge(nmacd_cross, rsi_cross, left_index=True, right_index=True)
        df["enhanced"] = self.enhanced
        df.to_csv("tmp_signal_cross_%s.csv" % self.engine.opts.symbol)

    def post_update_hist(self):
        self.update_indicators()


def main():
    strategy = NmacdRsiStrategy()
    strategy.auto_update_hist = True
    engine = BinanceFutureEngine(
        NmacdRsiStrategy(),
        opts=BinanceOptions(
            symbol="ETHUSDT",
            proxy_url="http://127.0.0.1:7890",
            hist_interval="1h", 
            hist_start_str="20 day ago UTC",
        ),
    )
    asyncio.run(engine.run())


if __name__ == "__main__":
    main()
