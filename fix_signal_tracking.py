#!/usr/bin/env python3
"""Fix signal tracking to process the missed SOLUSD signal"""

import sqlite3
from datetime import datetime

def fix_signal_tracking():
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("=== Fixing Signal Tracking ===")
    
    # Get the SOLUSD signal details
    cursor.execute('''
        SELECT id, symbol, side, entry_price, take_profit, stop_loss, message_id
        FROM signal_log 
        WHERE symbol = 'SOLUSD' 
        AND timestamp >= datetime('2025-08-06 19:00:00')
        AND processed = 0
        LIMIT 1
    ''')
    
    signal = cursor.fetchone()
    if signal:
        signal_id, symbol, side, entry, tp, sl, msg_id = signal
        print(f"Found unprocessed signal: {symbol} {side} @ ${entry}")
        print(f"  TP: ${tp}, SL: ${sl}")
        
        # Update message tracking to before this signal
        if msg_id:
            new_tracking_id = msg_id - 1
            cursor.execute('''
                UPDATE processed_messages 
                SET last_message_id = ?
                WHERE channel_name LIKE '%SMRT%'
            ''', (new_tracking_id,))
            print(f"Updated tracking to message ID {new_tracking_id} (before signal)")
            
            conn.commit()
            print("\n✓ Signal tracking fixed. The signal monitor will process this signal on the next check.")
        else:
            print("Signal has no message ID, cannot adjust tracking")
    else:
        print("No unprocessed SOLUSD signals found")
    
    # Show current status
    cursor.execute('''
        SELECT last_message_id FROM processed_messages WHERE channel_name LIKE '%SMRT%'
    ''')
    result = cursor.fetchone()
    print(f"\nCurrent tracking message ID: {result[0] if result else 'Not set'}")
    
    conn.close()

if __name__ == "__main__":
    fix_signal_tracking()