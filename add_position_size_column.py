#!/usr/bin/env python3
"""
Add position_size column to trades table for equity-based position sizing
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_position_size_column():
    """Add position_size column to trades table"""
    try:
        conn = sqlite3.connect('trade_log.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'position_size' not in columns:
            # Add position_size column
            cursor.execute('ALTER TABLE trades ADD COLUMN position_size REAL DEFAULT 1000.0')
            logger.info("✅ Added position_size column to trades table")
        else:
            logger.info("✅ position_size column already exists")
        
        # Also check for exit_price and exit_time columns
        if 'exit_price' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN exit_price REAL')
            logger.info("✅ Added exit_price column to trades table")
        
        if 'exit_time' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN exit_time TEXT')
            logger.info("✅ Added exit_time column to trades table")
        
        if 'profit_loss' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN profit_loss REAL')
            logger.info("✅ Added profit_loss column to trades table")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database schema updated successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error updating database schema: {e}")

if __name__ == "__main__":
    add_position_size_column()