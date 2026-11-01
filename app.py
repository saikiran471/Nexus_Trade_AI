from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

# Common symbol shortcuts. Users can also enter any valid NSE/BSE ticker.
ALIASES = {
    "RELIANCE": "RELIANCE", "TCS": "TCS", "INFY": "INFY",
    "INFOSYS": "INFY", "HDFCBANK": "HDFCBANK", "HDFC BANK": "HDFCBANK",
    "ICICIBANK": "ICICIBANK", "ICICI BANK": "ICICIBANK",
    "SBIN": "SBIN", "SBI": "SBIN", "ITC": "ITC", "BHARTIARTL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL", "LT": "LT", "L&T": "LT", "AXISBANK": "AXISBANK",
    "KOTAKBANK": "KOTAKBANK", "WIPRO": "WIPRO", "TATAMOTORS": "TATAMOTORS",
    "TATA MOTORS": "TATAMOTORS", "MARUTI": "MARUTI", "SUNPHARMA": "SUNPHARMA",
    "BAJFINANCE": "BAJFINANCE", "HINDUNILVR": "HINDUNILVR", "ONGC": "ONGC",
    "NTPC": "NTPC", "POWERGRID": "POWERGRID", "TITAN": "TITAN",
    "ADANIENT": "ADANIENT", "ADANIPORTS": "ADANIPORTS", "TATASTEEL": "TATASTEEL",
    "JSWSTEEL": "JSWSTEEL", "COALINDIA": "COALINDIA", "ULTRACEMCO": "ULTRACEMCO"
}

def normalize_symbol(raw, exchange):
    name = raw.strip().upper()
    if not name:
        return None
    # Accept users entering a Yahoo Finance ticker with its suffix.
    if name.endswith(".NS") or name.endswith(".BO"):
        return name
    symbol = ALIASES.get(name, name.replace(" ", "").replace("&", ""))
    return symbol + (".NS" if exchange == "NSE" else ".BO")

def get_history(ticker, period="6mo", interval="1d"):
    try:
        data = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if data is None or data.empty:
            return None
        data = data.dropna(subset=["Close"])
        return data
    except Exception:
        return None

def add_indicators(df):
    d = df.copy()
    close = d["Close"]
    d["EMA20"] = close.ewm(span=20, adjust=False).mean()
    d["EMA50"] = close.ewm(span=50, adjust=False).mean()
    d["SMA20"] = close.rolling(20).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI"] = 100 - (100 / (1 + rs))
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    d["MACD"] = fast - slow
    d["SIGNAL"] = d["MACD"].ewm(span=9, adjust=False).mean()
    return d

def detect_pattern(df):
    if len(df) < 2:
        return "Not enough candles"
    a, b = df.iloc[-2], df.iloc[-1]
    body = abs(float(b["Close"]) - float(b["Open"]))
    candle_range = max(float(b["High"]) - float(b["Low"]), 1e-9)
    lower_wick = min(float(b["Open"]), float(b["Close"])) - float(b["Low"])
    upper_wick = float(b["High"]) - max(float(b["Open"]), float(b["Close"]))
    if b["Close"] > b["Open"] and a["Close"] < a["Open"] and b["Close"] >= a["Open"] and b["Open"] <= a["Close"]:
        return "Bullish engulfing"
    if b["Close"] < b["Open"] and a["Close"] > a["Open"] and b["Open"] >= a["Close"] and b["Close"] <= a["Open"]:
        return "Bearish engulfing"
    if lower_wick > body * 2 and upper_wick < max(body, 1e-9) and b["Close"] > b["Open"]:
        return "Hammer-like candle"
    if upper_wick > body * 2 and lower_wick < max(body, 1e-9) and b["Close"] < b["Open"]:
        return "Shooting-star-like candle"
    if body / candle_range < 0.08:
        return "Doji"
    return "No major single-candle pattern"

