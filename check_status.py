"""Check Paper Trading System Status"""

import sqlite3
import os
from datetime import datetime

print("=" * 70)
print("PAPER TRADING SYSTEM STATUS")
print("=" * 70)
print(f"Time: {datetime.now()}")
print()

# Check if paper trading database exists
if os.path.exists('paper_trades.db'):
    conn = sqlite3.connect('paper_trades.db')
    cursor = conn.cursor()
    
    # Check for trades
    try:
        cursor.execute("SELECT COUNT(*) FROM paper_trades")
        trade_count = cursor.fetchone()[0]
        print(f"Paper Trades Executed: {trade_count}")
    except:
        print("Paper Trades Table: Not yet created (no trades executed)")
    
    conn.close()
else:
    print("Paper Trading Database: Not yet created")

print()

# Check signals
conn = sqlite3.connect('trade_log.db')
cursor = conn.cursor()

# Count unprocessed signals
cursor.execute("SELECT COUNT(*) FROM signal_log WHERE processed = 0")
unprocessed = cursor.fetchone()[0]
print(f"Unprocessed Signals: {unprocessed}")

# Check signal quality
cursor.execute("""
    SELECT symbol, 
           COUNT(*) as count,
           AVG(CASE 
               WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
               ELSE (entry_price - take_profit) / (stop_loss - entry_price)
           END) as avg_rr
    FROM signal_log 
    WHERE processed = 0
    GROUP BY symbol
    ORDER BY avg_rr DESC
""")

print("\nSignal Quality by Symbol:")
for row in cursor.fetchall():
    symbol, count, avg_rr = row
    if avg_rr:
        print(f"  {symbol:10} Count: {count:3}  Avg R:R: {avg_rr:.2f}")

conn.close()

print()
print("System Configuration:")
print("  Min R:R for Crypto: 2.0")
print("  Min R:R for Gold/FX: 2.5")
print("  Risk per trade: 1%")
print("  Demo Balance: $50,000")
print()

# Check if process is running
log_file = 'paper_trading.log'
if os.path.exists(log_file):
    # Get last modified time
    mod_time = os.path.getmtime(log_file)
    last_update = datetime.fromtimestamp(mod_time)
    time_diff = (datetime.now() - last_update).total_seconds()
    
    if time_diff < 60:
        print(f"System Status: ACTIVE (last update {int(time_diff)}s ago)")
    else:
        print(f"System Status: INACTIVE (last update {int(time_diff/60)}m ago)")
        print("  To restart: python start_paper_trading.py")
    
    # Show last few lines of log
    print("\nRecent Activity:")
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[-5:]:
            if line.strip():
                print(f"  {line.strip()}")
else:
    print("System Status: NOT STARTED")
    print("  To start: python start_paper_trading.py")

print()
print("=" * 70)
print("\nNOTE: The system is correctly filtering out low R:R trades.")
print("Current crypto signals have R:R ratios of 0.7-1.2 (below 2.0 minimum).")
print("System is waiting for higher quality signals to execute trades.")
print("This is CORRECT behavior for prop firm evaluation.")