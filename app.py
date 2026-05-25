from urllib.parse import urlencode
from datetime import datetime
from zoneinfo import ZoneInfo
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from backtest import backtest_signals, get_trade_history
from data_fetch import (
    fetch_fundamental_snapshot,
    fetch_quote_snapshot,
    fetch_stock_data,
    fetch_stock_news,
    search_companies,
)
from macd_logic import calculate_macd, generate_signals, get_last_n_signals, get_latest_signal


st.set_page_config(
    page_title="MarketDesk India",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        :root {
            --panel: #101820;
            --panel-soft: #13212b;
            --line: rgba(255, 255, 255, 0.08);
            --text-soft: #9fb0bf;
            --accent: #27d3a2;
            --gold: #d6b45d;
            --danger: #ff5b6e;
            --amber: #f0b84d;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 180, 93, 0.13), transparent 28rem),
                radial-gradient(circle at 80% 10%, rgba(39, 211, 162, 0.08), transparent 26rem),
                linear-gradient(135deg, #060b0f 0%, #0a1118 45%, #11181f 100%);
            color: #edf5f7;
        }

        [data-testid="stSidebar"] {
            background: #071015;
            border-right: 1px solid var(--line);
        }

        [data-testid="stHeader"] {
            background: rgba(7, 16, 21, 0.65);
            backdrop-filter: blur(16px);
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1480px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        .terminal-hero {
            border: 1px solid rgba(214, 180, 93, 0.26);
            border-radius: 8px;
            padding: 26px 28px;
            background: linear-gradient(145deg, rgba(20, 28, 34, 0.98), rgba(8, 15, 20, 0.98));
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
            margin-bottom: 18px;
        }

        .kicker {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .hero-title {
            font-size: clamp(2rem, 4vw, 4rem);
            line-height: 1;
            font-weight: 800;
            margin: 0;
        }

        .hero-subtitle {
            color: var(--text-soft);
            max-width: 760px;
            margin-top: 12px;
            font-size: 1rem;
        }

        .metric-card {
            border: 1px solid rgba(214, 180, 93, 0.14);
            background: linear-gradient(150deg, rgba(17, 27, 34, 0.95), rgba(10, 18, 24, 0.95));
            border-radius: 8px;
            padding: 15px 16px;
            min-height: 112px;
        }

        .metric-label {
            color: var(--text-soft);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 8px;
        }

        .metric-value {
            color: #f5fbfc;
            font-size: 1.45rem;
            font-weight: 760;
        }

        .metric-delta-positive {
            color: var(--accent);
            font-size: 0.88rem;
            font-weight: 650;
        }

        .metric-delta-negative {
            color: var(--danger);
            font-size: 0.88rem;
            font-weight: 650;
        }

        .section-title {
            margin-top: 8px;
            margin-bottom: 8px;
            color: #e9f5f7;
            font-size: 1.2rem;
            font-weight: 760;
        }

        .news-item {
            border: 1px solid var(--line);
            background: rgba(16, 24, 32, 0.78);
            border-radius: 8px;
            padding: 13px 14px;
            margin-bottom: 10px;
        }

        .news-source {
            color: var(--accent);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 5px;
        }

        .news-title {
            color: #f4fbfc;
            font-size: 0.95rem;
            font-weight: 680;
            line-height: 1.35;
        }

        .news-summary {
            color: var(--text-soft);
            font-size: 0.86rem;
            line-height: 1.4;
            margin-top: 5px;
        }

        .watch-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px solid var(--line);
            padding: 9px 0;
            font-size: 0.9rem;
        }

        .watch-symbol {
            color: #edf5f7;
            font-weight: 700;
        }

        .watch-price {
            color: var(--text-soft);
        }

        .setup-card {
            border: 1px solid rgba(214, 180, 93, 0.14);
            background: linear-gradient(145deg, rgba(16, 24, 32, 0.92), rgba(13, 23, 30, 0.92));
            border-radius: 8px;
            padding: 16px;
            min-height: 132px;
        }

        .scanner-shell {
            border: 1px solid rgba(214, 180, 93, 0.18);
            background: rgba(12, 20, 26, 0.74);
            border-radius: 8px;
            padding: 12px 14px;
        }

        .setup-action {
            color: var(--accent);
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .setup-action-wait {
            color: var(--amber);
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .setup-action-risk {
            color: var(--danger);
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .setup-note {
            color: var(--text-soft);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .analysis-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px solid var(--line);
            padding: 10px 0;
        }

        .analysis-label {
            color: var(--text-soft);
        }

        .analysis-value {
            color: #edf5f7;
            font-weight: 750;
            text-align: right;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            background: rgba(16, 24, 32, 0.82);
            border-radius: 8px;
            padding: 14px 16px;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }

        .stButton > button {
            border-radius: 6px;
            border: 1px solid rgba(39, 211, 162, 0.34);
            background: #13212b;
            color: #effbfc;
            font-weight: 700;
        }

        .stButton > button:hover {
            border-color: var(--accent);
            color: white;
            background: #17313a;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


INTERVAL_OPTIONS = {
    "1 Minute": "1m",
    "5 Minutes": "5m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "4 Hours": "4h",
    "1 Day": "1d",
}

MARKET_SYMBOLS = ["^NSEI", "^NSEBANK", "^BSESN", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]


def format_large_number(value):
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:,.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:,.2f} L"
    return f"₹{value:,.2f}"


def format_ratio(value, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}{suffix}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def calculate_rsi(close, period=14):
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def calculate_atr(data, period=14):
    high_low = data["high"] - data["low"]
    high_close = (data["high"] - data["close"].shift()).abs()
    low_close = (data["low"] - data["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def format_ist_time(value):
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        else:
            value = value.astimezone(ZoneInfo("Asia/Kolkata"))
        return value.strftime("%Y-%m-%d %H:%M IST")
    return str(value)


def detect_candlestick_pattern(data):
    if data is None or len(data) < 3:
        return "Neutral", "None"

    current = data.iloc[-1]
    previous = data.iloc[-2]
    body = abs(float(current["close"] - current["open"]))
    candle_range = max(float(current["high"] - current["low"]), 0.01)
    upper_wick = float(current["high"] - max(current["open"], current["close"]))
    lower_wick = float(min(current["open"], current["close"]) - current["low"])

    bullish_engulfing = (
        current["close"] > current["open"]
        and previous["close"] < previous["open"]
        and current["close"] >= previous["open"]
        and current["open"] <= previous["close"]
    )
    bearish_engulfing = (
        current["close"] < current["open"]
        and previous["close"] > previous["open"]
        and current["open"] >= previous["close"]
        and current["close"] <= previous["open"]
    )
    hammer = lower_wick >= body * 2 and upper_wick <= body * 0.8 and current["close"] > current["open"]
    shooting_star = upper_wick >= body * 2 and lower_wick <= body * 0.8 and current["close"] < current["open"]

    if bullish_engulfing:
        return "Bullish", "Bullish Engulfing"
    if bearish_engulfing:
        return "Bearish", "Bearish Engulfing"
    if hammer:
        return "Bullish", "Hammer"
    if shooting_star:
        return "Bearish", "Shooting Star"
    if body / candle_range < 0.18:
        return "Neutral", "Doji / Indecision"
    return "Neutral", "No strong candle pattern"


def detect_chart_pattern(data):
    if data is None or len(data) < 30:
        return "Neutral", "Not enough candles"

    latest = data.iloc[-1]
    previous_window = data.iloc[-21:-1]
    recent = data.tail(8)
    resistance = float(previous_window["high"].max())
    support = float(previous_window["low"].min())
    higher_lows = recent["low"].iloc[-1] > recent["low"].iloc[0]
    lower_highs = recent["high"].iloc[-1] < recent["high"].iloc[0]

    if float(latest["close"]) > resistance:
        return "Bullish", "20-candle breakout"
    if float(latest["close"]) < support:
        return "Bearish", "20-candle breakdown"
    if higher_lows and float(latest["close"]) > float(data["ema_slow"].iloc[-1]):
        return "Bullish", "Higher-low uptrend"
    if lower_highs and float(latest["close"]) < float(data["ema_slow"].iloc[-1]):
        return "Bearish", "Lower-high downtrend"
    return "Neutral", "Range / no clear pattern"


def build_signal_confirmation(data, raw_signal=None):
    if data is None or len(data) < 35:
        return {
            "confirmed_signal": "WAIT",
            "score": 0,
            "candle_pattern": "Not enough data",
            "chart_pattern": "Not enough data",
            "reason": "Not enough candles for confirmation",
        }

    latest = data.iloc[-1]
    previous = data.iloc[-2]
    previous_diff = float(previous["macd"] - previous["signal"])
    latest_diff = float(latest["macd"] - latest["signal"])

    if raw_signal is None:
        if previous_diff <= 0 < latest_diff:
            raw_signal = "BUY"
        elif previous_diff >= 0 > latest_diff:
            raw_signal = "SELL"
        else:
            raw_signal = "WAIT"

    candle_bias, candle_pattern = detect_candlestick_pattern(data)
    chart_bias, chart_pattern = detect_chart_pattern(data)
    rsi_series = calculate_rsi(data["close"])
    rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0
    close = float(latest["close"])
    ema_slow = float(latest["ema_slow"])
    hist = float(latest["hist"])
    volume_avg = float(data["volume"].tail(20).mean()) if "volume" in data and len(data) >= 20 else 0
    volume_ok = volume_avg == 0 or float(latest.get("volume", 0)) >= volume_avg * 0.8

    score = 0
    reasons = []
    if raw_signal == "BUY":
        if candle_bias == "Bullish":
            score += 1
            reasons.append(candle_pattern)
        if chart_bias == "Bullish":
            score += 1
            reasons.append(chart_pattern)
        if close > ema_slow and hist > 0 and 38 <= rsi <= 72:
            score += 1
            reasons.append("trend + RSI confirm")
        if volume_ok:
            score += 1
            reasons.append("volume acceptable")
        confirmed = "BUY" if score >= 2 and candle_bias != "Bearish" else "WAIT"
    elif raw_signal == "SELL":
        if candle_bias == "Bearish":
            score += 1
            reasons.append(candle_pattern)
        if chart_bias == "Bearish":
            score += 1
            reasons.append(chart_pattern)
        if close < ema_slow and hist < 0 and rsi <= 62:
            score += 1
            reasons.append("trend + RSI confirm")
        if volume_ok:
            score += 1
            reasons.append("volume acceptable")
        confirmed = "SELL" if score >= 2 and candle_bias != "Bullish" else "WAIT"
    else:
        confirmed = "WAIT"
        reasons.append("no latest MACD crossover")

    return {
        "confirmed_signal": confirmed,
        "score": score,
        "candle_pattern": candle_pattern,
        "chart_pattern": chart_pattern,
        "reason": ", ".join(reasons) if reasons else "confirmation not strong enough",
    }


def apply_confirmed_signals(data):
    if data is None or data.empty:
        return data
    data = data.copy()
    data["raw_trade_signal"] = data["trade_signal"]
    confirmation = build_signal_confirmation(data)
    data.at[data.index[-1], "trade_signal"] = confirmation["confirmed_signal"]
    data.at[data.index[-1], "candle_pattern"] = confirmation["candle_pattern"]
    data.at[data.index[-1], "chart_pattern"] = confirmation["chart_pattern"]
    data.at[data.index[-1], "confirmation_score"] = confirmation["score"]
    data.at[data.index[-1], "confirmation_reason"] = confirmation["reason"]
    return data


def build_trade_setup(data):
    latest = data.iloc[-1]
    close = float(latest["close"])
    atr_series = calculate_atr(data)
    rsi_series = calculate_rsi(data["close"])
    atr = float(atr_series.dropna().iloc[-1]) if not atr_series.dropna().empty else close * 0.02
    rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0
    swing_low = float(data["low"].tail(10).min())
    swing_high = float(data["high"].tail(10).max())
    macd = float(latest["macd"])
    signal_line = float(latest["signal"])
    hist = float(latest["hist"])
    ema_fast = float(latest["ema_fast"])
    ema_slow = float(latest["ema_slow"])

    bullish = close > ema_fast > ema_slow and macd > signal_line and hist > 0 and 45 <= rsi <= 70
    weak_bullish = close > ema_slow and macd > signal_line and hist >= 0
    bearish = close < ema_slow or (macd < signal_line and hist < 0)

    if bullish:
        action = "BUY / ACCUMULATE"
        action_class = "setup-action"
        entry = close
        stop_loss = min(swing_low, close - (1.4 * atr))
        risk = max(entry - stop_loss, atr)
        target_1 = entry + (1.5 * risk)
        target_2 = entry + (2.5 * risk)
        exit_price = target_1
        note = "Trend and momentum are aligned. Entry is best near current price or on a small pullback."
    elif weak_bullish:
        action = "WAIT FOR PULLBACK"
        action_class = "setup-action-wait"
        entry = max(close - (0.6 * atr), float(data["low"].tail(5).min()))
        stop_loss = min(swing_low, entry - (1.2 * atr))
        risk = max(entry - stop_loss, atr)
        target_1 = entry + (1.4 * risk)
        target_2 = entry + (2.2 * risk)
        exit_price = target_1
        note = "Momentum is improving, but entry is cleaner on pullback or breakout confirmation."
    elif bearish:
        action = "AVOID FRESH BUY"
        action_class = "setup-action-risk"
        entry = None
        stop_loss = swing_high
        target_1 = None
        target_2 = None
        exit_price = close
        note = "Technical structure is weak. Existing holders can use the exit price as a risk-control reference."
    else:
        action = "NEUTRAL / WAIT"
        action_class = "setup-action-wait"
        entry = None
        stop_loss = close - (1.2 * atr)
        target_1 = None
        target_2 = None
        exit_price = close
        note = "No clean setup yet. Let price or MACD give a stronger confirmation."

    return {
        "action": action,
        "action_class": action_class,
        "entry": entry,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "exit_price": exit_price,
        "risk_reward": ((target_1 - entry) / (entry - stop_loss)) if entry and stop_loss and target_1 else None,
        "atr": atr,
        "rsi": rsi,
        "note": note,
    }


def build_investment_read(data, fundamentals):
    latest = data.iloc[-1]
    close = float(latest["close"])
    rsi_series = calculate_rsi(data["close"])
    rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0
    trend_score = 0

    if close > float(latest["ema_slow"]):
        trend_score += 1
    if float(latest["ema_fast"]) > float(latest["ema_slow"]):
        trend_score += 1
    if float(latest["macd"]) > float(latest["signal"]):
        trend_score += 1
    if 40 <= rsi <= 70:
        trend_score += 1

    fundamental_score = 0
    pe = fundamentals.get("trailing_pe")
    pb = fundamentals.get("price_to_book")
    roe = fundamentals.get("return_on_equity")
    profit_margin = fundamentals.get("profit_margins")
    debt_to_equity = fundamentals.get("debt_to_equity")

    if pe and 0 < pe < 35:
        fundamental_score += 1
    if pb and 0 < pb < 8:
        fundamental_score += 1
    if roe and roe > 0.10:
        fundamental_score += 1
    if profit_margin and profit_margin > 0.08:
        fundamental_score += 1
    if debt_to_equity is None or debt_to_equity < 150:
        fundamental_score += 1

    total_score = trend_score + fundamental_score
    if total_score >= 7:
        verdict = "Strong watchlist candidate"
    elif total_score >= 5:
        verdict = "Balanced, wait for good entry"
    elif total_score >= 3:
        verdict = "Mixed quality, be selective"
    else:
        verdict = "Weak setup for now"

    return {
        "verdict": verdict,
        "technical_score": f"{trend_score}/4",
        "fundamental_score": f"{fundamental_score}/5",
        "total_score": f"{total_score}/9",
        "rsi": rsi,
    }


def parse_symbol_list(text):
    tokens = re.split(r"[\s,;|]+", text.upper())
    symbols = []
    seen = set()
    for token in tokens:
        symbol = token.strip().replace(".NS", "")
        if symbol and symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return symbols[:250]


def normalize_lookup_text(value):
    value = str(value).upper()
    value = re.sub(r"\b(LIMITED|LTD|LTD\.|PRIVATE|PVT|CO|COMPANY|THE|INDIA|INDIAN)\b", " ", value)
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def parse_uploaded_stock_file(uploaded_file):
    if uploaded_file is None:
        return []

    raw_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    if uploaded_file.name.lower().endswith(".csv"):
        try:
            from io import StringIO

            df = pd.read_csv(StringIO(raw_text))
            df.columns = [str(column).strip().upper() for column in df.columns]
            preferred_columns = [
                "SYMBOL",
                "NSE SYMBOL",
                "TICKER",
                "YAHOO_SYMBOL",
                "YAHOO SYMBOL",
                "NAME",
                "COMPANY",
                "COMPANY NAME",
                "SCREENER",
            ]

            selected_column = next((column for column in preferred_columns if column in df.columns), None)
            if selected_column is None and len(df.columns) > 0:
                selected_column = df.columns[0]

            if selected_column:
                values = df[selected_column].dropna().astype(str).tolist()
                return [value.strip() for value in values if value.strip()][:250]
        except Exception as e:
            print(f"Error parsing uploaded CSV: {e}")

    return parse_symbol_list(raw_text)


@st.cache_data(ttl=900)
def load_stock_lookup(csv_file="indian_stocks.csv"):
    df = pd.read_csv(csv_file)
    df["symbol_clean"] = df["symbol"].astype(str).str.upper().str.replace(".NS", "", regex=False)
    df["yahoo_clean"] = df["yahoo_symbol"].astype(str).str.upper().str.replace(".NS", "", regex=False)
    df["company_clean"] = df["company_name"].map(normalize_lookup_text)
    return df


def resolve_scan_symbols(inputs):
    df = load_stock_lookup()
    resolved = []
    missing = []
    seen = set()

    for value in inputs:
        raw_value = str(value).strip()
        if not raw_value:
            continue

        clean_symbol = raw_value.upper().replace(".NS", "").strip()
        clean_name = normalize_lookup_text(raw_value)
        match = df[(df["symbol_clean"] == clean_symbol) | (df["yahoo_clean"] == clean_symbol)]

        if match.empty and clean_name:
            exact_name_match = df[df["company_clean"] == clean_name]
            if not exact_name_match.empty:
                match = exact_name_match

        if match.empty and clean_name:
            contains_name_match = df[df["company_clean"].str.contains(clean_name, na=False)]
            if contains_name_match.empty:
                contains_name_match = df[df["company_clean"].map(lambda name: clean_name in name or name in clean_name)]
            if not contains_name_match.empty:
                match = contains_name_match

        if match.empty:
            missing.append(raw_value)
            continue

        row = match.iloc[0]
        if row["symbol"] in seen:
            continue
        seen.add(row["symbol"])
        resolved.append(
            {
                "symbol": row["symbol"],
                "company_name": row["company_name"],
                "exchange": row["exchange"],
                "yahoo_symbol": row["yahoo_symbol"],
            }
        )

    return resolved, missing


def detect_macd_change(data):
    if data is None or len(data) < 35:
        return None

    analyzed = calculate_macd(data)
    analyzed = generate_signals(analyzed)
    confirmation = build_signal_confirmation(analyzed)
    if confirmation["confirmed_signal"] not in ("BUY", "SELL"):
        return None

    latest = analyzed.iloc[-1]
    return {
        "signal": confirmation["confirmed_signal"],
        "confirmation_score": confirmation["score"],
        "candle_pattern": confirmation["candle_pattern"],
        "chart_pattern": confirmation["chart_pattern"],
        "confirmation": confirmation["reason"],
        "price": round(float(latest["close"]), 2),
        "macd": round(float(latest["macd"]), 4),
        "signal_line": round(float(latest["signal"]), 4),
        "histogram": round(float(latest["hist"]), 4),
        "date": format_ist_time(latest.name),
    }


def run_macd_scan(records, interval, interval_label):
    results = []
    progress_bar = st.progress(0)
    status = st.empty()
    scan_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST")

    for idx, record in enumerate(records):
        status.caption(f"Scanning {idx + 1}/{len(records)}: {record['symbol']}")
        data = fetch_stock_data(record["yahoo_symbol"], interval)
        macd_change = detect_macd_change(data)
        if macd_change:
            results.append(
                {
                    "symbol": record["symbol"],
                    "company_name": record["company_name"],
                    "exchange": record["exchange"],
                    "yahoo_symbol": record["yahoo_symbol"],
                    "timeframe": interval_label,
                    "scan_time": scan_time,
                    **macd_change,
                }
            )
        progress_bar.progress((idx + 1) / len(records))

    status.empty()
    progress_bar.empty()
    return pd.DataFrame(results)


def tradingview_symbol(record):
    symbol = str(record.get("symbol", "")).strip().upper()
    exchange = str(record.get("exchange", "NSE")).strip().upper()

    index_map = {
        "^NSEI": "NSE:NIFTY",
        "^NSEBANK": "NSE:BANKNIFTY",
        "^BSESN": "BSE:SENSEX",
        "^BSE500": "BSE:BSE500",
        "^CNXIT": "NSE:CNXIT",
        "^CNXAUTO": "NSE:CNXAUTO",
        "^CNXPHARMA": "NSE:CNXPHARMA",
        "^CNXREALTY": "NSE:CNXREALTY",
    }
    if symbol in index_map:
        return index_map[symbol]
    return f"{exchange}:{symbol}" if symbol else "NSE:NIFTY"


def tradingview_external_url(tv_symbol):
    return f"https://www.tradingview.com/chart/?{urlencode({'symbol': tv_symbol})}"


def render_quote_cards(quotes):
    if not quotes:
        st.info("Market snapshot is loading slowly. Try refreshing in a moment.")
        return

    cols = st.columns(min(3, len(quotes)))
    for idx, quote in enumerate(quotes[:6]):
        with cols[idx % len(cols)]:
            direction_class = "metric-delta-positive" if quote["change"] >= 0 else "metric-delta-negative"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{quote['symbol']}</div>
                <div class="metric-value">₹{quote['price']:,.2f}</div>
                <div class="{direction_class}">
                    {quote['change']:+.2f} ({quote['change_pct']:+.2f}%)
                </div>
                <div style="color:#6f8494;font-size:0.72rem;margin-top:10px;">
                    Updated {quote.get('updated_at', 'recently')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_plotly_chart(data, company, symbol, selected_interval_label, trade_setup=None):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.045,
        row_heights=[0.55, 0.20, 0.25],
    )

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="Price",
            increasing_line_color="#27d3a2",
            decreasing_line_color="#ff5b6e",
        ),
        row=1,
        col=1,
    )

    buy_signals = data[data["trade_signal"] == "BUY"]
    sell_signals = data[data["trade_signal"] == "SELL"]
    if not buy_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_signals.index,
                y=buy_signals["close"],
                mode="markers",
                name="BUY",
                marker=dict(color="#27d3a2", size=12, symbol="triangle-up", line=dict(color="#071015", width=1)),
            ),
            row=1,
            col=1,
        )
    if not sell_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_signals.index,
                y=sell_signals["close"],
                mode="markers",
                name="SELL",
                marker=dict(color="#ff5b6e", size=12, symbol="triangle-down", line=dict(color="#071015", width=1)),
            ),
            row=1,
            col=1,
        )

    volume_colors = ["#27d3a2" if close >= open_ else "#ff5b6e" for close, open_ in zip(data["close"], data["open"])]
    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["volume"],
            name="Volume",
            marker_color=volume_colors,
            opacity=0.85,
            marker_line_width=0,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data.index, y=data["macd"], mode="lines", name="MACD", line=dict(color="#3ea7ff", width=2)),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=data["signal"], mode="lines", name="Signal", line=dict(color="#f0b84d", width=2)),
        row=3,
        col=1,
    )
    hist_colors = ["#27d3a2" if x > 0 else "#ff5b6e" for x in data["hist"]]
    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["hist"],
            name="Histogram",
            marker_color=hist_colors,
            opacity=0.9,
            marker_line_width=0,
        ),
        row=3,
        col=1,
    )

    if trade_setup:
        levels = [
            ("Entry", trade_setup.get("entry"), "#27d3a2"),
            ("Stop Loss", trade_setup.get("stop_loss"), "#ff5b6e"),
            ("Target 1", trade_setup.get("target_1"), "#f0b84d"),
            ("Target 2", trade_setup.get("target_2"), "#3ea7ff"),
            ("Exit Ref", trade_setup.get("exit_price"), "#9fb0bf"),
        ]
        for label, value, color in levels:
            if value:
                fig.add_hline(
                    y=value,
                    line_width=1,
                    line_dash="dot",
                    line_color=color,
                    annotation_text=label,
                    annotation_position="right",
                    row=1,
                    col=1,
                )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,16,21,0.72)",
        height=880,
        margin=dict(l=20, r=20, t=28, b=72),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=-0.08,
            x=0,
            bgcolor="rgba(7,16,21,0)",
            font=dict(size=12),
        ),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text="Price", gridcolor="rgba(255,255,255,0.08)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", gridcolor="rgba(255,255,255,0.08)", row=2, col=1)
    fig.update_yaxes(title_text="MACD", gridcolor="rgba(255,255,255,0.08)", zeroline=True, zerolinecolor="rgba(255,255,255,0.25)", row=3, col=1)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