def scan_one(raw, exchange):
    ticker = normalize_symbol(raw, exchange)
    if not ticker:
        return None
    hist = get_history(ticker, "6mo", "1d")
    if hist is None or len(hist) < 2:
        return {"symbol": raw.strip().upper(), "ticker": ticker, "exchange": exchange,
                "error": "No market data returned. Check the symbol or try the other exchange."}
    d = add_indicators(hist)
    last, prev = d.iloc[-1], d.iloc[-2]
    price = float(last["Close"])
    change = price - float(prev["Close"])
    pct = (change / float(prev["Close"]) * 100) if prev["Close"] else 0
    rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else None
    macd = float(last["MACD"]) if pd.notna(last["MACD"]) else None
    signal = float(last["SIGNAL"]) if pd.notna(last["SIGNAL"]) else None
    volume = float(last.get("Volume", 0) or 0)
    avg_vol = float(d["Volume"].tail(20).mean()) if "Volume" in d else 0
    return {
        "symbol": raw.strip().upper(), "ticker": ticker, "exchange": exchange,
        "price": round(price, 2), "change": round(change, 2), "change_pct": round(pct, 2),
        "volume": int(volume), "avg_volume": int(avg_vol),
        "rsi": round(rsi, 1) if rsi is not None else None,
        "macd_signal": "Bullish" if macd is not None and signal is not None and macd > signal else "Bearish",
        "trend": "Bullish" if last["EMA20"] > last["EMA50"] else "Bearish",
        "pattern": detect_pattern(d), "date": str(d.index[-1].date())
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/scan")
def scan():
    payload = request.get_json(silent=True) or {}
    raw_symbols = payload.get("symbols", [])
    exchange = str(payload.get("exchange", "NSE")).upper()
    prefs = payload.get("preferences", {})
    if exchange not in ("NSE", "BSE"):
        return jsonify({"error": "Exchange must be NSE or BSE."}), 400
    if isinstance(raw_symbols, str):
        raw_symbols = [s.strip() for s in raw_symbols.split(",")]
    symbols = list(dict.fromkeys([str(s).strip() for s in raw_symbols if str(s).strip()]))[:40]
    if not symbols:
        return jsonify({"error": "Enter at least one stock symbol."}), 400
    results = []
    for symbol in symbols:
        item = scan_one(symbol, exchange)
        if item:
            results.append(item)
    valid = [x for x in results if "error" not in x]
    if prefs.get("bullish"):
        valid = [x for x in valid if x["change_pct"] > 0 and x["trend"] == "Bullish"]
    if prefs.get("bearish"):
        valid = [x for x in valid if x["change_pct"] < 0 and x["trend"] == "Bearish"]
    if prefs.get("breakout"):
        valid = [x for x in valid if x["price"] >= x.get("price", 0) and x["change_pct"] > 1]
    if prefs.get("high_volume"):
        valid = [x for x in valid if x["avg_volume"] > 0 and x["volume"] > x["avg_volume"] * 1.5]
    if prefs.get("oversold"):
        valid = [x for x in valid if x["rsi"] is not None and x["rsi"] < 30]
    if prefs.get("overbought"):
        valid = [x for x in valid if x["rsi"] is not None and x["rsi"] > 70]
    return jsonify({"results": valid, "errors": [x for x in results if "error" in x],
                    "count": len(valid), "updated": datetime.now().strftime("%H:%M:%S"),
                    "notice": "Quotes and history are provided by Yahoo Finance and may be delayed; this is not an exchange-certified real-time feed."})

@app.get("/api/chart/<exchange>/<symbol>")
def chart(exchange, symbol):
    exchange = exchange.upper()
    if exchange not in ("NSE", "BSE"):
        return jsonify({"error": "Invalid exchange."}), 400
    ticker = normalize_symbol(symbol, exchange)
    period = request.args.get("period", "6mo")
    interval = request.args.get("interval", "1d")
    allowed = {"1d": ("1mo", "5d"), "1wk": ("2y", "1y"), "1mo": ("5y", "2y")}
    if interval not in allowed:
        interval = "1d"
    if period not in allowed[interval]:
        period = allowed[interval][0]
    hist = get_history(ticker, period, interval)
    if hist is None:
        return jsonify({"error": "No chart data available for this ticker."}), 404
    candles = []
    for idx, row in hist.iterrows():
        candles.append({
            "time": int(pd.Timestamp(idx).timestamp()),
            "open": round(float(row["Open"]), 4), "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4), "close": round(float(row["Close"]), 4),
            "volume": int(row.get("Volume", 0) or 0)
        })
    return jsonify({"ticker": ticker, "candles": candles, "interval": interval,
                    "notice": "Historical/delayed data; availability depends on the data provider."})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
