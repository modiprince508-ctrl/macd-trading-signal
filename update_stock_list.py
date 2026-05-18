#!/usr/bin/env python3
"""
Update indian_stocks.csv with NSE-listed Indian equities and major indices.

The Streamlit app expects:
symbol, company_name, exchange, sector, type, yahoo_symbol
"""
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


OUTPUT_CSV = "indian_stocks.csv"
NSE_EQUITY_CSV_URLS = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/market-data/securities-available-for-trading",
}


def clean_text(value):
    """Return a clean string for CSV output."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def yahoo_nse_symbol(symbol):
    """Convert an NSE symbol to Yahoo Finance format."""
    symbol = clean_text(symbol).upper()
    return f"{symbol}.NS" if symbol else ""


def fetch_csv_text(url):
    """Download CSV text from a URL."""
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_nse_stocks():
    """
    Fetch all NSE equity symbols from NSE's official equity list CSV.

    NSE's CSV has columns like SYMBOL, NAME OF COMPANY, SERIES, and ISIN NUMBER.
    We keep normal listed equity rows and generate Yahoo Finance .NS tickers.
    """
    last_error = None

    for url in NSE_EQUITY_CSV_URLS:
        try:
            print(f"Fetching NSE equity list from {url} ...")
            csv_text = fetch_csv_text(url)
            source_df = pd.read_csv(StringIO(csv_text))
            source_df.columns = [str(col).strip().upper() for col in source_df.columns]

            required_columns = {"SYMBOL", "NAME OF COMPANY"}
            missing_columns = required_columns - set(source_df.columns)
            if missing_columns:
                raise ValueError(f"Missing NSE columns: {sorted(missing_columns)}")

            if "SERIES" in source_df.columns:
                source_df = source_df[source_df["SERIES"].astype(str).str.strip().eq("EQ")]

            stocks = []
            for _, row in source_df.iterrows():
                symbol = clean_text(row.get("SYMBOL")).upper()
                company_name = clean_text(row.get("NAME OF COMPANY"))
                isin = clean_text(row.get("ISIN NUMBER"))

                if not symbol or not company_name:
                    continue

                stocks.append(
                    {
                        "symbol": symbol,
                        "company_name": company_name,
                        "exchange": "NSE",
                        "sector": "Equity",
                        "type": "STOCK",
                        "yahoo_symbol": yahoo_nse_symbol(symbol),
                        "isin": isin,
                    }
                )

            if stocks:
                return stocks

            raise ValueError("NSE CSV was downloaded, but no EQ stock rows were found")
        except Exception as exc:
            last_error = exc
            print(f"Failed from {url}: {exc}")

    print(f"Error fetching NSE stocks: {last_error}")
    return []


def fetch_indian_indices():
    """Return widely used Indian market indices supported by Yahoo Finance."""
    indices = [
        ("^NSEI", "NIFTY 50", "NSE"),
        ("^NSEBANK", "NIFTY BANK", "NSE"),
        ("^CNXIT", "NIFTY IT", "NSE"),
        ("^CNXAUTO", "NIFTY AUTO", "NSE"),
        ("^CNXPHARMA", "NIFTY PHARMA", "NSE"),
        ("^CNXREALTY", "NIFTY REALTY", "NSE"),
        ("^BSESN", "BSE SENSEX", "BSE"),
        ("^BSE500", "BSE 500", "BSE"),
    ]

    return [
        {
            "symbol": symbol,
            "company_name": name,
            "exchange": exchange,
            "sector": "Index",
            "type": "INDEX",
            "yahoo_symbol": symbol,
            "isin": "",
        }
        for symbol, name, exchange in indices
    ]


def get_fallback_stocks():
    """Fallback list used when the NSE CSV cannot be downloaded."""
    fallback = [
        ("RELIANCE", "Reliance Industries Limited", "Energy"),
        ("TCS", "Tata Consultancy Services Limited", "IT"),
        ("HDFCBANK", "HDFC Bank Limited", "Banking"),
        ("ICICIBANK", "ICICI Bank Limited", "Banking"),
        ("INFY", "Infosys Limited", "IT"),
        ("SBIN", "State Bank of India", "Banking"),
        ("BHARTIARTL", "Bharti Airtel Limited", "Telecom"),
        ("ITC", "ITC Limited", "Consumer"),
        ("LT", "Larsen & Toubro Limited", "Construction"),
        ("AXISBANK", "Axis Bank Limited", "Banking"),
        ("KOTAKBANK", "Kotak Mahindra Bank Limited", "Banking"),
        ("HCLTECH", "HCL Technologies Limited", "IT"),
        ("MARUTI", "Maruti Suzuki India Limited", "Auto"),
        ("SUNPHARMA", "Sun Pharmaceutical Industries Limited", "Pharma"),
        ("TITAN", "Titan Company Limited", "Consumer"),
        ("ULTRACEMCO", "UltraTech Cement Limited", "Cement"),
        ("BAJFINANCE", "Bajaj Finance Limited", "Finance"),
        ("BAJAJFINSV", "Bajaj Finserv Limited", "Finance"),
        ("LICI", "Life Insurance Corporation of India", "Insurance"),
        ("WIPRO", "Wipro Limited", "IT"),
    ]

    return [
        {
            "symbol": symbol,
            "company_name": company_name,
            "exchange": "NSE",
            "sector": sector,
            "type": "STOCK",
            "yahoo_symbol": yahoo_nse_symbol(symbol),
            "isin": "",
        }
        for symbol, company_name, sector in fallback
    ]


def build_stock_dataframe(stocks):
    """Normalize, deduplicate, and sort stock records."""
    df = pd.DataFrame(stocks)

    required_columns = [
        "symbol",
        "company_name",
        "exchange",
        "sector",
        "type",
        "yahoo_symbol",
        "isin",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    for column in required_columns:
        df[column] = df[column].map(clean_text)

    df = df[df["symbol"].ne("") & df["yahoo_symbol"].ne("")]
    df = df.drop_duplicates(subset=["exchange", "symbol"], keep="first")
    df = df.sort_values(["type", "exchange", "symbol"]).reset_index(drop=True)
    return df[required_columns]


def update_stock_list():
    """Update the stock list CSV used by the Streamlit app."""
    print("=" * 60)
    print("Indian Stock List Updater")
    print("=" * 60)
    print(f"Update started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    stocks = fetch_nse_stocks()
    if stocks:
        print(f"Fetched {len(stocks)} NSE stocks")
    else:
        print("NSE download failed, using fallback stock list")
        stocks = get_fallback_stocks()

    indices = fetch_indian_indices()
    print(f"Added {len(indices)} Indian indices")

    df = build_stock_dataframe(stocks + indices)
    if df.empty:
        print("Failed to build any stock records")
        return False

    output_path = Path(OUTPUT_CSV)
    df.to_csv(output_path, index=False)

    stock_count = int(df["type"].eq("STOCK").sum())
    index_count = int(df["type"].eq("INDEX").sum())
    print(f"Saved {len(df)} rows to {output_path}")
    print(f"  Stocks: {stock_count}")
    print(f"  Indices: {index_count}")
    print(f"Update completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if update_stock_list() else 1)