@st.cache_data(ttl=1)
def cached_market_snapshot():
    return fetch_quote_snapshot(MARKET_SYMBOLS)


def render_market_overview_header(live_mode=False):
    st.markdown('<div class="section-title">Market Overview</div>', unsafe_allow_html=True)
    if live_mode:
        st.caption("Broker-style live mode: refreshing every 1 second. Price changes depend on the data feed.")


@st.fragment(run_every=1)
def render_live_market_overview():
    cached_market_snapshot.clear()
    render_market_overview_header(live_mode=True)
    render_quote_cards(cached_market_snapshot())


@st.cache_data(ttl=900)
def cached_news(yahoo_symbol):
    return fetch_stock_news(yahoo_symbol)


@st.cache_data(ttl=1800)
def cached_fundamentals(yahoo_symbol):
    return fetch_fundamental_snapshot(yahoo_symbol)


if "selected_record" not in st.session_state:
    st.session_state.selected_record = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "scan_history" not in st.session_state:
    st.session_state.scan_history = pd.DataFrame()
if st.session_state.selected_record is None:
    default_matches = search_companies("RELIANCE", "indian_stocks.csv", 1)
    if default_matches:
        st.session_state.selected_record = default_matches[0]


with st.sidebar:
    st.markdown("### MarketDesk India")
    st.caption("NSE scanner, MACD engine, market charting")

    st.markdown("#### Quick Load")
    quick_cols = st.columns(2)
    quick_symbols = ["NIFTY 50", "NIFTY BANK", "RELIANCE", "TCS", "HDFCBANK", "INFY"]
    for idx, quick_symbol in enumerate(quick_symbols):
        with quick_cols[idx % 2]:
            if st.button(quick_symbol, width="stretch", key=f"quick_{quick_symbol}"):
                matches = search_companies(quick_symbol, "indian_stocks.csv", 1)
                if matches:
                    st.session_state.selected_record = matches[0]
                    st.session_state.data = None
                    st.rerun()

    st.session_state.search_query = st.text_input(
        "Search stock",
        value=st.session_state.search_query,
        placeholder="RELIANCE, TCS, NIFTY",
    )

    suggestions = search_companies(st.session_state.search_query, "indian_stocks.csv", 25) if st.session_state.search_query else []
    if suggestions:
        selected_index = st.selectbox(
            "Matches",
            range(len(suggestions)),
            format_func=lambda i: f"{suggestions[i]['symbol']} - {suggestions[i]['company_name']}",
        )
        if st.button("Load Market", width="stretch", type="primary"):
            st.session_state.selected_record = suggestions[selected_index]
            st.session_state.data = None
            st.rerun()
    elif st.session_state.search_query:
        st.warning("No matching symbol found.")

    if st.button("Clear", width="stretch"):
        st.session_state.search_query = ""
        st.session_state.selected_record = None
        st.session_state.data = None
        st.rerun()

    st.divider()
    st.markdown("### Live Market")
    auto_refresh_market = st.toggle("1-sec live prices", value=False)
    if st.button("Refresh Prices", width="stretch"):
        cached_market_snapshot.clear()
        st.rerun()

    if auto_refresh_market:
        st.caption("Market Overview refreshes every second.")

    st.divider()
    selected_interval_label = st.selectbox("Timeframe", list(INTERVAL_OPTIONS.keys()), index=2)
    selected_interval = INTERVAL_OPTIONS[selected_interval_label]

    if st.session_state.selected_record:
        st.markdown("### Active Symbol")
        active = st.session_state.selected_record
        st.markdown(f"**{active['symbol']}**")
        st.caption(active["company_name"])
        fetch_button = st.button("Run Analysis", width="stretch", type="primary")
    else:
        fetch_button = False


