#!/usr/bin/env python3
"""Check executed signals and clean up old test trades"""

import sqlite3
from datetime import datetime

def check_and_clean_trades():
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("=== Checking Executed Signals ===")
    # Check the executed signal
    cursor.execute('''
        SELECT id, symbol, side, entry_price, take_profit, stop_loss, 
               timestamp, channel, processed, trade_executed
        FROM signal_log 
        WHERE trade_executed = 1
    ''')
    
    executed_signals = cursor.fetchall()
    print(f"Found {len(executed_signals)} executed signals:")
    for signal in executed_signals:
        print(f"  Signal #{signal[0]}: {signal[1]} {signal[2]} @ ${signal[3]:.2f}")
        print(f"    TP: ${signal[4]:.2f}, SL: ${signal[5]:.2f}")
        print(f"    Time: {signal[6]}, Channel: {signal[7]}")
    
    print("\n=== Checking Pending Signals (Processed but not executed) ===")
    cursor.execute('''
        SELECT id, symbol, side, entry_price, take_profit, stop_loss, timestamp
        FROM signal_log 
        WHERE processed = 1 AND trade_executed = 0
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    
    pending_signals = cursor.fetchall()
    print(f"Found {len(pending_signals)} pending signals (showing latest 5):")
    for signal in pending_signals:
        print(f"  Signal #{signal[0]}: {signal[1]} {signal[2]} @ ${signal[3]:.2f} (waiting for entry)")
    
    print("\n=== Current Trades in Database ===")
    cursor.execute('''
        SELECT id, symbol, side, entry, tp, sl, result, timestamp, position_size
        FROM trades
        ORDER BY id
    ''')
    
    trades = cursor.fetchall()
    for trade in trades:
        print(f"  Trade #{trade[0]}: {trade[1]} {trade[2]} @ ${trade[3]:.2f}")
        print(f"    Status: {trade[6]}, Time: {trade[7]}, Size: ${trade[8]:.2f}")
    
    # Check if old test trades should be removed
    print("\n=== Analyzing Test Trades ===")
    old_test_trades = []
    for trade in trades:
        trade_id, symbol, side, entry, tp, sl, result, timestamp, size = trade
        trade_date = datetime.fromisoformat(timestamp.replace(' ', 'T'))
        
        # Check if this is an old test trade (before August 5th and not matched to signal_log)
        if trade_date < datetime(2025, 8, 5):
            cursor.execute('''
                SELECT COUNT(*) FROM signal_log 
                WHERE symbol = ? AND ABS(entry_price - ?) < 0.01 AND trade_executed = 1
            ''', (symbol, entry))
            
            matched_signal = cursor.fetchone()[0]
            if matched_signal == 0:
                old_test_trades.append(trade_id)
                print(f"  Trade #{trade_id} is an old test trade (no matching signal)")
    
    if old_test_trades:
        print(f"\nFound {len(old_test_trades)} old test trades to remove: {old_test_trades}")
        
        # Remove old test trades
        for trade_id in old_test_trades:
            cursor.execute('DELETE FROM trades WHERE id = ?', (trade_id,))
            print(f"  Removed trade #{trade_id}")
        
        conn.commit()
        print("\n[SUCCESS] Old test trades removed successfully")
    else:
        print("\n[SUCCESS] No old test trades found")
    
    # Final check
    cursor.execute('SELECT COUNT(*) FROM trades')
    remaining_trades = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM trades WHERE result = "open"')
    open_positions = cursor.fetchone()[0]
    
    print(f"\n=== Final Status ===")
    print(f"Total trades remaining: {remaining_trades}")
    print(f"Open positions: {open_positions}")
    
    conn.close()

if __name__ == "__main__":
    check_and_clean_trades()