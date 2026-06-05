import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import requests

try:
    import streamlit as st
except Exception:
    st = None

try:
    import pyotp
    from SmartApi import SmartConnect
except Exception:
    pyotp = None
    SmartConnect = None


ANGEL_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
_ANGEL_CLIENT = None


def _get_secret(section, key, env_name=None):
    if st is not None:
        try:
            value = st.secrets.get(section, {}).get(key)
            if value:
                return str(value)
        except Exception:
            pass
    return os.getenv(env_name or f"{section}_{key}".upper())


def get_data_provider_status():
    """Return the active/available market data provider status."""
    config = _get_angel_config()
    if not config["ready"]:
        return "Yahoo Finance fallback"
    if SmartConnect is None or pyotp is None:
        return "Yahoo Finance fallback (install smartapi-python + pyotp)"
    return "Angel One SmartAPI"


def _get_angel_config():
    config = {
        "api_key": _get_secret("angel_one", "api_key", "ANGEL_ONE_API_KEY"),
        "client_code": _get_secret("angel_one", "client_code", "ANGEL_ONE_CLIENT_CODE"),
        "password": _get_secret("angel_one", "password", "ANGEL_ONE_PASSWORD"),
        "totp_secret": _get_secret("angel_one", "totp_secret", "ANGEL_ONE_TOTP_SECRET"),
    }
    config["ready"] = all(config.values())
    return config


def _get_angel_client():
    global _ANGEL_CLIENT
    config = _get_angel_config()
    if not config["ready"] or SmartConnect is None or pyotp is None:
        return None

    if _ANGEL_CLIENT is not None:
        return _ANGEL_CLIENT

    try:
        client = SmartConnect(api_key=config["api_key"])
        totp = pyotp.TOTP(config["totp_secret"]).now()
        session = client.generateSession(config["client_code"], config["password"], totp)
        if not session or not session.get("status"):
            print(f"Angel One login failed: {session}")
            return None
        _ANGEL_CLIENT = client
        return _ANGEL_CLIENT
    except Exception as e:
        print(f"Angel One login error: {e}")
        return None


@lru_cache(maxsize=1)
def _load_angel_instruments():
    response = requests.get(ANGEL_MASTER_URL, timeout=30)
    response.raise_for_status()
    instruments = pd.DataFrame(response.json())
    instruments["name_clean"] = instruments["name"].astype(str).str.upper()
    instruments["symbol_clean"] = instruments["symbol"].astype(str).str.upper()
    return instruments


def _base_symbol(yahoo_symbol):
    symbol = str(yahoo_symbol).upper().strip()
    if symbol.startswith("^"):
        return symbol
    return symbol.replace(".NS", "").replace(".BO", "")


def _find_angel_instrument(yahoo_symbol):
    symbol = _base_symbol(yahoo_symbol)
    if symbol.startswith("^"):
        return None

    try:
        instruments = _load_angel_instruments()
        nse = instruments[instruments["exch_seg"].eq("NSE")].copy()
        exact_symbol = nse[nse["symbol_clean"].eq(f"{symbol}-EQ")]
        if not exact_symbol.empty:
            row = exact_symbol.iloc[0]
        else:
            exact_name = nse[nse["name_clean"].eq(symbol)]
            if exact_name.empty:
                return None
            row = exact_name.iloc[0]

        return {
            "exchange": row["exch_seg"],
            "tradingsymbol": row["symbol"],
            "symboltoken": str(row["token"]),
        }
    except Exception as e:
        print(f"Angel One instrument lookup failed for {yahoo_symbol}: {e}")
        return None


def _angel_interval(interval):
    interval_map = {
        "1m": "ONE_MINUTE",
        "5m": "FIVE_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "4h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }
    return interval_map.get(interval)


def _angel_period_days(interval):
    return {
        "1m": 5,
        "5m": 30,
        "15m": 60,
        "30m": 60,
        "1h": 120,
        "4h": 120,
        "1d": 730,
    }.get(interval, 30)


