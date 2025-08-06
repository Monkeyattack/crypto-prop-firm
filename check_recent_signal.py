#!/usr/bin/env python3
"""Check for recent signals around 2:12 PM CST"""

import sqlite3
from datetime import datetime, timedelta

def check_recent_signals():
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # 2:12 PM CST is 19:12 UTC (summer) or 20:12 UTC (winter)
    # Let's check both time ranges
    print("=== Checking for signals around 2:12 PM CST ===")
    
    # Check signals from 19:00 to 20:30 UTC
    cursor.execute('''
        SELECT id, symbol, side, entry_price, timestamp, channel, message_id
        FROM signal_log 
        WHERE timestamp >= datetime('2025-08-06 19:00:00') 
        AND timestamp <= datetime('2025-08-06 20:30:00')
        ORDER BY timestamp DESC
    ''')
    
    signals = cursor.fetchall()
    if signals:
        print(f"Found {len(signals)} signals in the time range:")
        for signal in signals:
            print(f"  Signal #{signal[0]}: {signal[1]} {signal[2]} @ ${signal[3] if signal[3] else 'N/A'}")
            print(f"    Time: {signal[4]} UTC")
            print(f"    Message ID: {signal[6]}")
    else:
        print("No signals found in that time range")
    
    # Check message tracking
    cursor.execute('''
        SELECT last_message_id, last_check_time 
        FROM processed_messages 
        WHERE channel_name LIKE '%SMRT%'
    ''')
    result = cursor.fetchone()
    if result:
        print(f"\n=== Message Tracking ===")
        print(f"Currently tracking from message ID: {result[0]}")
        print(f"Last check time: {result[1]}")
        
        # If we found signals, check if they were skipped
        if signals:
            for signal in signals:
                if signal[6] and signal[6] <= result[0]:
                    print(f"\n⚠️  Signal #{signal[0]} (message {signal[6]}) was SKIPPED - before tracking point")
                else:
                    print(f"\n✓ Signal #{signal[0]} (message {signal[6]}) should have been processed")
    
    # Check latest signals regardless of time
    print("\n=== Latest 5 Signals ===")
    cursor.execute('''
        SELECT id, symbol, side, entry_price, timestamp, message_id, processed, trade_executed
        FROM signal_log 
        WHERE channel LIKE '%SMRT%'
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        status = "EXECUTED" if row[7] else ("PROCESSED" if row[6] else "PENDING")
        print(f"  {row[4]}: {row[1]} {row[2]} @ ${row[3] if row[3] else 'N/A'} (msg {row[5]}) - {status}")
    
    # Check PM2 logs for signal monitor
    print("\n=== Checking Signal Monitor Activity ===")
    cursor.execute('''
        SELECT COUNT(*) FROM signal_log 
        WHERE timestamp >= datetime('now', '-1 hour')
        AND channel LIKE '%SMRT%'
    ''')
    recent_count = cursor.fetchone()[0]
    print(f"Signals logged in last hour: {recent_count}")
    
    conn.close()

if __name__ == "__main__":
    check_recent_signals()