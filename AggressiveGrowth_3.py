# region imports
from AlgorithmImports import *

class AggressiveGrowth(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2021, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(500)

        self.tickers = ["TSLA", "NVDA", "AMD", "PLTR", "MARA", "MLGO", "SQQQ", "TQQQ", "COIN"]
        self.symbols = [self.AddEquity(t, Resolution.Daily).Symbol for t in self.tickers]

        self.lookback = 5
        self.stop_loss = 0.05
        self.trailing_stop_pct = 0.08  # 动态止盈 / 止损回撤阈值
        self.take_profit = 0.10

        self.current_symbol = None
        self.entry_price = None
        self.max_price = None
        self.added_level_1 = False
        self.added_level_2 = False

        # 添加 TQQQ 用于情绪判断
        self.AddEquity("TQQQ", Resolution.Daily)
        self.tqqq_ema = self.EMA("TQQQ", 15, Resolution.Daily)

        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.BeforeMarketClose("TQQQ", 30),  # 收盘前30分钟执行
            self.Trade
        )

    def Trade(self):
        # 市场情绪过滤（无TQQQ趋势，不交易）
        if not self.tqqq_ema.IsReady:
            return
        tqqq_price = self.Securities["TQQQ"].Price
        if tqqq_price < self.tqqq_ema.Current.Value:
            self.Debug(f"[情绪过滤] TQQQ({tqqq_price:.2f}) < EMA15({self.tqqq_ema.Current.Value:.2f}) → 不建仓")
            return

        # 有持仓时，处理加仓、止盈止损
        if self.current_symbol:
            price = self.Securities[self.current_symbol].Price
            if price is None or price <= 0 or np.isnan(price):
                return

            self.max_price = max(self.max_price, price)

            # 动态止损条件
            stop_price = min(self.entry_price * (1 - self.stop_loss), self.max_price * (1 - self.trailing_stop_pct))
            if price <= stop_price:
                self.Liquidate(self.current_symbol, "动态止损")
                self.Debug(f"[止损] {self.current_symbol} @ {price:.2f}")
                self._reset_position()
                return

            # 固定止盈 or 动态止盈
            if price >= self.entry_price * (1 + self.take_profit):
                self.Liquidate(self.current_symbol, "固定止盈")
                self.Debug(f"[止盈] {self.current_symbol} 固定止盈 @ {price:.2f}")
                self._reset_position()
                return
            elif price <= self.max_price * (1 - self.trailing_stop_pct):
                self.Liquidate(self.current_symbol, "动态止盈")
                self.Debug(f"[止盈] {self.current_symbol} 动态止盈（回撤8%）@ {price:.2f}")
                self._reset_position()
                return

            # 加仓逻辑
            qty0 = self.Portfolio[self.current_symbol].Quantity
            if not self.added_level_1 and price >= self.entry_price * 1.03:
                qty = int(qty0 * 0.5)
                if qty > 0:
                    self.MarketOrder(self.current_symbol, qty)
                    self.added_level_1 = True
                    self.Debug(f"[加仓1] {self.current_symbol} @ {price:.2f}")

            if not self.added_level_2 and price >= self.entry_price * 1.06:
                qty = int(qty0 * 0.3)
                if qty > 0:
                    self.MarketOrder(self.current_symbol, qty)
                    self.added_level_2 = True
                    self.Debug(f"[加仓2] {self.current_symbol} @ {price:.2f}")

            return

        # 开仓逻辑
        candidates = []
        for symbol in self.symbols:
            hist = self.History(symbol, self.lookback + 1, Resolution.Daily)
            if hist.empty or symbol not in hist.index.get_level_values(0):
                continue

            closes = hist.loc[symbol]['close'].values
            volumes = hist.loc[symbol]['volume'].values

            if len(closes) <= 1 or np.isnan(closes).any() or np.isnan(volumes).any():
                continue

            if closes[-1] > max(closes[:-1]) and volumes[-1] > sum(volumes[:-1]) / self.lookback:
                pct_change = (closes[-1] - closes[-2]) / closes[-2]
                candidates.append((symbol, pct_change))

        if not candidates:
            return

        selected = sorted(candidates, key=lambda x: -x[1])[0]
        symbol = selected[0]
        price = self.Securities[symbol].Price
        if price is None or price <= 0 or np.isnan(price):
            return

        quantity = int(self.Portfolio.Cash / price)
        if quantity > 0:
            self.MarketOrder(symbol, quantity)
            self.current_symbol = symbol
            self.entry_price = price
            self.max_price = price
            self.added_level_1 = False
            self.added_level_2 = False
            self.Debug(f"[开仓] {symbol} @ {price:.2f}")

    def _reset_position(self):
        self.current_symbol = None
        self.entry_price = None
        self.max_price = None
        self.added_level_1 = False
        self.added_level_2 = False

    def OnData(self, data):
        pass
