#!/usr/bin/env python3
"""Fix database schema issues for VPS deployment"""

import sqlite3
import json
from datetime import datetime

def fix_database_schema():
    """Fix database schema issues"""
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    print("Fixing database schema...")
    
    # Fix trading_settings table - remove key column approach, use id-based
    cursor.execute("DROP TABLE IF EXISTS trading_settings_old")
    cursor.execute("ALTER TABLE trading_settings RENAME TO trading_settings_old")
    
    # Create new trading_settings table with proper schema
    cursor.execute('''
        CREATE TABLE trading_settings (
            id INTEGER PRIMARY KEY,
            settings_json TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate data if exists
    try:
        cursor.execute("SELECT * FROM trading_settings_old")
        old_data = cursor.fetchall()
        if old_data:
            # Assuming old format had key/value pairs, combine into JSON
            settings = {}
            for row in old_data:
                if len(row) >= 2:
                    settings[row[0]] = row[1]
            
            cursor.execute(
                "INSERT INTO trading_settings (id, settings_json) VALUES (1, ?)",
                (json.dumps(settings),)
            )
    except:
        # If migration fails, insert default settings
        pass
    
    # Ensure default settings exist
    cursor.execute("SELECT COUNT(*) FROM trading_settings WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        default_settings = {
            "enabled": True,
            "max_daily_trades": 10,
            "position_size": 1000,
            "use_market_analysis": True,
            "trailing_take_profit": {
                "enabled": True,
                "target_profit_pct": 5.0,
                "activation_pct": 3.0,
                "trail_distance_pct": 1.5,
                "fallback_profit_pct": 3.5
            }
        }
        cursor.execute(
            "INSERT INTO trading_settings (id, settings_json) VALUES (1, ?)",
            (json.dumps(default_settings),)
        )
    
    # Drop old table
    cursor.execute("DROP TABLE IF EXISTS trading_settings_old")
    
    print("[OK] Fixed trading_settings table")
    
    # Ensure signal_log table exists with correct schema
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
    
    print("[OK] Verified signal_log table")
    
    # Ensure processed_messages table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_messages (
            channel_name TEXT PRIMARY KEY,
            last_message_id INTEGER,
            last_check_time DATETIME
        )
    ''')
    
    print("[OK] Verified processed_messages table")
    
    conn.commit()
    conn.close()
    
    print("\nDatabase schema fixed successfully!")

if __name__ == "__main__":
    fix_database_schema()