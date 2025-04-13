import talib as ta
import pandas as pd
import numpy as np
from enum import Enum

class TradeType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    REVERSE_LONG = "REVERSE_LONG"
    REVERSE_SHORT = "REVERSE_SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"

class Strategy:
    def __init__(self, rsi_period=10, rsi_overbought=85, rsi_oversold=15, atr_period=14, atr_multiplier=3.0, risk_pct=1.0, dip_drop_pct=0.01, dip_drop_atr_mult=1.0, dip_consol_window=6, dip_consol_atr_mult=0.7, profit_threshold=0.01):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.risk_pct = risk_pct
        self.dip_drop_pct = dip_drop_pct
        self.dip_drop_atr_mult = dip_drop_atr_mult
        self.dip_consol_window = dip_consol_window
        self.dip_consol_atr_mult = dip_consol_atr_mult

    def run(self, df: pd.DataFrame, equity: float = 10000.0) -> pd.DataFrame:
        df = self.calculate_indicators(df)
        df = self.generate_signals(df.copy(), equity)
        return df

    def calculate_indicators(self, df):
        df["ema_10"] = ta.EMA(df["close"], timeperiod=10).shift(1)
        df["ema_20"] = ta.EMA(df["close"], timeperiod=20).shift(1)
        df["ema_50"] = ta.EMA(df["close"], timeperiod=50).shift(1)
        df["rsi"] = ta.RSI(df["close"], timeperiod=self.rsi_period).shift(1)
        df["atr"] = ta.ATR(df["high"], df["low"], df["close"], timeperiod=self.atr_period).shift(1)
        df["adx"] = ta.ADX(df["high"], df["low"], df["close"], timeperiod=18).shift(1)
        return df

    def generate_signals(self, df, equity=10000.0):
       # Ensure that entry/exit signals are based on data up to the previous bar
        df["trade_type"] = TradeType.HOLD.value
        df["Position"] = 0
        df["entry_price"] = np.nan
        df["stoploss_price"] = np.nan
        df["position_size"] = 0.0

        # Shift pct_change by 1 step
        df["pct_change"] = df["close"].pct_change().shift(1)

        # Calculate signals for trade entries and exits
        sharp_pct_drop = df["pct_change"] < -self.dip_drop_pct
        sharp_atr_drop = df["pct_change"] < -(self.dip_drop_atr_mult * df["atr"] / df["close"].shift(1))

        # Check for consolidation using rolling max and min up to the current period
        range_N = df["high"].rolling(self.dip_consol_window).max().shift(1) - df["low"].rolling(self.dip_consol_window).min().shift(1)
        consol = range_N < (self.dip_consol_atr_mult * df["atr"])

        dip_buy = (sharp_pct_drop.shift(1) | sharp_atr_drop.shift(1)) & consol

        # Set buy/sell conditions based on only past data
        bullish_cross = (
            (df["ema_10"].shift(1) > df["ema_20"].shift(1)) &
            (df["ema_20"].shift(1) > df["ema_50"].shift(1)) &
            (df["rsi"].shift(1) < self.rsi_overbought) &
            (df["adx"].shift(1) > 15)
        ) | dip_buy

        bearish_cross = (
            (df["ema_10"].shift(1) < df["ema_20"].shift(1)) &
            (df["ema_20"].shift(1) < df["ema_50"].shift(1)) &
            (df["rsi"].shift(1) > self.rsi_oversold) &
            (df["adx"].shift(1) > 15)
        )

        # Only trade with past information
        df.loc[bullish_cross, "Position"] = 1
        df.loc[bearish_cross, "Position"] = -1


        df["Position"] = df["Position"].replace(0, np.nan).ffill().fillna(0)
        df["position_change"] = df["Position"].diff().fillna(df["Position"])

        entry_long = df["position_change"] == 1
        entry_short = df["position_change"] == -1

        df.loc[entry_long, "entry_price"] = df.loc[entry_long, "close"]
        df.loc[entry_short, "entry_price"] = df.loc[entry_short, "close"]

        df.loc[entry_long, "stoploss_price"] = df.loc[entry_long, "entry_price"] - df.loc[entry_long, "atr"] * self.atr_multiplier
        df.loc[entry_short, "stoploss_price"] = df.loc[entry_short, "entry_price"] + df.loc[entry_short, "atr"] * self.atr_multiplier

        df["entry_price"] = df["entry_price"].where(df["Position"] != 0).ffill()
        df["stoploss_price"] = df["stoploss_price"].where(df["Position"] != 0).ffill()

        df["position_size"] = self.calculate_position_size(equity, df["entry_price"], df["stoploss_price"]).fillna(0)

        exit_long = (df["Position"] == 1) & ((df["ema_20"] < df["ema_50"]) | (df["rsi"] > self.rsi_overbought))
        exit_short = (df["Position"] == -1) & ((df["ema_20"] > df["ema_50"]) | (df["rsi"] < self.rsi_oversold))

        long_stoploss = (df["Position"] == 1) & (df["low"] < df["stoploss_price"])
        short_stoploss = (df["Position"] == -1) & (df["high"] > df["stoploss_price"])

        exit_signal = exit_long | exit_short | long_stoploss | short_stoploss
        df.loc[exit_signal, "Position"] = 0
        df["Position"] = df["Position"].ffill().fillna(0)

        df["position_change"] = df["Position"].diff().fillna(df["Position"])
        df["prev_position"] = df["Position"].shift(1).fillna(0)

        long_entries = df["position_change"] == 1
        short_entries = df["position_change"] == -1

        df.loc[long_entries, "trade_type"] = np.where(df.loc[long_entries, "prev_position"] == -1, TradeType.REVERSE_LONG.value, TradeType.LONG.value)
        df.loc[short_entries, "trade_type"] = np.where(df.loc[short_entries, "prev_position"] == 1, TradeType.REVERSE_SHORT.value, TradeType.SHORT.value)

        df.loc[(df["position_change"] != 0) & (df["Position"] == 0), "trade_type"] = TradeType.CLOSE.value

        df.drop(columns=["Position", "position_change"], inplace=True)
        return df

    def calculate_position_size(self, equity, entry_price, stoploss_price):
        if isinstance(entry_price, pd.Series) and isinstance(stoploss_price, pd.Series):
            risk_amount = equity * (self.risk_pct / 100)
            risk_per_unit = (entry_price - stoploss_price).abs()
            risk_per_unit = risk_per_unit.where(risk_per_unit > 0)
            position_size = pd.Series(0.0, index=risk_per_unit.index)
            valid_mask = (risk_per_unit > 0) & ~risk_per_unit.isna()
            position_size.loc[valid_mask] = risk_amount / risk_per_unit.loc[valid_mask]
            return position_size.round(2)
        else:
            risk_amount = equity * (self.risk_pct / 100)
            risk_per_unit = abs(entry_price - stoploss_price)
            if risk_per_unit == 0 or pd.isna(risk_per_unit):
                return 0
            return np.round(risk_amount / risk_per_unit, 2)
