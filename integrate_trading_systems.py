#!/usr/bin/env python3
"""
Integrate the automated trading system with the dashboard
This will ensure both systems use the same database
"""

import sqlite3
import os
import shutil
from datetime import datetime

def integrate_databases():
    """Integrate trading.db and trade_log.db"""
    
    print("="*60)
    print("Trading System Integration")
    print("="*60)
    
    # 1. Backup existing databases
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if os.path.exists('trade_log.db'):
        backup_name = f'trade_log.db.backup_{timestamp}'
        shutil.copy2('trade_log.db', backup_name)
        print(f"[OK] Backed up trade_log.db to {backup_name}")
    
    if os.path.exists('trading.db'):
        backup_name = f'trading.db.backup_{timestamp}'
        shutil.copy2('trading.db', backup_name)
        print(f"[OK] Backed up trading.db to {backup_name}")
    
    # 2. Update the automated trading system to use trade_log.db
    print("\nUpdating automated trading system configuration...")
    
    files_to_update = [
        'trading_engine.py',
        'automated_signal_monitor.py',
        'trailing_take_profit.py',
        'market_analyzer.py',
        'position_monitor.py'
    ]
    
    for file in files_to_update:
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read()
            
            # Replace trading.db with trade_log.db
            if 'trading.db' in content:
                content = content.replace("'trading.db'", "'trade_log.db'")
                content = content.replace('"trading.db"', '"trade_log.db"')
                
                with open(file, 'w') as f:
                    f.write(content)
                
                print(f"  [OK] Updated {file}")
    
    # 3. Ensure trade_log.db has all necessary tables
    print("\nEnsuring all tables exist in trade_log.db...")
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Create signal_log table for automated trading
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message_id INTEGER,
            timestamp DATETIME,
            symbol TEXT,
            side TEXT,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            signal_type TEXT,
            raw_message TEXT,
            processed INTEGER DEFAULT 0,
            trade_executed INTEGER DEFAULT 0,
            execution_result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create trading_settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_settings (
            id INTEGER PRIMARY KEY,
            settings_json TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize default settings if not exists
    cursor.execute("SELECT COUNT(*) FROM trading_settings WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        default_settings = '''{
            "enabled": true,
            "max_daily_trades": 10,
            "position_size": 1000,
            "use_market_analysis": true,
            "trailing_take_profit": {
                "enabled": true,
                "target_profit_pct": 5.0,
                "activation_pct": 3.0,
                "trail_distance_pct": 1.5,
                "fallback_profit_pct": 3.5
            }
        }'''
        cursor.execute("INSERT INTO trading_settings (id, settings_json) VALUES (1, ?)", (default_settings,))
    
    # Copy market data tables from trading.db if they exist
    if os.path.exists('trading.db'):
        print("\nCopying market data from trading.db...")
        
        trading_conn = sqlite3.connect('trading.db')
        trading_cursor = trading_conn.cursor()
        
        # Get market_conditions table
        trading_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_conditions'")
        if trading_cursor.fetchone():
            # Create table
            trading_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='market_conditions'")
            create_sql = trading_cursor.fetchone()[0]
            cursor.execute(create_sql)
            
            # Copy data
            trading_cursor.execute("SELECT * FROM market_conditions")
            data = trading_cursor.fetchall()
            if data:
                cursor.executemany(
                    "INSERT OR IGNORE INTO market_conditions VALUES (" + ",".join(["?" for _ in range(len(data[0]))]) + ")",
                    data
                )
                print(f"  [OK] Copied {len(data)} market condition records")
        
        # Get volume_history table
        trading_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='volume_history'")
        if trading_cursor.fetchone():
            # Create table
            trading_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='volume_history'")
            create_sql = trading_cursor.fetchone()[0]
            cursor.execute(create_sql)
            
            # Copy data
            trading_cursor.execute("SELECT * FROM volume_history")
            data = trading_cursor.fetchall()
            if data:
                cursor.executemany(
                    "INSERT OR IGNORE INTO volume_history VALUES (" + ",".join(["?" for _ in range(len(data[0]))]) + ")",
                    data
                )
                print(f"  [OK] Copied {len(data)} volume history records")
        
        trading_conn.close()
    
    conn.commit()
    conn.close()
    
    print("\n[DONE] Integration complete!")
    print("\nNext steps:")
    print("1. Start the automated signal monitor:")
    print("   python automated_signal_monitor.py")
    print("\n2. The dashboard will now show all trades from both manual and automated systems")
    print("\n3. All systems now use trade_log.db as the single source of truth")

if __name__ == "__main__":
    integrate_databases()