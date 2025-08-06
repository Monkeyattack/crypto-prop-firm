#!/usr/bin/env python3
"""Comprehensive database check to find the 23 trades"""

import sqlite3
import pandas as pd

# Check trading.db for all tables including those that might not be created yet
print("="*60)
print("Checking trading.db comprehensively")
print("="*60)

try:
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"\nTables in trading.db: {tables}")
    
    # Look for signal_log table
    if 'signal_log' in tables:
        cursor.execute("SELECT COUNT(*) FROM signal_log")
        count = cursor.fetchone()[0]
        print(f"\nsignal_log table: {count} records")
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE processed = 1")
        processed = cursor.fetchone()[0]
        print(f"Processed signals: {processed}")
        
        # Show some records
        cursor.execute("SELECT * FROM signal_log WHERE processed = 1 LIMIT 5")
        records = cursor.fetchall()
        if records:
            print("\nProcessed signals:")
            for r in records:
                print(f"  {r}")
    
    # Check if trades table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        print(f"\ntrades table exists with {count} records")
        
        cursor.execute("SELECT * FROM trades LIMIT 5")
        records = cursor.fetchall()
        if records:
            print("\nTrade records:")
            for r in records:
                print(f"  {r}")
    else:
        print("\ntrades table does NOT exist in trading.db")
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")

# Check where the trading engine is creating trades
print("\n" + "="*60)
print("Checking if trades table needs to be created")
print("="*60)

# Let's create the trades table if it doesn't exist
try:
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    
    # Create trades table matching what trading_engine.py expects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            entry REAL NOT NULL,
            tp REAL NOT NULL,
            sl REAL NOT NULL,
            result TEXT DEFAULT 'open',
            pnl REAL DEFAULT 0.0,
            timestamp DATETIME,
            exit_time DATETIME,
            exit_price REAL,
            profit_loss REAL DEFAULT 0.0
        )
    ''')
    
    conn.commit()
    print("trades table created/verified in trading.db")
    
    # Check signal_log for signals that should have created trades
    cursor.execute('''
        SELECT symbol, side, entry_price, take_profit, stop_loss, processed, trade_executed, timestamp
        FROM signal_log
        WHERE processed = 1
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    
    signals = cursor.fetchall()
    if signals:
        print(f"\nFound {len(signals)} processed signals:")
        for s in signals:
            print(f"  {s[0]} {s[1]} @ {s[2]}, TP: {s[3]}, SL: {s[4]}, Executed: {s[6]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")