#!/usr/bin/env python3
"""Check real signals from SMRT channel"""

import sqlite3
from datetime import datetime, timedelta

def check_real_signals():
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("=== Recent SMRT Signals ===")
    # Get recent signals from SMRT channel
    cursor.execute('''
        SELECT id, symbol, side, entry_price, take_profit, stop_loss, 
               timestamp, processed, trade_executed
        FROM signal_log 
        WHERE channel LIKE '%SMRT%'
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    
    signals = cursor.fetchall()
    print(f"Found {len(signals)} recent SMRT signals (showing latest 10):")
    
    for signal in signals:
        status = "EXECUTED" if signal[8] else ("PROCESSED" if signal[7] else "PENDING")
        entry_str = f"${signal[3]:.2f}" if signal[3] else "N/A"
        tp_str = f"${signal[4]:.2f}" if signal[4] else "N/A"
        sl_str = f"${signal[5]:.2f}" if signal[5] else "N/A"
        
        print(f"\n  Signal #{signal[0]}: {signal[1]} {signal[2]} @ {entry_str}")
        print(f"    TP: {tp_str}, SL: {sl_str}")
        print(f"    Time: {signal[6]}")
        print(f"    Status: {status}")
    
    # Check if trading is enabled
    cursor.execute('''
        SELECT settings_json FROM trading_settings WHERE id = 1
    ''')
    result = cursor.fetchone()
    if result and result[0]:
        import json
        settings = json.loads(result[0])
        trading_enabled = settings.get('enabled', False)
        print(f"\n=== Trading Status ===")
        print(f"Automated trading: {'ENABLED' if trading_enabled else 'DISABLED'}")
    
    # Check signal monitor status
    cursor.execute('''
        SELECT last_message_id, last_check_time 
        FROM processed_messages 
        WHERE channel_name LIKE '%SMRT%'
    ''')
    result = cursor.fetchone()
    if result:
        last_check = datetime.fromisoformat(result[1].replace(' ', 'T'))
        time_since = datetime.now() - last_check
        print(f"\n=== Signal Monitor Status ===")
        print(f"Last message ID tracked: {result[0]}")
        print(f"Last check: {time_since.total_seconds()/60:.1f} minutes ago")
    
    conn.close()

if __name__ == "__main__":
    check_real_signals()