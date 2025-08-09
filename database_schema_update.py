#!/usr/bin/env python3
"""
Database Schema Update for Prop Firm Integration
Adds tables to track prop firm signal decisions and separate account statistics
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema(db_path="trade_log.db"):
    """Add prop firm tables to existing database"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Prop Firm Signal Decisions Table
        logger.info("Creating prop_firm_decisions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prop_firm_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,  -- References signal_log.id
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Signal Details
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                
                -- Risk Analysis
                risk_reward_ratio REAL,
                position_size_usd REAL,
                risk_percent REAL,
                
                -- Decision
                decision TEXT,  -- 'ACCEPTED', 'REJECTED'
                reason TEXT,    -- Detailed reason for decision
                
                -- Context
                daily_loss REAL,
                daily_loss_limit REAL,
                current_drawdown REAL,
                max_drawdown_limit REAL,
                daily_trades_count INTEGER,
                
                -- Action Taken
                telegram_sent INTEGER DEFAULT 0,
                alert_message TEXT,
                
                FOREIGN KEY (signal_id) REFERENCES signal_log (id)
            )
        """)
        
        # 2. Prop Firm Account Statistics Table
        logger.info("Creating prop_firm_stats table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prop_firm_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,  -- Daily stats record
                
                -- Account Balances
                starting_balance REAL,
                ending_balance REAL,
                peak_balance REAL,
                
                -- Daily Metrics
                daily_pnl REAL,
                daily_pnl_percent REAL,
                daily_trades INTEGER,
                daily_wins INTEGER,
                daily_losses INTEGER,
                
                -- Risk Metrics
                max_drawdown REAL,
                current_drawdown REAL,
                max_daily_loss REAL,
                
                -- Progress
                profit_target REAL,
                profit_achieved REAL,
                progress_percent REAL,
                
                -- Status Flags
                evaluation_active INTEGER DEFAULT 1,
                daily_limit_hit INTEGER DEFAULT 0,
                drawdown_limit_hit INTEGER DEFAULT 0,
                
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Real-time Prop Firm Status Table
        logger.info("Creating prop_firm_status table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prop_firm_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single row table
                
                -- Current Status
                is_trading_allowed INTEGER DEFAULT 1,
                current_balance REAL DEFAULT 10000.00,
                daily_pnl REAL DEFAULT 0.00,
                daily_trades INTEGER DEFAULT 0,
                
                -- Limits
                daily_loss_limit REAL DEFAULT 500.00,
                max_drawdown_limit REAL DEFAULT 600.00,
                profit_target REAL DEFAULT 1000.00,
                
                -- Evaluation Status
                evaluation_passed INTEGER DEFAULT 0,
                evaluation_failed INTEGER DEFAULT 0,
                
                -- Timestamps
                last_trade_time DATETIME,
                daily_reset_time DATETIME,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert initial status record
        cursor.execute("""
            INSERT OR IGNORE INTO prop_firm_status (id, current_balance, daily_reset_time) 
            VALUES (1, 10000.00, datetime('now'))
        """)
        
        # 4. Create indexes for performance
        logger.info("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prop_decisions_timestamp ON prop_firm_decisions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prop_decisions_signal_id ON prop_firm_decisions(signal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prop_decisions_decision ON prop_firm_decisions(decision)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prop_stats_date ON prop_firm_stats(date)")
        
        # 5. Add columns to existing signal_log if they don't exist
        logger.info("Updating signal_log table...")
        try:
            cursor.execute("ALTER TABLE signal_log ADD COLUMN prop_firm_processed INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE signal_log ADD COLUMN prop_firm_decision TEXT")
            cursor.execute("ALTER TABLE signal_log ADD COLUMN prop_firm_reason TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                logger.warning(f"Could not add columns to signal_log: {e}")
        
        conn.commit()
        logger.info("Database schema updated successfully!")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'prop_firm%'")
        tables = cursor.fetchall()
        logger.info(f"Prop firm tables created: {[table[0] for table in tables]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_schema(db_path="trade_log.db"):
    """Verify the new schema was created correctly"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if all tables exist
        required_tables = [
            'prop_firm_decisions',
            'prop_firm_stats', 
            'prop_firm_status'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone()[0] == 0:
                logger.error(f"Table {table} was not created!")
                return False
            else:
                logger.info(f"✓ Table {table} exists")
                
        # Check initial data
        cursor.execute("SELECT * FROM prop_firm_status")
        status = cursor.fetchone()
        if status:
            logger.info(f"✓ Initial prop firm status record created: Balance=${status[1]}")
        else:
            logger.warning("No initial status record found")
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying schema: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Updating database schema for prop firm integration...")
    
    if update_database_schema():
        print("\n✅ Schema update completed successfully!")
        
        print("\nVerifying schema...")
        if verify_schema():
            print("✅ Schema verification passed!")
        else:
            print("❌ Schema verification failed!")
    else:
        print("❌ Schema update failed!")
    
    print("\nYou can now use the enhanced dashboard with prop firm integration.")