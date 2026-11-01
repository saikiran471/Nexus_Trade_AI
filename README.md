# Nexus Trade AI — NSE / BSE Stock Scanner

A locally run Flask stock-scanning dashboard with an animated HTML/CSS/JavaScript interface and individual candlestick chart views.

## Start on Windows (no Git required)

1. Install Python 3.10 or newer from https://www.python.org/downloads/
2. Extract this ZIP folder.
3. Double-click `run_windows.bat`.
4. The first run creates a virtual environment and installs dependencies.
5. The browser opens at http://127.0.0.1:5000.

## Start on macOS / Linux

Run `chmod +x run_mac_linux.sh` once, then `./run_mac_linux.sh`.

## Using the scanner

- Choose NSE or BSE.
- Enter comma-separated symbols, e.g. `RELIANCE, TCS, INFY, HDFCBANK`.
- Select any scan preferences and click **SCAN STOCKS**.
- Click **VIEW CHART** on a stock card to open its candlestick chart.
- Choose 1D, 1W or 1M chart intervals.

Common stock-name shortcuts are included in `app.py`. You can add more in the `ALIASES` dictionary. For less common listings, enter the exchange ticker symbol.

## Data and important limitations

This starter app retrieves historical price data through the `yfinance` Python package (Yahoo Finance). It is **not** an exchange-certified real-time feed, and data may be delayed, incomplete, rate-limited or unavailable for some NSE/BSE listings. BSE symbol coverage can differ from NSE coverage. Do not use it as the sole basis for financial decisions.

For reliable live quotes, full exchange coverage, alerts and commercial use, connect a licensed market-data provider and follow its exchange/API terms. No API key is required for the current historical-data implementation.

## Current scan filters

- Bullish: positive daily move and EMA20 above EMA50.
- Bearish: negative daily move and EMA20 below EMA50.
- Momentum: daily change above 1% (a simple momentum proxy, not a formal breakout detector).
- High volume: current volume above 1.5× the 20-session average.
- RSI oversold / overbought: RSI(14) below 30 / above 70.

The pattern label is a basic candle-shape heuristic, not a validated trading signal. The app does not provide investment advice or guaranteed predictions.

## Project structure

```text
nexus_trade_ai/
  app.py
  requirements.txt
  run_windows.bat
  run_mac_linux.sh
  templates/
    index.html
  static/
    style.css
    app.js
```

The interface loads Google Fonts and TradingView Lightweight Charts from public CDNs, so an internet connection is needed for those assets. Market-data retrieval also requires internet access.
