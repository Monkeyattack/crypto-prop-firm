"""
Monitor Paper Trading System Status
Shows signal collector and paper trader status
"""

import sqlite3
import os
from datetime import datetime
import MetaTrader5 as mt5

def check_market_hours():
    """Check if forex market is open"""
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    
    # Forex market hours (roughly)
    # Sunday 5PM - Friday 5PM EST
    # Closed: Friday 5PM - Sunday 5PM
    
    if weekday == 5:  # Saturday
        return False, "Market closed (Weekend)"
    elif weekday == 6:  # Sunday
        if hour < 17:  # Before 5 PM
            return False, "Market closed (Weekend - opens 5 PM EST)"
        else:
            return True, "Market open (Sunday evening)"
    elif weekday == 4:  # Friday
        if hour >= 17:  # After 5 PM
            return False, "Market closed (Weekend started)"
        else:
            return True, "Market open"
    else:
        return True, "Market open"

def main():
    print("=" * 70)
    print("PAPER TRADING SYSTEM MONITOR")
    print("=" * 70)
    print(f"Time: {datetime.now()}")
    print()
    
    # Check market status
    market_open, status = check_market_hours()
    print(f"Market Status: {status}")
    if not market_open:
        print("  Note: Trades will execute when market reopens")
    print()
    
    # Check signal collector
    if os.path.exists('signal_collector.log'):
        mod_time = os.path.getmtime('signal_collector.log')
        last_update = datetime.fromtimestamp(mod_time)
        time_diff = (datetime.now() - last_update).total_seconds()
        if time_diff < 300:  # 5 minutes
            print(f"Signal Collector: RUNNING (last activity {int(time_diff)}s ago)")
        else:
            print(f"Signal Collector: STOPPED (last activity {int(time_diff/60)}m ago)")
    else:
        print("Signal Collector: NOT STARTED")
    
    # Check paper trader
    if os.path.exists('paper_trading.log'):
        mod_time = os.path.getmtime('paper_trading.log')
        last_update = datetime.fromtimestamp(mod_time)
        time_diff = (datetime.now() - last_update).total_seconds()
        if time_diff < 60:
            print(f"Paper Trader: RUNNING (last activity {int(time_diff)}s ago)")
        else:
            print(f"Paper Trader: STOPPED (last activity {int(time_diff/60)}m ago)")
    else:
        print("Paper Trader: NOT STARTED")
    
    print()
    
    # Check database for recent signals
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Count signals by type
    cursor.execute("""
        SELECT 
            CASE 
                WHEN symbol IN ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY') THEN 'Gold/FX'
                ELSE 'Crypto'
            END as type,
            COUNT(*) as count,
            AVG(CASE 
                WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                ELSE (entry_price - take_profit) / (stop_loss - entry_price)
            END) as avg_rr
        FROM signal_log 
        WHERE processed = 0
        GROUP BY type
    """)
    
    print("Unprocessed Signals:")
    for row in cursor.fetchall():
        sig_type, count, avg_rr = row
        if avg_rr:
            print(f"  {sig_type}: {count} signals, Avg R:R: {avg_rr:.2f}")
    
    # Check for recent new signals
    cursor.execute("""
        SELECT COUNT(*) 
        FROM signal_log 
        WHERE datetime(timestamp) > datetime('now', '-5 minutes')
        AND processed = 0
    """)
    recent = cursor.fetchone()[0]
    if recent > 0:
        print(f"  New signals in last 5 minutes: {recent}")
    
    # Check paper trades
    if os.path.exists('paper_trades.db'):
        trade_conn = sqlite3.connect('paper_trades.db')
        trade_cursor = trade_conn.cursor()
        
        try:
            trade_cursor.execute("SELECT COUNT(*) FROM paper_trades")
            total_trades = trade_cursor.fetchone()[0]
            
            trade_cursor.execute("SELECT COUNT(*) FROM paper_trades WHERE close_time IS NULL")
            open_trades = trade_cursor.fetchone()[0]
            
            print(f"\nPaper Trades:")
            print(f"  Total: {total_trades}")
            print(f"  Open: {open_trades}")
            print(f"  Closed: {total_trades - open_trades}")
        except:
            print("\nPaper Trades: No trades executed yet")
        
        trade_conn.close()
    else:
        print("\nPaper Trades: Database not created (no trades yet)")
    
    conn.close()
    
    # Check MT5 connection
    if mt5.initialize():
        account = mt5.account_info()
        if account:
            print(f"\nMT5 Status: Connected")
            print(f"  Account: {account.login}")
            print(f"  Balance: ${account.balance:.2f}")
            
            # Check if any symbols are tradeable now
            symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
            tradeable = []
            for symbol in symbols:
                info = mt5.symbol_info(symbol)
                if info and info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    tradeable.append(symbol)
            
            if tradeable:
                print(f"  Tradeable now: {', '.join(tradeable)}")
            else:
                print(f"  No symbols tradeable (market closed)")
        
        mt5.shutdown()
    else:
        print("\nMT5 Status: Not connected")
    
    print("\n" + "=" * 70)
    
    if not market_open:
        print("IMPORTANT: Forex market is closed")
        print("Paper trading will resume when market opens")
        print("Market opens: Sunday 5 PM EST")
    else:
        print("System is operational and waiting for signals")
    
    print("=" * 70)

if __name__ == "__main__":
    main()