st.markdown(
    """
    <div class="terminal-hero">
        <div class="kicker">Indian equity intelligence terminal</div>
        <div class="hero-title">MarketDesk India</div>
        <div class="hero-subtitle">
            Clean NSE discovery, live charting, MACD signal analysis, trade review, and stock news in one focused workspace.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


if auto_refresh_market:
    render_live_market_overview()
else:
    render_market_overview_header()
    render_quote_cards(cached_market_snapshot())

with st.expander("MACD Signal Scanner - paste up to 250 stocks", expanded=True):
    scan_left, scan_right = st.columns([1.25, 0.75])
    with scan_left:
        scan_text = st.text_area(
            "Stock symbols",
            placeholder="RELIANCE, TCS, INFY, HDFCBANK, SBIN\nPaste up to 250 NSE symbols here",
            height=150,
        )
        uploaded_symbols = st.file_uploader("Or upload CSV/TXT with stock symbols", type=["csv", "txt"])
    with scan_right:
        scan_interval_label = st.selectbox(
            "Scan timeframe",
            list(INTERVAL_OPTIONS.keys()),
            index=2,
            key="scanner_interval",
        )
        scan_only_message = st.caption(
            "Scanner returns only MACD crosses confirmed by candle pattern, chart pattern, trend, or volume."
        )
        scan_button = st.button("Scan MACD Changes", width="stretch", type="primary")

    pasted_symbols = parse_symbol_list(scan_text)
    uploaded_values = parse_uploaded_stock_file(uploaded_symbols)
    combined_symbols = (pasted_symbols + uploaded_values)[:250]
    if combined_symbols:
        matched_preview, missing_preview = resolve_scan_symbols(combined_symbols)
        st.caption(f"{len(combined_symbols)} rows ready. Matched {len(matched_preview)} stock(s).")
        if missing_preview:
            st.caption(f"Unmatched preview: {', '.join(missing_preview[:6])}")

    if scan_button:
        if not combined_symbols:
            st.warning("Paste or upload at least one stock symbol.")
        else:
            records, missing_symbols = resolve_scan_symbols(combined_symbols)
            if missing_symbols:
                st.warning(f"Could not match {len(missing_symbols)} symbol(s): {', '.join(missing_symbols[:12])}")

            if records:
                new_results = run_macd_scan(records, INTERVAL_OPTIONS[scan_interval_label], scan_interval_label)
                st.session_state.scan_results = new_results
                if not new_results.empty:
                    st.session_state.scan_history = pd.concat(
                        [new_results, st.session_state.scan_history],
                        ignore_index=True,
                    )
                st.session_state.scan_interval_label = scan_interval_label
            else:
                st.session_state.scan_results = pd.DataFrame()

    if "scan_results" in st.session_state:
        results = st.session_state.scan_results
        if results.empty:
            st.info("No latest MACD crossover found in this list.")
        else:
            st.success(f"Found {len(results)} MACD crossover stock(s).")
            display_results = results[
                [
                    "signal",
                    "symbol",
                    "company_name",
                    "timeframe",
                    "price",
                    "confirmation_score",
                    "candle_pattern",
                    "chart_pattern",
                    "confirmation",
                    "date",
                ]
            ].copy()
            display_results.index = range(1, len(display_results) + 1)
            st.dataframe(display_results, width="stretch", height=320)

            result_options = results.to_dict("records")
            selected_scan_index = st.selectbox(
                "Open scanned stock",
                range(len(result_options)),
                format_func=lambda i: f"{result_options[i]['signal']} - {result_options[i]['symbol']} - {result_options[i]['company_name']}",
            )
            if st.button("Open Selected Signal", width="stretch"):
                selected_scan = result_options[selected_scan_index]
                st.session_state.selected_record = {
                    "symbol": selected_scan["symbol"],
                    "company_name": selected_scan["company_name"],
                    "exchange": selected_scan["exchange"],
                    "yahoo_symbol": selected_scan["yahoo_symbol"],
                }
                st.session_state.data = None
                st.rerun()

    if not st.session_state.scan_history.empty:
        st.markdown('<div class="section-title">Previous Scan Results</div>', unsafe_allow_html=True)
        history_display = st.session_state.scan_history[
            [
                "signal",
                "symbol",
                "company_name",
                "timeframe",
                "price",
                "confirmation_score",
                "candle_pattern",
                "chart_pattern",
                "scan_time",
                "date",
            ]
        ].copy()
        history_display.index = range(1, len(history_display) + 1)
        st.dataframe(history_display, width="stretch", height=360)


if st.session_state.selected_record and fetch_button:
    selected_record = st.session_state.selected_record
    yahoo_symbol = selected_record["yahoo_symbol"]
    with st.spinner("Loading price data and signal model..."):
        data = fetch_stock_data(yahoo_symbol, selected_interval)
        if data is not None and len(data) > 0:
            data = calculate_macd(data)
            data = generate_signals(data)
            data = apply_confirmed_signals(data)
            st.session_state.data = data
            st.session_state.company = selected_record["company_name"]
            st.session_state.symbol = yahoo_symbol
            st.session_state.interval = selected_interval_label
            st.session_state.interval_value = selected_interval
        else:
            st.error(f"Could not fetch data for {yahoo_symbol}. Try a higher timeframe.")

if st.session_state.selected_record and (
    "data" not in st.session_state
    or st.session_state.data is None
    or st.session_state.get("symbol") != st.session_state.selected_record["yahoo_symbol"]
):
    selected_record = st.session_state.selected_record
    yahoo_symbol = selected_record["yahoo_symbol"]
    with st.spinner("Preparing default analysis..."):
        data = fetch_stock_data(yahoo_symbol, selected_interval)
        if data is not None and len(data) > 0:
            data = calculate_macd(data)
            data = generate_signals(data)
            data = apply_confirmed_signals(data)
            st.session_state.data = data
            st.session_state.company = selected_record["company_name"]
            st.session_state.symbol = yahoo_symbol
            st.session_state.interval = selected_interval_label
            st.session_state.interval_value = selected_interval


if st.session_state.selected_record:
    selected_record = st.session_state.selected_record
    yahoo_symbol = selected_record["yahoo_symbol"]
    tv_symbol = tradingview_symbol(selected_record)

    top_left, top_right = st.columns([1.45, 0.9])
    with top_left:
        st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Price Chart</div>', unsafe_allow_html=True)
        if "data" in st.session_state and st.session_state.data is not None:
            chart_data = st.session_state.data
            chart_company = st.session_state.get("company", selected_record["company_name"])
            chart_symbol = st.session_state.get("symbol", yahoo_symbol)
            chart_interval = st.session_state.get("interval", selected_interval_label)
            chart_setup = build_trade_setup(chart_data)
            st.markdown(
                f"""
                <div style="margin: 2px 0 14px 0;">
                    <span style="font-size:1.02rem;font-weight:760;color:#edf5f7;">{chart_company}</span>
                    <span style="font-size:0.94rem;color:#9fb0bf;margin-left:8px;">{chart_symbol} | {chart_interval}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                build_plotly_chart(chart_data, chart_company, chart_symbol, chart_interval, chart_setup),
                width="stretch",
            )
            st.markdown(
                f'<a href="{tradingview_external_url(tv_symbol)}" target="_blank" '
                'style="color:#27d3a2;text-decoration:none;font-weight:700;">Open this symbol on TradingView</a>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Chart data is loading. If it takes too long, click Run Analysis.")

    with top_right:
        st.markdown('<div class="section-title">Stock News</div>', unsafe_allow_html=True)
        news = cached_news(yahoo_symbol)
        if news:
            for item in news[:6]:
                title = item["title"]
                source = item["publisher"]
                summary = item["summary"][:180]
                link = item["link"]
                title_html = f'<a href="{link}" target="_blank" style="color:#f4fbfc;text-decoration:none;">{title}</a>' if link else title
                st.markdown(
                    f"""
                    <div class="news-item">
                        <div class="news-source">{source}</div>
                        <div class="news-title">{title_html}</div>
                        <div class="news-summary">{summary}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recent news returned for this symbol.")


if "data" in st.session_state and st.session_state.data is not None:
    data = st.session_state.data
    company = st.session_state.company
    symbol = st.session_state.symbol
    selected_interval_label = st.session_state.get("interval", "1 Day")
    latest = get_latest_signal(data)
    trade_setup = build_trade_setup(data)
    fundamentals = cached_fundamentals(symbol)
    investment_read = build_investment_read(data, fundamentals)

    if latest:
        signal_text = "BUY" if latest["signal"] == "BUY" else "SELL" if latest["signal"] == "SELL" else "NEUTRAL"
        latest_row = data.iloc[-1]
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Signal", signal_text)
        col2.metric("Last Price", f"₹{latest['price']:.2f}")
        col3.metric("MACD", f"{latest['macd']:.4f}")
        col4.metric("Signal Line", f"{latest['signal_line']:.4f}")
        col5.metric("Histogram", f"{latest['histogram']:.4f}")
        st.markdown(
            f"""
            <div class="setup-card" style="margin: 10px 0 12px 0;">
                <div class="analysis-row"><span class="analysis-label">Confirmed By</span><span class="analysis-value">{latest_row.get('confirmation_reason', 'No confirmation available')}</span></div>
                <div class="analysis-row"><span class="analysis-label">Candlestick Pattern</span><span class="analysis-value">{latest_row.get('candle_pattern', 'N/A')}</span></div>
                <div class="analysis-row"><span class="analysis-label">Chart Pattern</span><span class="analysis-value">{latest_row.get('chart_pattern', 'N/A')}</span></div>
                <div class="analysis-row"><span class="analysis-label">Confirmation Score</span><span class="analysis-value">{int(latest_row.get('confirmation_score', 0))}/4</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    setup_col, investment_col = st.columns([1, 1])
    with setup_col:
        st.markdown('<div class="section-title">Trade Setup</div>', unsafe_allow_html=True)
        entry_text = f"₹{trade_setup['entry']:.2f}" if trade_setup["entry"] else "Wait"
        stop_text = f"₹{trade_setup['stop_loss']:.2f}" if trade_setup["stop_loss"] else "N/A"
        target_1_text = f"₹{trade_setup['target_1']:.2f}" if trade_setup["target_1"] else "N/A"
        target_2_text = f"₹{trade_setup['target_2']:.2f}" if trade_setup["target_2"] else "N/A"
        exit_text = f"₹{trade_setup['exit_price']:.2f}" if trade_setup["exit_price"] else "N/A"
        rr_text = f"1:{trade_setup['risk_reward']:.2f}" if trade_setup["risk_reward"] else "N/A"
        st.markdown(
            f"""
            <div class="setup-card">
                <div class="{trade_setup['action_class']}">{trade_setup['action']}</div>
                <div class="analysis-row"><span class="analysis-label">Entry Price</span><span class="analysis-value">{entry_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Stop Loss</span><span class="analysis-value">{stop_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Target / Exit 1</span><span class="analysis-value">{target_1_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Target 2</span><span class="analysis-value">{target_2_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Exit Reference</span><span class="analysis-value">{exit_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Risk : Reward</span><span class="analysis-value">{rr_text}</span></div>
                <div class="setup-note">{trade_setup['note']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with investment_col:
        st.markdown('<div class="section-title">Basic Investment Read</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="setup-card">
                <div class="setup-action-wait">{investment_read['verdict']}</div>
                <div class="analysis-row"><span class="analysis-label">Overall Score</span><span class="analysis-value">{investment_read['total_score']}</span></div>
                <div class="analysis-row"><span class="analysis-label">Technical Score</span><span class="analysis-value">{investment_read['technical_score']}</span></div>
                <div class="analysis-row"><span class="analysis-label">Fundamental Score</span><span class="analysis-value">{investment_read['fundamental_score']}</span></div>
                <div class="analysis-row"><span class="analysis-label">RSI</span><span class="analysis-value">{investment_read['rsi']:.2f}</span></div>
                <div class="analysis-row"><span class="analysis-label">ATR</span><span class="analysis-value">₹{trade_setup['atr']:.2f}</span></div>
                <div class="setup-note">Educational analysis only. Always confirm with your own research before investing.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    fund_col, tech_col = st.columns([1, 1])
    with fund_col:
        st.markdown('<div class="section-title">Fundamental Snapshot</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="setup-card">
                <div class="analysis-row"><span class="analysis-label">Market Cap</span><span class="analysis-value">{format_large_number(fundamentals.get('market_cap'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Trailing PE</span><span class="analysis-value">{format_ratio(fundamentals.get('trailing_pe'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Forward PE</span><span class="analysis-value">{format_ratio(fundamentals.get('forward_pe'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Price / Book</span><span class="analysis-value">{format_ratio(fundamentals.get('price_to_book'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">ROE</span><span class="analysis-value">{format_percent(fundamentals.get('return_on_equity'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Profit Margin</span><span class="analysis-value">{format_percent(fundamentals.get('profit_margins'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Debt / Equity</span><span class="analysis-value">{format_ratio(fundamentals.get('debt_to_equity'))}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tech_col:
        latest_close = float(data["close"].iloc[-1])
        ema_fast = float(data["ema_fast"].iloc[-1])
        ema_slow = float(data["ema_slow"].iloc[-1])
        trend = "Bullish" if latest_close > ema_fast > ema_slow else "Weak / Sideways" if latest_close > ema_slow else "Bearish"
        momentum = "Positive" if float(data["macd"].iloc[-1]) > float(data["signal"].iloc[-1]) else "Negative"
        volume_avg = float(data["volume"].tail(20).mean()) if "volume" in data else 0
        volume_state = "Above average" if float(data["volume"].iloc[-1]) > volume_avg else "Below average"
        rsi_value = calculate_rsi(data["close"]).dropna()
        rsi_text = f"{float(rsi_value.iloc[-1]):.2f}" if not rsi_value.empty else "N/A"
        support = float(data["low"].tail(20).min())
        resistance = float(data["high"].tail(20).max())
        st.markdown('<div class="section-title">Technical Snapshot</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="setup-card">
                <div class="analysis-row"><span class="analysis-label">Trend</span><span class="analysis-value">{trend}</span></div>
                <div class="analysis-row"><span class="analysis-label">Momentum</span><span class="analysis-value">{momentum}</span></div>
                <div class="analysis-row"><span class="analysis-label">RSI</span><span class="analysis-value">{rsi_text}</span></div>
                <div class="analysis-row"><span class="analysis-label">Support / Resistance</span><span class="analysis-value">₹{support:.2f} / ₹{resistance:.2f}</span></div>
                <div class="analysis-row"><span class="analysis-label">Volume</span><span class="analysis-value">{volume_state}</span></div>
                <div class="analysis-row"><span class="analysis-label">52W Low / High</span><span class="analysis-value">{format_ratio(fundamentals.get('fifty_two_week_low'))} / {format_ratio(fundamentals.get('fifty_two_week_high'))}</span></div>
                <div class="analysis-row"><span class="analysis-label">Sector</span><span class="analysis-value">{fundamentals.get('sector') or 'N/A'}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    signals_col, backtest_col = st.columns([1.05, 0.95])
    with signals_col:
        st.markdown('<div class="section-title">Recent Signals</div>', unsafe_allow_html=True)
        signals_table = get_last_n_signals(data, 20)
        if signals_table is not None:
            signals_table.index = range(1, len(signals_table) + 1)
            st.dataframe(signals_table, width="stretch", height=360)
        else:
            st.info("No signals generated.")

    with backtest_col:
        st.markdown('<div class="section-title">Backtest Summary</div>', unsafe_allow_html=True)
        backtest_result = backtest_signals(data)
        if backtest_result:
            m1, m2, m3 = st.columns(3)
            m1.metric("Trades", backtest_result["total_trades"])
            m2.metric("Win Rate", f"{backtest_result.get('win_rate', 0):.2f}%")
            m3.metric("Total P/L", f"₹{backtest_result.get('total_profit_loss', 0):.2f}")

            trade_history = get_trade_history(data)
            if trade_history is not None:
                trade_history.index = range(1, len(trade_history) + 1)
                st.dataframe(trade_history, width="stretch", height=242)
            else:
                st.info("No completed BUY to SELL cycles in this period.")
else:
    if not st.session_state.selected_record:
        st.markdown('<div class="section-title">Watchlist Pulse</div>', unsafe_allow_html=True)
        quotes = cached_market_snapshot()
        if quotes:
            for quote in quotes:
                cls = "metric-delta-positive" if quote["change"] >= 0 else "metric-delta-negative"
                st.markdown(
                    f"""
                    <div class="watch-row">
                        <span class="watch-symbol">{quote['symbol']}</span>
                        <span class="watch-price">₹{quote['price']:,.2f}</span>
                        <span class="{cls}">{quote['change_pct']:+.2f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
