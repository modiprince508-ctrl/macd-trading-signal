import yfinance as yf
import pandas as pd

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
        '1d': '2y'
    }
    period = period_map.get(interval, '30d')

    try:
        data = yf.download(yahoo_symbol, period=period, interval=interval, progress=False)

        if data.empty:
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period, interval=interval)

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
            ticker = yf.Ticker(yahoo_symbol)
            history = ticker.history(period='5d', interval='1d')
            if history.empty:
                continue

            latest = history.iloc[-1]
            previous_close = history['Close'].iloc[-2] if len(history) > 1 else latest['Close']
            change = latest['Close'] - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0

            snapshots.append({
                'symbol': yahoo_symbol,
                'price': round(float(latest['Close']), 2),
                'change': round(float(change), 2),
                'change_pct': round(float(change_pct), 2),
                'volume': int(latest['Volume']) if 'Volume' in latest and pd.notna(latest['Volume']) else 0
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
