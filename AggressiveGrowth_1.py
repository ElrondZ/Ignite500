# region imports
from AlgorithmImports import *


class AggressiveGrowth(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetCash(500)

        self.tickers = ["TSLA", "NVDA", "AMD", "PLTR", "MARA", "MLGO", "SQQQ", "TQQQ", "COIN"]
        self.symbols = [self.AddEquity(t, Resolution.Daily).Symbol for t in self.tickers]

        self.lookback = 5
        self.stop_loss = 0.05
        self.take_profit = 0.10
        self.max_positions = 1

        self.current_symbol = None
        self.entry_price = None

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen("TSLA", 30), self.Trade)

    def Trade(self):
        if self.current_symbol:
            price = self.Securities[self.current_symbol].Price
            if price <= self.entry_price * (1 - self.stop_loss):
                self.Liquidate(self.current_symbol, "Stop Loss")
                self.Debug(f"[止损] {self.current_symbol} @ {price}")
                self.current_symbol = None
                self.entry_price = None
            elif price >= self.entry_price * (1 + self.take_profit):
                self.Liquidate(self.current_symbol, "Take Profit")
                self.Debug(f"[止盈] {self.current_symbol} @ {price}")
                self.current_symbol = None
                self.entry_price = None
            return

        candidates = []
        for symbol in self.symbols:
            hist = self.History(symbol, self.lookback + 1, Resolution.Daily)
            if hist.empty or symbol not in hist.index.get_level_values(0):
                continue

            closes = hist.loc[symbol]['close'].values
            volumes = hist.loc[symbol]['volume'].values

            if closes[-1] > max(closes[:-1]) and volumes[-1] > sum(volumes[:-1]) / self.lookback:
                pct_change = (closes[-1] - closes[-2]) / closes[-2]
                candidates.append((symbol, pct_change))

        if not candidates:
            return

        selected = sorted(candidates, key=lambda x: -x[1])[0]
        symbol = selected[0]
        price = self.Securities[symbol].Price
        quantity = int(self.Portfolio.Cash / price)

        if quantity > 0:
            self.MarketOrder(symbol, quantity)
            self.current_symbol = symbol
            self.entry_price = price
            self.Debug(f"[开仓] {symbol} @ {price:.2f}")

    def OnData(self, data):
        pass
