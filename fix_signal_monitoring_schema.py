#!/usr/bin/env python3
"""
Fix signal monitoring database schema issues
"""

import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_signal_monitoring_schema():
    """Fix database schema for signal monitoring dashboard"""
    try:
        conn = sqlite3.connect('trade_log.db')
        cursor = conn.cursor()
        
        # Check current trading_settings table structure
        cursor.execute("PRAGMA table_info(trading_settings)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Current trading_settings columns: {columns}")
        
        # If using old structure, migrate to new structure
        if 'key' in columns and 'value' in columns:
            logger.info("Found old key-value structure, migrating to JSON structure...")
            
            # Get existing settings
            cursor.execute("SELECT key, value FROM trading_settings")
            old_settings = dict(cursor.fetchall())
            
            # Drop old table
            cursor.execute("DROP TABLE trading_settings")
            
            # Create new table with JSON structure
            cursor.execute('''
                CREATE TABLE trading_settings (
                    id INTEGER PRIMARY KEY,
                    settings_json TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Convert old settings to JSON format
            json_settings = {
                "enabled": old_settings.get('automated_trading_enabled', 'true') == 'true',
                "max_daily_trades": int(old_settings.get('max_daily_trades', 10)),
                "use_market_analysis": True,
                "position_sizing_method": "equity_based",
                "risk_per_trade_pct": 2.0,
                "max_portfolio_risk_pct": 10.0,
                "max_position_size_pct": 20.0,
                "min_position_size_usd": 100.0,
                "max_position_size_usd": 5000.0,
                "trailing_take_profit": {
                    "enabled": True,
                    "target_profit_pct": 5.0,
                    "activation_pct": 3.0,
                    "trail_distance_pct": 1.5,
                    "fallback_profit_pct": 3.5
                },
                "stop_loss_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_open_positions": 5,
                "market_analysis_enabled": True,
                "skip_poor_market_conditions": True,
                "volatility_adjustment_enabled": True
            }
            
            # Insert converted settings
            cursor.execute('''
                INSERT INTO trading_settings (id, settings_json)
                VALUES (1, ?)
            ''', (json.dumps(json_settings, indent=2),))
            
            logger.info("✅ Migrated old settings to new JSON structure")
        
        elif 'settings_json' not in columns:
            logger.info("Creating new trading_settings table with JSON structure...")
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_settings (
                    id INTEGER PRIMARY KEY,
                    settings_json TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add default settings
            default_settings = {
                "enabled": True,
                "max_daily_trades": 10,
                "use_market_analysis": True,
                "position_sizing_method": "equity_based",
                "risk_per_trade_pct": 2.0,
                "max_portfolio_risk_pct": 10.0,
                "max_position_size_pct": 20.0,
                "min_position_size_usd": 100.0,
                "max_position_size_usd": 5000.0,
                "trailing_take_profit": {
                    "enabled": True,
                    "target_profit_pct": 5.0,
                    "activation_pct": 3.0,
                    "trail_distance_pct": 1.5,
                    "fallback_profit_pct": 3.5
                },
                "stop_loss_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_open_positions": 5,
                "market_analysis_enabled": True,
                "skip_poor_market_conditions": True,
                "volatility_adjustment_enabled": True
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO trading_settings (id, settings_json)
                VALUES (1, ?)
            ''', (json.dumps(default_settings, indent=2),))
            
            logger.info("✅ Created trading_settings table with default settings")
        
        else:
            logger.info("✅ trading_settings table already has correct structure")
        
        # Ensure signal_log table exists
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
                processed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ensure processed_messages table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_messages (
                channel_name TEXT PRIMARY KEY,
                last_message_id INTEGER,
                last_check_time DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Signal monitoring database schema fixed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error fixing signal monitoring schema: {e}")

if __name__ == "__main__":
    fix_signal_monitoring_schema()