"""
Add Gold/FX Channel to Signal Monitoring
Configures the system to monitor SMRT Signals - Gold/FX Channel
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_gold_fx_channel():
    """Add Gold/FX channel to monitoring list"""
    
    db_path = 'trade_log.db'
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Add the Gold/FX channel to processed_messages
        cursor.execute("""
            INSERT OR REPLACE INTO processed_messages 
            (channel_name, last_message_id, last_check_time)
            VALUES (?, ?, ?)
        """, ('SMRT Signals - Gold/FX Channel', 0, datetime.now()))
        
        # Create a table for Gold/FX signals if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_fx_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                action TEXT,  -- BUY/SELL
                entry_price REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                take_profit_3 REAL,
                risk_reward REAL,
                message_text TEXT,
                message_id INTEGER,
                processed BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        logger.info("Added SMRT Signals - Gold/FX Channel to monitoring")
        
        # Check current channels
        cursor.execute("SELECT * FROM processed_messages")
        channels = cursor.fetchall()
        
        print("\nCurrently monitored channels:")
        for channel in channels:
            print(f"  - {channel[0]}: Last ID {channel[1]}, Last check {channel[2]}")

def sample_gold_fx_analysis():
    """Analyze sample Gold/FX signals for comparison"""
    
    # Sample Gold/FX signals for analysis (typical patterns)
    sample_signals = [
        # XAUUSD (Gold) signals
        {'symbol': 'XAUUSD', 'action': 'BUY', 'entry': 1950.50, 'sl': 1945.00, 'tp': 1965.00},
        {'symbol': 'XAUUSD', 'action': 'SELL', 'entry': 1975.00, 'sl': 1980.00, 'tp': 1960.00},
        {'symbol': 'XAUUSD', 'action': 'BUY', 'entry': 1935.00, 'sl': 1930.00, 'tp': 1950.00},
        
        # Major Forex pairs
        {'symbol': 'EURUSD', 'action': 'BUY', 'entry': 1.0850, 'sl': 1.0820, 'tp': 1.0920},
        {'symbol': 'GBPUSD', 'action': 'SELL', 'entry': 1.2750, 'sl': 1.2780, 'tp': 1.2680},
        {'symbol': 'USDJPY', 'action': 'BUY', 'entry': 148.50, 'sl': 148.00, 'tp': 149.50},
        {'symbol': 'AUDUSD', 'action': 'SELL', 'entry': 0.6550, 'sl': 0.6580, 'tp': 0.6480},
    ]
    
    # Calculate statistics
    stats = {
        'total': len(sample_signals),
        'by_symbol': {},
        'avg_rr': 0,
        'total_rr': 0
    }
    
    for signal in sample_signals:
        symbol = signal['symbol']
        if symbol not in stats['by_symbol']:
            stats['by_symbol'][symbol] = {'count': 0, 'total_rr': 0}
        
        # Calculate R:R
        if signal['action'] == 'BUY':
            risk = signal['entry'] - signal['sl']
            reward = signal['tp'] - signal['entry']
        else:
            risk = signal['sl'] - signal['entry']
            reward = signal['entry'] - signal['tp']
        
        if risk > 0:
            rr = reward / risk
            signal['rr_ratio'] = rr
            stats['total_rr'] += rr
            stats['by_symbol'][symbol]['count'] += 1
            stats['by_symbol'][symbol]['total_rr'] += rr
    
    stats['avg_rr'] = stats['total_rr'] / len(sample_signals) if sample_signals else 0
    
    # Print analysis
    print("\n" + "="*60)
    print("GOLD/FX SIGNAL ANALYSIS (Sample Data)")
    print("="*60)
    print(f"\nTotal Signals: {stats['total']}")
    print(f"Average R:R Ratio: {stats['avg_rr']:.2f}")
    
    print("\nBy Symbol:")
    for symbol, data in stats['by_symbol'].items():
        avg_rr = data['total_rr'] / data['count'] if data['count'] > 0 else 0
        print(f"  {symbol}: {data['count']} signals, Avg R:R: {avg_rr:.2f}")
    
    print("\nSignal Details:")
    for signal in sample_signals:
        print(f"  {signal['symbol']} {signal['action']} @ {signal['entry']}, "
              f"SL: {signal['sl']}, TP: {signal['tp']}, R:R: {signal.get('rr_ratio', 0):.2f}")
    
    # Compare with typical crypto stats
    print("\n" + "="*60)
    print("COMPARISON WITH CRYPTO SIGNALS")
    print("="*60)
    
    comparison = """
    Metric                  Gold/FX         Crypto
    ─────────────────────────────────────────────────
    Avg R:R Ratio:          2.8-3.5         1.5-2.5
    Typical Win Rate:       55-60%          60-65%
    Volatility:             Lower           Higher
    Trading Hours:          24/5            24/7
    Leverage Available:     100-500x        20-125x
    Stop Loss (typical):    20-50 pips      2-5%
    Take Profit (typical):  60-150 pips     3-10%
    
    KEY DIFFERENCES:
    • Gold/FX: Higher R:R but lower win rate
    • Gold/FX: More predictable, follows traditional patterns
    • Crypto: Higher frequency of signals
    • Crypto: More volatile, larger percentage moves
    
    PROP FIRM CONSIDERATIONS:
    • Gold/FX often preferred for consistency
    • Lower correlation between trades
    • Better for risk management
    • Typically allowed in more prop firms
    """
    
    print(comparison)
    
    return stats

if __name__ == "__main__":
    # Add channel to monitoring
    add_gold_fx_channel()
    
    # Analyze sample signals
    sample_gold_fx_analysis()