def _resample_4h(data):
    return data.resample("4h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()


def _fetch_angel_stock_data(yahoo_symbol, interval):
    client = _get_angel_client()
    instrument = _find_angel_instrument(yahoo_symbol)
    candle_interval = _angel_interval(interval)
    if client is None or instrument is None or candle_interval is None:
        return None

    try:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        start = now - timedelta(days=_angel_period_days(interval))
        params = {
            "exchange": instrument["exchange"],
            "symboltoken": instrument["symboltoken"],
            "interval": candle_interval,
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": now.strftime("%Y-%m-%d %H:%M"),
        }
        response = client.getCandleData(params)
        candles = response.get("data") if isinstance(response, dict) else None
        if not candles:
            return None

        data = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume"])
        data["datetime"] = pd.to_datetime(data["datetime"])
        data = data.set_index("datetime")
        for column in ["open", "high", "low", "close", "volume"]:
            data[column] = pd.to_numeric(data[column], errors="coerce")
        data = data.dropna(subset=["open", "high", "low", "close"])
        if interval == "4h":
            data = _resample_4h(data)
        return data
    except Exception as e:
        print(f"Angel One candle fetch failed for {yahoo_symbol}: {e}")
        return None


def _fetch_angel_quote(yahoo_symbol):
    client = _get_angel_client()
    instrument = _find_angel_instrument(yahoo_symbol)
    if client is None or instrument is None:
        return None

    try:
        response = client.ltpData(
            instrument["exchange"],
            instrument["tradingsymbol"],
            instrument["symboltoken"],
        )
        payload = response.get("data") if isinstance(response, dict) else None
        if not payload:
            return None

        price = float(payload.get("ltp", 0))
        previous_close = float(payload.get("close", price) or price)
        change = price - previous_close
        change_pct = (change / previous_close * 100) if previous_close else 0
        return {
            "symbol": yahoo_symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(payload.get("tradeVolume", 0) or 0),
            "updated_at": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST"),
        }
    except Exception as e:
        print(f"Angel One quote fetch failed for {yahoo_symbol}: {e}")
        return None

def fetch_stock_data(yahoo_symbol, interval):
    """
    Fetch OHLC data for the stock using a specific interval.

    Args:
        yahoo_symbol: Yahoo format symbol (e.g., RELIANCE.NS)
        interval: interval string for yfinance (1m, 5m, 15m, 30m, 1d)

    Returns:
        DataFrame with OHLC data or None if failed
    """
    period_map = {
        '1m': '7d',
        '5m': '30d',
        '15m': '60d',
        '30m': '60d',
        '1h': '730d',
        '4h': '730d',
        '1d': '2y'
    }
    period = period_map.get(interval, '30d')
    download_interval = '1h' if interval == '4h' else interval

    try:
        angel_data = _fetch_angel_stock_data(yahoo_symbol, interval)
        if angel_data is not None and not angel_data.empty:
            return angel_data

        data = yf.download(yahoo_symbol, period=period, interval=download_interval, progress=False)

        if data.empty:
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period, interval=download_interval)

        if data.empty:
            return None

        def _col_to_str(col):
            # Handle multi-index column names returned by yfinance
            try:
                if isinstance(col, tuple):
                    parts = [str(c) for c in col if c is not None and str(c) != '']
                    name = '_'.join(parts)
                else:
                    name = str(col)
            except Exception:
                name = str(col)
            return name.lower()

        data.columns = [_col_to_str(c) for c in data.columns]

        # Normalize common column name variations to single names
        col_map = {}
        cols = list(data.columns)
        for c in cols:
            if 'open' == c or c.endswith('_open') or c == 'o' or 'open' in c:
                col_map[c] = 'open'
            elif 'high' == c or c.endswith('_high') or 'high' in c:
                col_map[c] = 'high'
            elif 'low' == c or c.endswith('_low') or 'low' in c:
                col_map[c] = 'low'
            elif c == 'close' or 'close' in c:
                col_map[c] = 'close'
            elif 'volume' in c:
                col_map[c] = 'volume'
            elif 'adj' in c and 'close' in c:
                col_map[c] = 'adj_close'

        if col_map:
            data = data.rename(columns=col_map)

        if interval == '4h':
            data = _resample_4h(data)
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def load_indian_stocks(csv_file='indian_stocks.csv'):
    """
    Load Indian stocks from CSV file
    
    Returns:
        DataFrame with stock information
    """
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        print(f"Error loading stocks CSV: {e}")
        return None

def search_companies(query, csv_file='indian_stocks.csv', max_results=100):
    """
    Search Indian company names and symbols from the CSV database.

    Returns:
        List of matching records with company_name, exchange, symbol, yahoo_symbol
    """
    try:
        if not query:
            return []

        df = pd.read_csv(csv_file)
        query_normalized = str(query).strip().lower()
        mask = (
            df['company_name'].str.contains(query, case=False, na=False) |
            df['symbol'].str.contains(query, case=False, na=False)
        )
        results = df[mask].drop_duplicates(['company_name', 'exchange', 'symbol']).copy()
        results['_exact_symbol'] = results['symbol'].str.lower().eq(query_normalized)
        results['_symbol_starts'] = results['symbol'].str.lower().str.startswith(query_normalized)
        results['_company_starts'] = results['company_name'].str.lower().str.startswith(query_normalized)
        results = results.sort_values(
            by=['_exact_symbol', '_symbol_starts', '_company_starts', 'type', 'symbol'],
            ascending=[False, False, False, True, True]
        )
        results = results.drop(columns=['_exact_symbol', '_symbol_starts', '_company_starts'])
        return results.head(max_results).to_dict('records')
    except Exception as e:
        print(f"Error searching companies: {e}")
        return []

