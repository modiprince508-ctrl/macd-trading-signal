import pandas as pd
import numpy as np

def EMA(series, period):
    """Calculate Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_macd(df):
    """
    Calculate MACD, Signal, and Histogram
    
    Args:
        df: DataFrame with 'close' column
    
    Returns:
        DataFrame with MACD columns added
    """
    if df is None or df.empty:
        return None
    
    fast = 12
    slow = 26
    signal_period = 9
    
    df = df.copy()
    
    df["ema_fast"] = EMA(df["close"], fast)
    df["ema_slow"] = EMA(df["close"], slow)
    
    df["macd"] = df["ema_fast"] - df["ema_slow"]
    df["signal"] = EMA(df["macd"], signal_period)
    df["hist"] = df["macd"] - df["signal"]
    
    # Threshold to avoid sideways
    df["zeroThreshold"] = 0.0005 * df["close"]
    
    return df

def generate_signals(df):
    """
    Generate trading signals (BUY/SELL/WAIT)
    
    Args:
        df: DataFrame with MACD data
    
    Returns:
        DataFrame with trade_signal column added
    """
    if df is None or df.empty:
        return None
    
    df = df.copy()
    df["trade_signal"] = "WAIT"
    
    for i in range(2, len(df)):
        macd_now = df["macd"].iloc[i]
        signal_now = df["signal"].iloc[i]
        hist_now = df["hist"].iloc[i]
        
        macd_prev = df["macd"].iloc[i-1]
        signal_prev = df["signal"].iloc[i-1]
        
        hist_prev1 = df["hist"].iloc[i-1]
        hist_prev2 = df["hist"].iloc[i-2]
        
        threshold = df["zeroThreshold"].iloc[i]
        
        # Sideways filter
        if abs(macd_now) < threshold:
            df.at[df.index[i], "trade_signal"] = "WAIT"
            continue
        
        # BUY condition
        if (macd_prev <= signal_prev and macd_now > signal_now and
            macd_now > 0 and
            hist_now > 0 and
            hist_prev1 > hist_prev2 and
            hist_now > hist_prev1):
            
            df.at[df.index[i], "trade_signal"] = "BUY"
        
        # SELL condition
        elif (macd_prev >= signal_prev and macd_now < signal_now and
              macd_now < 0 and
              hist_now < 0 and
              hist_prev1 < hist_prev2 and
              hist_now < hist_prev1):
            
            df.at[df.index[i], "trade_signal"] = "SELL"
        
        else:
            df.at[df.index[i], "trade_signal"] = "WAIT"
    
    return df

def get_latest_signal(df):
    """Get the latest trading signal"""
    if df is None or df.empty:
        return None
    
    latest = df.iloc[-1]
    return {
        'date': latest.name.strftime('%Y-%m-%d'),
        'signal': latest['trade_signal'],
        'price': latest['close'],
        'macd': latest['macd'],
        'signal_line': latest['signal'],
        'histogram': latest['hist']
    }

def get_last_n_signals(df, n=20):
    """Get last n signals"""
    if df is None or df.empty:
        return None
    
    signals_df = df[['close', 'macd', 'signal', 'hist', 'trade_signal']].tail(n).copy()
    signals_df['date'] = signals_df.index.strftime('%Y-%m-%d')
    signals_df['close'] = signals_df['close'].round(2)
    signals_df['macd'] = signals_df['macd'].round(4)
    signals_df['signal'] = signals_df['signal'].round(4)
    signals_df['hist'] = signals_df['hist'].round(4)
    
    return signals_df[['date', 'close', 'macd', 'signal', 'hist', 'trade_signal']].iloc[::-1]
