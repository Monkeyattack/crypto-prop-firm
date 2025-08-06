#!/usr/bin/env python3
"""Check signal monitoring status and recent signals"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def check_signal_status():
    """Check current signal monitoring status"""
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("="*60)
    print("SIGNAL MONITORING STATUS CHECK")
    print("="*60)
    
    # Check if signal_log table exists and has data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_log'")
    if not cursor.fetchone():
        print("\n[WARNING] signal_log table does not exist!")
        print("The automated signal monitor has not been initialized.")
    else:
        # Get signal counts
        cursor.execute("SELECT COUNT(*) FROM signal_log")
        total_signals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE processed = 1")
        processed_signals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE trade_executed = 1")
        executed_trades = cursor.fetchone()[0]
        
        print(f"\nSignal Statistics:")
        print(f"  Total signals captured: {total_signals}")
        print(f"  Processed signals: {processed_signals}")
        print(f"  Executed trades: {executed_trades}")
        
        # Get today's signals
        today = datetime.now().date()
        cursor.execute("""
            SELECT timestamp, symbol, side, entry_price, take_profit, stop_loss, 
                   processed, trade_executed
            FROM signal_log 
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        """, (today,))
        
        today_signals = cursor.fetchall()
        if today_signals:
            print(f"\nToday's Signals ({today}):")
            for sig in today_signals:
                status = "EXECUTED" if sig[7] else ("PROCESSED" if sig[6] else "PENDING")
                print(f"  {sig[0]} - {sig[1]} {sig[2]} @ {sig[3]} (TP: {sig[4]}, SL: {sig[5]}) - {status}")
        else:
            print(f"\nNo signals captured today ({today})")
    
    # Check current open positions
    print("\n" + "-"*60)
    print("CURRENT POSITIONS:")
    
    cursor.execute("""
        SELECT id, symbol, side, entry, tp, sl, timestamp
        FROM trades
        WHERE result = 'open'
        ORDER BY timestamp DESC
    """)
    
    open_trades = cursor.fetchall()
    if open_trades:
        print(f"\nOpen Positions ({len(open_trades)} total):")
        for trade in open_trades:
            print(f"  ID: {trade[0]} - {trade[1]} {trade[2]} @ {trade[3]} (TP: {trade[4]}, SL: {trade[5]})")
            print(f"    Opened: {trade[6]}")
    else:
        print("\nNo open positions")
    
    # Check recent closed trades
    cursor.execute("""
        SELECT symbol, side, entry, result, pnl, timestamp
        FROM trades
        WHERE result != 'open'
        AND DATE(timestamp) >= DATE('now', '-7 days')
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    closed_trades = cursor.fetchall()
    if closed_trades:
        print(f"\nRecent Closed Trades:")
        for trade in closed_trades:
            result_str = "TP HIT" if trade[3] == 'tp' else trade[3].upper()
            print(f"  {trade[0]} {trade[1]} @ {trade[2]} - {result_str} - PnL: ${trade[4]:.2f}")
    
    # Check trading settings
    print("\n" + "-"*60)
    print("TRADING SETTINGS:")
    
    cursor.execute("SELECT settings_json FROM trading_settings WHERE id = 1")
    settings = cursor.fetchone()
    if settings:
        import json
        settings_data = json.loads(settings[0])
        print(f"  Automated Trading Enabled: {settings_data.get('enabled', False)}")
        print(f"  Max Daily Trades: {settings_data.get('max_daily_trades', 'N/A')}")
        print(f"  Position Size: ${settings_data.get('position_size', 'N/A')}")
        print(f"  Trailing TP Enabled: {settings_data.get('trailing_take_profit', {}).get('enabled', False)}")
    else:
        print("  No trading settings found")
    
    # Check last signal check time
    cursor.execute("""
        SELECT updated_at FROM trading_settings 
        WHERE id = 1
    """)
    last_check = cursor.fetchone()
    if last_check:
        print(f"\n  Last Signal Check: {last_check[0]}")
    else:
        print("\n  Signal monitor has never run")
    
    conn.close()
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    if total_signals == 0 if 'total_signals' in locals() else True:
        print("\n1. The automated signal monitor is NOT running")
        print("2. Start it with: python automated_signal_monitor.py")
        print("3. It will monitor Telegram channels for new signals")
        print("4. Signals will be displayed in the dashboard once captured")
    else:
        print("\n1. Signal monitor has captured signals but may not be running")
        print("2. Check if monitor is active: ps aux | grep automated_signal_monitor")
        print("3. If not running, start it: python automated_signal_monitor.py")

if __name__ == "__main__":
    check_signal_status()