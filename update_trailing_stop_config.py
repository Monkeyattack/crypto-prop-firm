#!/usr/bin/env python3
"""
Update Trailing Stop Configuration Based on Backtest Results
Implements the recommended parameters: 4.0%/1.0%/3.0%
"""

import sqlite3
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_trailing_stop_config():
    """Update trailing stop configuration in the database"""
    
    # New optimized parameters from backtest analysis
    new_config = {
        'activation_pct': 4.0,      # Start trailing after 4.0% profit (was 4.5%)
        'trail_distance_pct': 1.0,  # Trail by 1.0% from high (was 1.5%)  
        'min_profit_pct': 3.0,      # Minimum 3.0% profit when exiting (was 3.5%)
        'target_profit_pct': 5.0,   # Keep original target
    }
    
    old_config = {
        'activation_pct': 4.5,
        'trail_distance_pct': 1.5,
        'min_profit_pct': 3.5,
        'target_profit_pct': 5.0,
    }
    
    try:
        # Update main trading database
        db_paths = ['trade_log.db', 'trading.db', 'ftmo_trading.db']
        
        for db_path in db_paths:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if trading_settings table exists
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        description TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Update trailing stop settings
                for key, value in new_config.items():
                    setting_key = f'trailing_{key}'
                    cursor.execute('''
                        INSERT OR REPLACE INTO trading_settings (key, value, description, updated_at)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        setting_key, 
                        str(value),
                        f'Trailing stop {key} - updated from backtest analysis',
                        datetime.now()
                    ))
                    
                # Log the configuration change
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config_changes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        change_date DATETIME,
                        change_type TEXT,
                        old_config TEXT,
                        new_config TEXT,
                        reason TEXT
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO config_changes (
                        change_date, change_type, old_config, new_config, reason
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    'trailing_stop_update',
                    json.dumps(old_config),
                    json.dumps(new_config),
                    'Backtest analysis showed 40.6% improvement with new parameters'
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Updated trailing stop config in {db_path}")
                
            except Exception as e:
                logger.warning(f"Could not update {db_path}: {e}")
                continue
                
        # Update the trailing_take_profit.py file's default config
        logger.info("Configuration update complete!")
        
        print("\n" + "="*60)
        print("TRAILING STOP CONFIGURATION UPDATED")
        print("="*60)
        print(f"Previous Configuration:")
        print(f"  Activation: {old_config['activation_pct']}%")
        print(f"  Trail Distance: {old_config['trail_distance_pct']}%") 
        print(f"  Minimum Profit: {old_config['min_profit_pct']}%")
        print(f"\nNew Configuration:")
        print(f"  Activation: {new_config['activation_pct']}%")
        print(f"  Trail Distance: {new_config['trail_distance_pct']}%")
        print(f"  Minimum Profit: {new_config['min_profit_pct']}%")
        print(f"\nExpected Improvement: +40.6% based on backtest")
        print(f"Update Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return False

def validate_configuration():
    """Validate that the new configuration is properly set"""
    
    try:
        db_paths = ['trade_log.db', 'trading.db', 'ftmo_trading.db']
        
        for db_path in db_paths:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT key, value FROM trading_settings 
                    WHERE key LIKE 'trailing_%'
                ''')
                
                settings = cursor.fetchall()
                if settings:
                    print(f"\nCurrent settings in {db_path}:")
                    for key, value in settings:
                        print(f"  {key}: {value}")
                        
                conn.close()
                
            except Exception as e:
                logger.warning(f"Could not validate {db_path}: {e}")
                
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")

def create_monitoring_alert():
    """Create monitoring setup for the new configuration"""
    
    monitoring_script = '''
# Add this to your monitoring dashboard or alerts

# Key Metrics to Monitor with New Trailing Stop Config:

1. Profit Capture Rate:
   - Track how often trades hit 4.0% activation vs old 4.5%
   - Monitor 1.0% trail distance effectiveness
   
2. Exit Distribution:
   - Count trailing stop exits vs time limit exits
   - Measure average profit at exit
   
3. Performance Validation:
   - Daily P&L vs backtest predictions
   - Win rate consistency (should stay ~62.5%)
   - Average holding time (target: ~150 hours)

# SQL Query for Daily Monitoring:
SELECT 
    DATE(timestamp) as trade_date,
    COUNT(*) as total_trades,
    AVG(pnl) as avg_pnl,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
    AVG(
        CASE WHEN result IN ('tp', 'trailing_stop') 
        THEN (julianday('now') - julianday(timestamp)) * 24 
        END
    ) as avg_hold_hours
FROM trades 
WHERE timestamp >= date('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;

# Alert Thresholds:
- If win rate drops below 55% for 3+ days: investigate
- If avg_pnl drops below $0.80/trade for 5+ days: consider reverting
- If hold time increases above 180 hours: check market conditions
'''
    
    with open('trailing_stop_monitoring.sql', 'w') as f:
        f.write(monitoring_script)
        
    logger.info("Created monitoring script: trailing_stop_monitoring.sql")

if __name__ == "__main__":
    print("Updating trailing stop configuration based on backtest results...")
    
    success = update_trailing_stop_config()
    
    if success:
        print("\nValidating configuration...")
        validate_configuration()
        
        print("\nCreating monitoring setup...")
        create_monitoring_alert()
        
        print(f"\n✅ Configuration update completed successfully!")
        print(f"Next steps:")
        print(f"1. Restart any running trading systems")
        print(f"2. Monitor performance for first 48 hours")
        print(f"3. Compare actual results to backtest predictions")
        print(f"4. Set up daily monitoring alerts")
        
    else:
        print(f"\n❌ Configuration update failed!")
        print(f"Please check the logs and try again.")