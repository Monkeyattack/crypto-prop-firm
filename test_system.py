#!/usr/bin/env python3
"""
Test the crypto paper trading system components
"""

import os
from database import DatabaseManager
from signal_processor import SignalProcessor

def test_database():
    """Test database functionality"""
    print("=== Testing Database ===")
    try:
        db = DatabaseManager()
        
        # Test connection
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades")
            count = cursor.fetchone()[0]
            print(f"[SUCCESS] Database connected. Total trades: {count}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")
        return False

def test_signal_processor():
    """Test signal processing"""
    print("\n=== Testing Signal Processor ===")
    try:
        processor = SignalProcessor()
        
        test_signals = [
            """
            Buy BTCUSDT
            Entry: 45000
            TP: 47000
            SL: 43000
            """,
            """
            LONG ETHUSDT
            Entry: 2600
            Target: 2750
            Stop Loss: 2450
            """,
            """
            BUY $ADA @ 0.45 | TP: 0.50 | SL: 0.40
            """
        ]
        
        success_count = 0
        for i, signal in enumerate(test_signals, 1):
            result = processor.parse_signal(signal.strip())
            if result:
                print(f"[SUCCESS] Signal {i}: {result['symbol']} {result['side']} @ {result['entry']}")
                success_count += 1
            else:
                print(f"[FAILED] Signal {i}: Could not parse")
        
        print(f"[RESULT] Parsed {success_count}/{len(test_signals)} signals")
        return success_count > 0
        
    except Exception as e:
        print(f"[ERROR] Signal processor test failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("\n=== Testing Environment ===")
    
    required_vars = [
        'TELEGRAM_API_ID',
        'TELEGRAM_API_HASH', 
        'TELEGRAM_PHONE_NUMBER',
        'TELEGRAM_BOT_TOKEN'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
        else:
            print(f"[OK] {var} is set")
    
    if missing:
        print(f"[WARNING] Missing variables: {', '.join(missing)}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("=== Crypto Paper Trading System Test ===")
    
    results = {
        'database': test_database(),
        'signal_processor': test_signal_processor(),
        'environment': test_environment()
    }
    
    print(f"\n=== Test Results ===")
    for test, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n[SUCCESS] All tests passed!")
        print(f"Your system is ready for paper trading!")
        print(f"\nNext steps:")
        print(f"1. Dashboard: http://localhost:8501")
        print(f"2. Fix Telegram API credentials if needed")
        print(f"3. Start paper trading!")
    else:
        print(f"\n[WARNING] Some tests failed")
        print(f"Check the errors above and fix before proceeding")

if __name__ == "__main__":
    main()