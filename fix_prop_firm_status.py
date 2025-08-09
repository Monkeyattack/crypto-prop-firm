#!/usr/bin/env python3
"""
Fix Prop Firm Status Database Issues
Reset and properly initialize the prop firm status table
"""

import sqlite3
from datetime import datetime

def fix_prop_firm_status(db_path="trade_log.db"):
    """Fix prop firm status table initialization"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Clear and reinitialize prop firm status table
        print("Fixing prop firm status table...")
        
        cursor.execute("DELETE FROM prop_firm_status")
        
        # Insert proper initial status
        cursor.execute("""
            INSERT INTO prop_firm_status 
            (id, is_trading_allowed, current_balance, daily_pnl, daily_trades,
             daily_loss_limit, max_drawdown_limit, profit_target,
             evaluation_passed, evaluation_failed, daily_reset_time, last_updated)
            VALUES (1, 1, 10000.0, 0.0, 0, 500.0, 600.0, 1000.0, 0, 0, ?, ?)
        """, (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        # Clear existing decisions to reset processing
        cursor.execute("DELETE FROM prop_firm_decisions")
        
        # Reset signal processing flags
        cursor.execute("""
            UPDATE signal_log 
            SET prop_firm_processed = 0,
                prop_firm_decision = NULL,
                prop_firm_reason = NULL
        """)
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT * FROM prop_firm_status WHERE id = 1")
        row = cursor.fetchone()
        
        if row:
            print("✅ Prop firm status fixed successfully!")
            print(f"   Current Balance: ${row[2]:.2f}")
            print(f"   Trading Allowed: {'Yes' if row[1] else 'No'}")
            print(f"   Daily P&L: ${row[3]:.2f}")
        else:
            print("❌ Failed to create status record")
            
        # Also verify daily_reset_time
        print(f"   Daily Reset Time: {row[8]}")
        print(f"   Last Updated: {row[11]}")
        
    except Exception as e:
        print(f"Error fixing prop firm status: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_prop_firm_status()
    print("\n🔄 Ready to test again. Run: python test_prop_firm_integration.py")