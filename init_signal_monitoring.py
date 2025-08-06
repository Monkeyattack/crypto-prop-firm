#!/usr/bin/env python3
"""Initialize signal monitoring tables and test with sample data"""

import sqlite3
from datetime import datetime, timedelta

def init_signal_monitoring():
    """Initialize signal monitoring tables"""
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("Initializing signal monitoring tables...")
    
    # Create signal_log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message_id INTEGER,
            timestamp DATETIME,
            symbol TEXT,
            side TEXT,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            signal_type TEXT,
            raw_message TEXT,
            processed INTEGER DEFAULT 0,
            trade_executed INTEGER DEFAULT 0,
            execution_result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("[OK] signal_log table created")
    
    # Add some test signals for today to demonstrate the UI
    test_signals = [
        {
            'channel': 'TestChannel',
            'message_id': 1001,
            'timestamp': datetime.now() - timedelta(hours=3),
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'entry_price': 68000,
            'take_profit': 71400,  # 5% TP
            'stop_loss': 64600,    # 5% SL
            'signal_type': 'SPOT',
            'processed': 1,
            'trade_executed': 0,  # Waiting for entry
            'raw_message': 'BTC/USDT BUY @ 68000'
        },
        {
            'channel': 'TestChannel', 
            'message_id': 1002,
            'timestamp': datetime.now() - timedelta(hours=2),
            'symbol': 'ETHUSDT',
            'side': 'BUY',
            'entry_price': 3350,
            'take_profit': 3517.5,  # 5% TP
            'stop_loss': 3182.5,    # 5% SL
            'signal_type': 'SPOT',
            'processed': 1,
            'trade_executed': 1,  # Executed
            'execution_result': 'Trade opened at 3345',
            'raw_message': 'ETH/USDT BUY @ 3350'
        },
        {
            'channel': 'TestChannel',
            'message_id': 1003,
            'timestamp': datetime.now() - timedelta(minutes=30),
            'symbol': 'SOLUSDT',
            'side': 'BUY',
            'entry_price': 145,
            'take_profit': 152.25,  # 5% TP
            'stop_loss': 137.75,    # 5% SL
            'signal_type': 'SPOT',
            'processed': 0,  # Not processed yet
            'trade_executed': 0,
            'raw_message': 'SOL/USDT BUY @ 145'
        }
    ]
    
    # Insert test signals
    for signal in test_signals:
        cursor.execute('''
            INSERT INTO signal_log 
            (channel, message_id, timestamp, symbol, side, entry_price, 
             take_profit, stop_loss, signal_type, raw_message, processed, 
             trade_executed, execution_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal['channel'], signal['message_id'], signal['timestamp'],
            signal['symbol'], signal['side'], signal['entry_price'],
            signal['take_profit'], signal['stop_loss'], signal['signal_type'],
            signal['raw_message'], signal['processed'], signal['trade_executed'],
            signal.get('execution_result', None)
        ))
    
    print(f"[OK] Added {len(test_signals)} test signals")
    
    # Update trading settings to show monitoring is active
    cursor.execute('''
        UPDATE trading_settings 
        SET updated_at = ? 
        WHERE id = 1
    ''', (datetime.now(),))
    
    conn.commit()
    conn.close()
    
    print("\nSignal monitoring initialized!")
    print("You can now view signals in the dashboard under 'Signal Monitoring'")
    print("\nTo start real monitoring, run: python automated_signal_monitor.py")

if __name__ == "__main__":
    init_signal_monitoring()