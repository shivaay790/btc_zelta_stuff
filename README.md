# btc_zelta_stuff

# EMA-RSI-Dip-Buy Strategy

This is a custom algorithmic trading strategy that combines **EMA crossover**, **RSI levels**, **ADX strength**, and a **dip-buying mechanism** using **ATR-based volatility filtering**.

##  Strategy Logic

### Entry Conditions
- **Bullish Entry** (`LONG` or `REVERSE_LONG`)
  - `EMA 10 > EMA 20 > EMA 50`
  - RSI below overbought (default: 85)
  - ADX > 15 (strong trend)
  - OR a sharp price drop (dip) followed by a volatility contraction (consolidation)

- **Bearish Entry** (`SHORT` or `REVERSE_SHORT`)
  - `EMA 10 < EMA 20 < EMA 50`
  - RSI above oversold (default: 15)
  - ADX > 15

###  Exit Conditions
- Opposite EMA and RSI signal
- OR price breaches ATR-based stoploss

## Technical Indicators Used
- **EMA (10, 20, 50)**
- **RSI (default: 10)**
- **ATR (default: 10)**
- **ADX (18)**

## Features
- No forward-looking bias (`shift(1)` ensures signal generation uses only historical data)
- Dip-buy detection based on % drop or ATR volatility spike
- Adaptive stoploss using ATR × multiplier
- Dynamic position sizing based on fixed risk per trade
- Trade types: `LONG`, `SHORT`, `REVERSE_LONG`, `REVERSE_SHORT`, `CLOSE`, `HOLD`

## Parameters

| Parameter             | Description                                   | Default |
|-----------------------|-----------------------------------------------|---------|
| `rsi_period`          | RSI calculation period                        | 10      |
| `rsi_overbought`      | Overbought RSI level                          | 85      |
| `rsi_oversold`        | Oversold RSI level                            | 15      |
| `atr_period`          | ATR period                                    | 10      |
| `atr_multiplier`      | Stoploss distance multiplier                  | 4.0     |
| `risk_pct`            | % of equity risked per trade                  | 1.0     |
| `dip_drop_pct`        | Sharp drop threshold in percentage            | 0.01    |
| `dip_drop_atr_mult`   | Sharp drop threshold in ATR units             | 1.0     |
| `dip_consol_window`   | Window size for consolidation detection       | 6       |
| `dip_consol_atr_mult` | Consolidation volatility threshold (ATR mult) | 0.7     |

## Requirements

- Python 3.7+
- `pandas`
- `numpy`
- `TA-Lib`

Install dependencies:
```bash
pip install pandas numpy TA-Lib

