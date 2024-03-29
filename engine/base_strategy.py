import pandas as pd
from engine.base_structs import SymbolInfo, KlineTick

class BaseStrategy:
    def __init__(self):
        self.engine = None
        # 是否自动更新历史数据
        self.auto_update_hist = True
    
    @property
    def symbol(self):
        return self.engine.opts.symbol

    @property
    def symbol_info(self) -> SymbolInfo:
        return self.engine.symbol_info
    
    @property
    def opts(self):
        return self.engine.opts
    
    @property
    def hist(self)->pd.DataFrame:
        return self.engine._hist
    
    def is_last_hist_kline_closed(self):
        return self.engine.is_last_hist_kline_closed()
    
    def hist_need_update(self):
        """
        if self.auto_update_hist:
            # 是否更新由引擎决定
            need_update = self.engine.hist_need_auto_update()
        else:
            # 告知引擎，需要更新历史数据
            need_update = self.hist_need_update()
        """
        return False

    def pre_init(self):
        pass
    def post_init(self):
        pass

    def pre_open_order(self, order):
        pass

    def post_open_order(self, order):
        pass

    def on_tick(self, tick: KlineTick):
        pass

    def pre_update_hist(self):
        pass

    def on_update_hist(self):
        pass
    
    def post_update_hist(self):
        pass

    def post_update_hist(self):
        pass

    def on_process_timeout(self, routine_name, e):
        """
        当消息处理超时时，回调用此函数
        """
        raise e

    def on_tick_latency(self, contents):
        """
        当上一次消息处理还未完成， 新消息到达时，回调此函数, 用于处理消息堆积
        该函数应该尽量简单，不要有耗时操作
        """
        # print("message latency", contents)

class SimpleStrategy(BaseStrategy):
    def on_tick(self, tick):
        print(tick)