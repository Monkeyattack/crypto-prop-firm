#!/usr/bin/env python3
"""Check both databases to understand the discrepancy"""

import sqlite3
import pandas as pd

def check_database(db_path, db_name):
    """Check database structure and content"""
    print(f"\n{'='*60}")
    print(f"Checking {db_name}: {db_path}")
    print('='*60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\nTables found: {[t[0] for t in tables]}")
        
        # Check for trades-related tables
        for table in tables:
            table_name = table[0]
            if 'trade' in table_name.lower():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"\n{table_name}: {count} records")
                
                # Show sample records
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"Columns: {[col[1] for col in columns]}")
                
                # Show first few records
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                records = cursor.fetchall()
                if records:
                    print(f"\nFirst few records:")
                    for i, record in enumerate(records):
                        print(f"  {i+1}: {record}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking {db_name}: {e}")

# Check both databases
check_database('trade_log.db', 'trade_log.db (Dashboard DB)')
check_database('trading.db', 'trading.db (Automated Trading DB)')

# Check if we need to migrate data
print("\n" + "="*60)
print("ANALYSIS:")
print("="*60)
print("\nThe dashboard is using 'trade_log.db' while the automated trading")
print("system is using 'trading.db'. This explains why you see only 4 trades")
print("in the dashboard but 23 trades exist in the automated system.")
print("\nTo fix this, we need to either:")
print("1. Point the automated trading system to use trade_log.db")
print("2. Point the dashboard to use trading.db")
print("3. Migrate data from trading.db to trade_log.db")