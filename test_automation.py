"""
Quick test script to verify the Breakout automation is working
Tests both Telegram connection and signal reading
"""

import asyncio
import sqlite3
import os
from datetime import datetime
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_telegram_connection():
    """Test 1: Verify Telegram bot can send messages"""
    print("\n=== TEST 1: Telegram Connection ===")
    
    # Load credentials
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ ERROR: Telegram credentials not found in .env")
        return False
    
    print(f"Token: {token[:20]}...")
    print(f"Chat ID: {chat_id}")
    
    # Send test message
    import aiohttp
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    test_message = {
        'chat_id': chat_id,
        'text': f"""
✅ **Telegram Test Successful!**

Time: {datetime.now().strftime('%H:%M:%S')}

Your bot is working correctly.
The automation system can send you alerts.

Next: Testing signal database...
        """,
        'parse_mode': 'Markdown'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=test_message) as response:
                if response.status == 200:
                    print("✅ Telegram message sent successfully!")
                    print("   Check your Telegram for the test message")
                    return True
                else:
                    print(f"❌ Failed to send: {await response.text()}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_signal_database():
    """Test 2: Check if we can read signals from the database"""
    print("\n=== TEST 2: Signal Database ===")
    
    db_path = 'trade_log.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check signal_log table
        cursor.execute("SELECT COUNT(*) FROM signal_log")
        total_signals = cursor.fetchone()[0]
        print(f"✅ Total signals in database: {total_signals}")
        
        # Get latest signal
        cursor.execute("""
            SELECT id, symbol, side, entry_price, stop_loss, take_profit, timestamp
            FROM signal_log 
            WHERE symbol IS NOT NULL 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        latest = cursor.fetchone()
        if latest:
            print(f"✅ Latest signal:")
            print(f"   ID: {latest[0]}")
            print(f"   Symbol: {latest[1]}")
            print(f"   Side: {latest[2]}")
            print(f"   Entry: {latest[3]}")
            print(f"   SL: {latest[4]}")
            print(f"   TP: {latest[5]}")
            print(f"   Time: {latest[6]}")
        else:
            print("   No signals with complete data found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_prop_firm_rules():
    """Test 3: Verify prop firm validation is working"""
    print("\n=== TEST 3: Prop Firm Rules ===")
    
    try:
        from prop_firm_manager import PropFirmManager
        
        manager = PropFirmManager()
        status = manager.get_status_report()
        
        print(f"✅ Prop Firm Manager initialized")
        print(f"   Balance: {status['account']['current_balance']}")
        print(f"   Progress: {status['progress']['progress_percent']}")
        print(f"   Daily Loss Used: {status['limits']['daily_loss_used']}")
        print(f"   Drawdown Used: {status['limits']['drawdown_used']}")
        print(f"   Trading Allowed: {status['status']['is_trading_allowed']}")
        
        # Test a trade validation
        can_trade, reason, params = manager.can_open_trade(
            symbol="BTCUSDT",
            position_size=150,
            stop_loss_amount=150
        )
        
        print(f"\n   Test Trade (BTC $150):")
        print(f"   Can Trade: {can_trade}")
        print(f"   Reason: {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_full_integration():
    """Test 4: Send a sample trade alert"""
    print("\n=== TEST 4: Sample Trade Alert ===")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    sample_alert = f"""
🚨🚨🚨 **BREAKOUT TRADE ALERT (TEST)** 🚨🚨🚨

🟢 **BUY BTCUSDT**

📍 **Entry**: 45250.0000
🛑 **Stop Loss**: 44800.0000
🎯 **Take Profit**: 46150.0000

💰 **Position Size**: $150.00
⚡ **Leverage**: 5x
⚠️ **Risk**: $150.00
📊 **RR Ratio**: 2.00

🔧 **Account Mode**: evaluation_normal
📝 **Note**: This is a TEST alert - DO NOT EXECUTE

**QUICK EXECUTION:**
1️⃣ Open Breakout Terminal
2️⃣ Go to BTCUSDT
3️⃣ BUY $150.00 @ 45250.0000
4️⃣ SL: 44800.0000 | TP: 46150.0000
5️⃣ Leverage: 5x

⏰ Signal ID: #TEST
📅 Time: {datetime.now().strftime('%H:%M:%S')}

**This is a test - no action needed**
    """
    
    import aiohttp
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                'chat_id': chat_id,
                'text': sample_alert,
                'parse_mode': 'Markdown'
            }) as response:
                if response.status == 200:
                    print("✅ Sample trade alert sent!")
                    print("   Check Telegram for the formatted alert")
                    return True
                else:
                    print(f"❌ Failed: {await response.text()}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("BREAKOUT AUTOMATION SYSTEM TEST")
    print("=" * 50)
    
    # Test 1: Telegram
    telegram_ok = await test_telegram_connection()
    await asyncio.sleep(2)
    
    # Test 2: Database
    db_ok = test_signal_database()
    
    # Test 3: Prop Firm Rules
    prop_ok = await test_prop_firm_rules()
    
    # Test 4: Sample Alert
    alert_ok = await test_full_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Telegram Connection: {'✅ PASS' if telegram_ok else '❌ FAIL'}")
    print(f"Signal Database:     {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"Prop Firm Rules:     {'✅ PASS' if prop_ok else '❌ FAIL'}")
    print(f"Alert Formatting:    {'✅ PASS' if alert_ok else '❌ FAIL'}")
    
    if all([telegram_ok, db_ok, prop_ok, alert_ok]):
        print("\n🎉 ALL TESTS PASSED! System is ready to use.")
        print("\nTo start the automation, run:")
        print("  python breakout_integrated_automation.py")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above.")

if __name__ == "__main__":
    # Check for required packages
    try:
        import aiohttp
        import dotenv
    except ImportError:
        print("Missing required packages. Install with:")
        print("  pip install aiohttp python-dotenv")
        sys.exit(1)
    
    # Run tests
    asyncio.run(main())