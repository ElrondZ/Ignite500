# region imports
from AlgorithmImports import *

class AggressiveGrowth(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2021, 1, 1)
        self.SetEndDate(2024, 12, 31)  # 设置结束时间
        self.SetCash(500)

        self.tickers = ["TSLA", "NVDA", "AMD", "PLTR", "MARA", "MLGO", "SQQQ", "TQQQ", "COIN"]
        self.symbols = [self.AddEquity(t, Resolution.Daily).Symbol for t in self.tickers]

        self.lookback = 5
        self.stop_loss = 0.05
        self.take_profit = 0.10
        self.max_positions = 1

        self.current_symbol = None
        self.entry_price = None
        self.max_price = None
        self.added_level_1 = False
        self.added_level_2 = False

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen("TSLA", 30), self.Trade)

    def Trade(self):
        # 如果当前有持仓
        if self.current_symbol:
            price = self.Securities[self.current_symbol].Price

            # 保证 price 有效
            if price is None or price <= 0 or np.isnan(price):
                return

            self.max_price = max(self.max_price, price)

            # 止损逻辑
            if price <= self.entry_price * (1 - self.stop_loss):
                self.Liquidate(self.current_symbol, "Stop Loss")
                self.Debug(f"[止损] {self.current_symbol} @ {price:.2f}")
                self._reset_position()
                return

            # 止盈逻辑
            if price >= self.entry_price * (1 + self.take_profit):
                self.Liquidate(self.current_symbol, "Take Profit")
                self.Debug(f"[止盈] {self.current_symbol} @ {price:.2f}")
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

        # 没有持仓，开始寻找突破标的
        candidates = []
        for symbol in self.symbols:
            hist = self.History(symbol, self.lookback + 1, Resolution.Daily)
            if hist.empty or symbol not in hist.index.get_level_values(0):
                continue

            closes = hist.loc[symbol]['close'].values
            volumes = hist.loc[symbol]['volume'].values

            # 防止历史数据不足
            if len(closes) <= 1 or len(volumes) <= 1:
                continue

            # 防止 NaN 数据引发异常
            if np.isnan(closes).any() or np.isnan(volumes).any():
                continue

            if closes[-1] > max(closes[:-1]) and volumes[-1] > sum(volumes[:-1]) / self.lookback:
                pct_change = (closes[-1] - closes[-2]) / closes[-2]
                candidates.append((symbol, pct_change))

        if not candidates:
            return

        # 选择涨幅最大的票
        selected = sorted(candidates, key=lambda x: -x[1])[0]
        symbol = selected[0]
        price = self.Securities[symbol].Price

        # 防止除以 0 或无效价格
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
