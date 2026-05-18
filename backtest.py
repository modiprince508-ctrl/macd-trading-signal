import pandas as pd

def backtest_signals(df):
    """
    Simple backtest analysis based on BUY/SELL signals
    
    Args:
        df: DataFrame with trade_signal column
    
    Returns:
        Dictionary with backtest summary
    """
    if df is None or df.empty:
        return None
    
    # Filter only BUY and SELL signals
    signals = df[df['trade_signal'].isin(['BUY', 'SELL'])].copy()
    
    if signals.empty:
        return {
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0,
            'total_profit_loss': 0,
            'avg_profit_loss': 0
        }
    
    total_trades = 0
    win_trades = 0
    loss_trades = 0
    total_profit_loss = 0
    
    buy_price = None
    buy_date = None
    
    for idx, row in signals.iterrows():
        if row['trade_signal'] == 'BUY':
            buy_price = row['close']
            buy_date = idx
        
        elif row['trade_signal'] == 'SELL' and buy_price is not None:
            sell_price = row['close']
            sell_date = idx
            
            profit_loss = sell_price - buy_price
            total_profit_loss += profit_loss
            total_trades += 1
            
            if profit_loss > 0:
                win_trades += 1
            else:
                loss_trades += 1
            
            buy_price = None
            buy_date = None
    
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    avg_profit_loss = (total_profit_loss / total_trades) if total_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'win_rate': round(win_rate, 2),
        'total_profit_loss': round(total_profit_loss, 2),
        'avg_profit_loss': round(avg_profit_loss, 2)
    }

def get_trade_history(df):
    """Get detailed trade history"""
    if df is None or df.empty:
        return None
    
    signals = df[df['trade_signal'].isin(['BUY', 'SELL'])].copy()
    
    if signals.empty:
        return None
    
    trades = []
    buy_price = None
    buy_date = None
    
    for idx, row in signals.iterrows():
        if row['trade_signal'] == 'BUY':
            buy_price = row['close']
            buy_date = idx
        
        elif row['trade_signal'] == 'SELL' and buy_price is not None:
            sell_price = row['close']
            sell_date = idx
            
            profit_loss = sell_price - buy_price
            profit_loss_pct = (profit_loss / buy_price * 100) if buy_price != 0 else 0
            
            trades.append({
                'buy_date': buy_date.strftime('%Y-%m-%d'),
                'buy_price': round(buy_price, 2),
                'sell_date': sell_date.strftime('%Y-%m-%d'),
                'sell_price': round(sell_price, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_pct': round(profit_loss_pct, 2)
            })
            
            buy_price = None
            buy_date = None
    
    return pd.DataFrame(trades) if trades else None
