#!/usr/bin/env python3
"""
Add a test trade to demonstrate the system
"""

from database import DatabaseManager, Trade
from datetime import datetime

def add_test_trade():
    """Add a sample trade for testing"""
    
    print("=== Adding Test Trade ===")
    
    db = DatabaseManager()
    
    # Create a sample trade
    test_trade = Trade(
        symbol="BTCUSDT",
        side="Buy",
        entry=45000.00,
        tp=47000.00,
        sl=43000.00,
        result="open",
        timestamp=datetime.now().isoformat()
    )
    
    try:
        trade_id = db.add_trade(test_trade)
        print(f"[SUCCESS] Added test trade with ID: {trade_id}")
        print(f"Symbol: {test_trade.symbol}")
        print(f"Side: {test_trade.side}")
        print(f"Entry: ${test_trade.entry}")
        print(f"TP: ${test_trade.tp}")
        print(f"SL: ${test_trade.sl}")
        
        print(f"\n[INFO] Go to http://localhost:8501 to see your trade in the dashboard!")
        
    except Exception as e:
        print(f"[ERROR] Failed to add trade: {e}")

if __name__ == "__main__":
    add_test_trade()