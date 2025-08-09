#!/usr/bin/env python3
"""
FTMO Trading Monitor
Real-time monitoring of FTMO Bitcoin trading performance
"""

import sqlite3
import time
from datetime import datetime
import os

def monitor_ftmo_trading():
    """Monitor FTMO trading in real-time"""
    
    db_path = 'ftmo_bitcoin.db'
    log_path = 'ftmo_bitcoin.log'
    
    if not os.path.exists(db_path):
        print("No trading database found yet. Waiting for first trade...")
        return
    
    print("="*80)
    print("FTMO BITCOIN TRADING MONITOR")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get overall statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
            SUM(CASE WHEN status LIKE 'CLOSED%' THEN 1 ELSE 0 END) as closed_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as best_trade,
            MIN(pnl) as worst_trade
        FROM ftmo_trades
    """)
    
    stats = cursor.fetchone()
    
    if stats and stats[0] > 0:
        print("TRADING STATISTICS:")
        print("-"*50)
        print(f"Total Trades: {stats[0]}")
        print(f"Open Positions: {stats[1]}")
        print(f"Closed Trades: {stats[2]}")
        print(f"Wins: {stats[3]} | Losses: {stats[4]}")
        if stats[2] > 0:
            win_rate = (stats[3] / stats[2]) * 100 if stats[2] > 0 else 0
            print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total P&L: ${stats[5]:.2f}" if stats[5] else "Total P&L: $0.00")
        print(f"Average P&L: ${stats[6]:.2f}" if stats[6] else "Average P&L: $0.00")
        print(f"Best Trade: ${stats[7]:.2f}" if stats[7] else "Best Trade: $0.00")
        print(f"Worst Trade: ${stats[8]:.2f}" if stats[8] else "Worst Trade: $0.00")
        
        # FTMO Progress (scaled)
        print("\nFTMO PROGRESS (Demo scaled to $100k):")
        print("-"*50)
        scale = 2  # $50k demo to $100k FTMO
        scaled_pnl = (stats[5] * scale) if stats[5] else 0
        phase1_target = 10000  # $10k for phase 1
        progress = (scaled_pnl / phase1_target) * 100 if phase1_target > 0 else 0
        
        print(f"Scaled P&L: ${scaled_pnl:.2f}")
        print(f"Phase 1 Progress: {progress:.1f}% (${scaled_pnl:.0f} / $10,000)")
        
        if scaled_pnl > 0:
            days_to_target = (10000 - scaled_pnl) / (scaled_pnl / 1) if scaled_pnl > 0 else 999
            print(f"Est. Days to Phase 1: {days_to_target:.0f} days")
    
    # Get recent trades
    print("\nRECENT TRADES:")
    print("-"*50)
    
    cursor.execute("""
        SELECT 
            ticket, symbol, side, entry_price, exit_price,
            pnl, pnl_pct, status, exit_reason, close_time
        FROM ftmo_trades
        WHERE status LIKE 'CLOSED%'
        ORDER BY close_time DESC
        LIMIT 5
    """)
    
    recent = cursor.fetchall()
    if recent:
        for trade in recent:
            status = "WIN" if trade[5] > 0 else "LOSS"
            print(f"{trade[2]} {trade[1]} @ {trade[3]:.2f} -> {trade[4]:.2f} | "
                  f"{status} ${trade[5]:.2f} ({trade[6]:.1f}%) | {trade[8] or 'In Progress'}")
    else:
        print("No closed trades yet")
    
    # Get open positions
    print("\nOPEN POSITIONS:")
    print("-"*50)
    
    cursor.execute("""
        SELECT 
            ticket, symbol, side, entry_price, stop_loss, take_profit,
            lot_size, open_time
        FROM ftmo_trades
        WHERE status = 'OPEN'
        ORDER BY open_time DESC
    """)
    
    open_trades = cursor.fetchall()
    if open_trades:
        for trade in open_trades:
            print(f"#{trade[0]}: {trade[2]} {trade[1]} @ {trade[3]:.2f} | "
                  f"SL: {trade[4]:.2f} | TP: {trade[5]:.2f} | "
                  f"Lots: {trade[6]:.2f} | Opened: {trade[7]}")
    else:
        print("No open positions - scanning for opportunities...")
    
    # Check log for recent activity
    print("\nRECENT LOG ACTIVITY:")
    print("-"*50)
    
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-10:]  # Last 10 lines
            for line in recent_lines:
                if any(keyword in line for keyword in ['TRADE OPENED', 'WIN', 'LOSS', 'TRAILING', 'PHASE']):
                    # Extract timestamp and message
                    parts = line.split(' - ')
                    if len(parts) >= 4:
                        timestamp = parts[0].split()[-1]  # Time only
                        message = parts[-1].strip()
                        print(f"{timestamp}: {message}")
    
    conn.close()
    print("\n" + "="*80)

if __name__ == "__main__":
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        monitor_ftmo_trading()
        time.sleep(30)  # Update every 30 seconds