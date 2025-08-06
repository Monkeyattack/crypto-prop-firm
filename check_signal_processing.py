#!/usr/bin/env python3
"""Check signal processing status"""

import sqlite3
from datetime import datetime

def check_signal_processing():
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute('SELECT COUNT(*) FROM signal_log WHERE trade_executed = 1')
    executed_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM signal_log WHERE processed = 1 AND trade_executed = 0')
    pending_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM signal_log WHERE processed = 0')
    unprocessed_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM trades')
    trade_count = cursor.fetchone()[0]
    
    print(f"Signal Processing Status:")
    print(f"- Total trades in database: {trade_count}")
    print(f"- Executed signals: {executed_count}")
    print(f"- Pending signals (processed but not executed): {pending_count}")
    print(f"- Unprocessed signals: {unprocessed_count}")
    
    # Check for discrepancy
    if trade_count != executed_count:
        print(f"\n⚠️  WARNING: Trade count ({trade_count}) doesn't match executed signals ({executed_count})")
    
    # Show latest signals
    print("\nLatest 10 signals:")
    cursor.execute('''
        SELECT symbol, datetime(timestamp), entry_price, processed, trade_executed, channel
        FROM signal_log 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        symbol, timestamp, entry, processed, executed, channel = row
        status = "✅ EXECUTED" if executed else ("🔄 PROCESSED" if processed else "⏳ PENDING")
        entry_str = f"${entry:.2f}" if entry is not None else "N/A"
        print(f"  {timestamp}: {symbol} @ {entry_str} - {status} (from {channel})")
    
    # Check for missing trade_executed updates
    print("\nChecking for trades without signal_log updates...")
    cursor.execute('''
        SELECT t.id, t.symbol, t.entry, t.timestamp
        FROM trades t
        LEFT JOIN signal_log s ON t.symbol = s.symbol 
            AND ABS(t.entry - s.entry_price) < 0.01
            AND s.trade_executed = 1
        WHERE s.id IS NULL
    ''')
    
    missing_updates = cursor.fetchall()
    if missing_updates:
        print(f"Found {len(missing_updates)} trades without corresponding signal_log updates:")
        for trade in missing_updates:
            print(f"  Trade #{trade[0]}: {trade[1]} @ ${trade[2]:.2f} on {trade[3]}")
    else:
        print("All trades have corresponding signal_log entries ✅")
    
    conn.close()

if __name__ == "__main__":
    check_signal_processing()