def get_company_suggestions(csv_file='indian_stocks.csv'):
    """
    Get list of unique company names for search.
    """
    try:
        df = pd.read_csv(csv_file)
        return sorted(df['company_name'].unique().tolist())
    except Exception as e:
        print(f"Error loading company names: {e}")
        return []

def get_yahoo_symbol(company_name, csv_file='indian_stocks.csv'):
    """
    Get yahoo_symbol for a company name
    
    Returns:
        yahoo_symbol string or None
    """
    try:
        df = pd.read_csv(csv_file)
        result = df[df['company_name'] == company_name]
        if not result.empty:
            return result.iloc[0]['yahoo_symbol']
    except Exception as e:
        print(f"Error getting yahoo symbol: {e}")
    
    return None

def fetch_quote_snapshot(yahoo_symbols):
    """
    Fetch latest quote snapshots for a small list of Yahoo Finance symbols.
    """
    snapshots = []

    for yahoo_symbol in yahoo_symbols:
        try:
            angel_quote = _fetch_angel_quote(yahoo_symbol)
            if angel_quote:
                snapshots.append(angel_quote)
                continue

            ticker = yf.Ticker(yahoo_symbol)
            intraday = ticker.history(period='1d', interval='1m')
            daily = ticker.history(period='5d', interval='1d')

            if intraday.empty and daily.empty:
                continue

            latest_source = intraday if not intraday.empty else daily
            latest = latest_source.iloc[-1]
            latest_time = latest_source.index[-1]
            previous_close = daily['Close'].iloc[-2] if len(daily) > 1 else latest['Close']
            change = float(latest['Close']) - float(previous_close)
            change_pct = (change / previous_close * 100) if previous_close else 0

            snapshots.append({
                'symbol': yahoo_symbol,
                'price': round(float(latest['Close']), 2),
                'change': round(float(change), 2),
                'change_pct': round(float(change_pct), 2),
                'volume': int(latest['Volume']) if 'Volume' in latest and pd.notna(latest['Volume']) else 0,
                'updated_at': latest_time.strftime('%Y-%m-%d %H:%M IST') if hasattr(latest_time, 'strftime') else str(latest_time)
            })
        except Exception as e:
            print(f"Error fetching quote snapshot for {yahoo_symbol}: {e}")

    return snapshots

def fetch_stock_news(yahoo_symbol, max_items=6):
    """
    Fetch recent Yahoo Finance news for a stock or index.
    """
    try:
        ticker = yf.Ticker(yahoo_symbol)
        news_items = getattr(ticker, 'news', []) or []
        cleaned_news = []

        for item in news_items[:max_items]:
            content = item.get('content', item) if isinstance(item, dict) else {}
            title = content.get('title') or item.get('title')
            publisher = content.get('provider', {}).get('displayName') if isinstance(content.get('provider'), dict) else item.get('publisher')
            link = content.get('canonicalUrl', {}).get('url') if isinstance(content.get('canonicalUrl'), dict) else item.get('link')
            summary = content.get('summary') or ''

            if title:
                cleaned_news.append({
                    'title': title,
                    'publisher': publisher or 'Market news',
                    'link': link or '',
                    'summary': summary
                })

        return cleaned_news
    except Exception as e:
        print(f"Error fetching news for {yahoo_symbol}: {e}")
        return []

def fetch_fundamental_snapshot(yahoo_symbol):
    """
    Fetch a compact fundamental snapshot from Yahoo Finance.
    """
    try:
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info or {}

        return {
            'market_cap': info.get('marketCap'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'price_to_book': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'profit_margins': info.get('profitMargins'),
            'return_on_equity': info.get('returnOnEquity'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'debt_to_equity': info.get('debtToEquity'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'long_name': info.get('longName') or info.get('shortName'),
            'currency': info.get('currency', 'INR'),
        }
    except Exception as e:
        print(f"Error fetching fundamentals for {yahoo_symbol}: {e}")
        return {}
