"""
Process a historical XAUUSD signal from Telegram
"""

import sqlite3
from datetime import datetime

def process_xauusd_signal():
    """Process the XAUUSD signal we found"""
    
    # The signal from Telegram:
    # Buy XAUUSD
    # Entry: 3400.48
    # TP: 3456.927968
    # SL: 3344.712128
    
    signal = {
        'channel': 'SMRT Signals - Gold/FX Channel',
        'message_id': 447,
        'timestamp': '2025-08-07 22:06:01',
        'symbol': 'XAUUSD',
        'side': 'BUY',
        'entry_price': 3400.48,
        'stop_loss': 3344.712128,
        'take_profit': 3456.927968,
        'signal_type': 'SPOT',
        'raw_message': 'Buy XAUUSD\nEntry: 3400.48\nTP: 3456.927968\nSL: 3344.712128'
    }
    
    # Calculate R:R
    risk = signal['entry_price'] - signal['stop_loss']
    reward = signal['take_profit'] - signal['entry_price']
    rr = reward / risk if risk > 0 else 0
    
    print("="*70)
    print("PROCESSING HISTORICAL XAUUSD SIGNAL")
    print("="*70)
    print(f"Symbol: {signal['symbol']}")
    print(f"Side: {signal['side']}")
    print(f"Entry: {signal['entry_price']:.2f}")
    print(f"Stop Loss: {signal['stop_loss']:.2f}")
    print(f"Take Profit: {signal['take_profit']:.2f}")
    print(f"Risk: {risk:.2f} points")
    print(f"Reward: {reward:.2f} points")
    print(f"R:R Ratio: {rr:.2f}")
    print()
    
    # Check if it meets our criteria
    min_rr = 2.5  # Minimum for Gold/FX
    if rr >= min_rr:
        print(f"[PASS] Signal PASSES criteria (R:R {rr:.2f} >= {min_rr})")
    else:
        print(f"[FAIL] Signal FAILS criteria (R:R {rr:.2f} < {min_rr})")
    
    # Insert into database
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Check if already exists
    cursor.execute("""
        SELECT COUNT(*) FROM signal_log 
        WHERE message_id = ? AND channel = ?
    """, (signal['message_id'], signal['channel']))
    
    exists = cursor.fetchone()[0] > 0
    
    if not exists:
        cursor.execute("""
            INSERT INTO signal_log 
            (channel, message_id, timestamp, symbol, side, entry_price, 
             stop_loss, take_profit, signal_type, raw_message, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            signal['channel'],
            signal['message_id'],
            signal['timestamp'],
            signal['symbol'],
            signal['side'],
            signal['entry_price'],
            signal['stop_loss'],
            signal['take_profit'],
            signal['signal_type'],
            signal['raw_message']
        ))
        conn.commit()
        print("\n[OK] Signal added to database for processing")
    else:
        print("\n[OK] Signal already in database")
    
    conn.close()
    
    print("\n" + "="*70)
    print("Signal is now available for paper trading system to process")
    print("="*70)

if __name__ == "__main__":
    process_xauusd_signal()