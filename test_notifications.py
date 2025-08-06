#!/usr/bin/env python3
"""
Test the Telegram notification system
"""

import os
from dotenv import load_dotenv
from telegram_notifier import notifier

# Load environment variables
load_dotenv()

def test_notifications():
    """Test all notification types"""
    
    print("Testing Telegram Notifications...")
    
    # Test 1: New Signal
    print("\nTesting new signal notification...")
    test_signal = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 65000,
        'take_profit': 68250,
        'stop_loss': 61750,
        'channel': 'Test Channel',
        'risk_reward_ratio': '1:1.5',
        'position_size': 1000,
        'modified_tp': 68250,
        'modified_sl': 61750
    }
    
    if notifier.notify_new_signal(test_signal):
        print("New signal notification sent!")
    else:
        print("Failed to send new signal notification")
    
    # Test 2: Signal Processed (Success)
    print("\nTesting signal processed (success) notification...")
    if notifier.notify_signal_processed(test_signal, True):
        print("Signal processed notification sent!")
    else:
        print("Failed to send signal processed notification")
    
    # Test 3: Trade Opened
    print("\nTesting trade opened notification...")
    test_trade = {
        'id': 123,
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry': 65000,
        'tp': 68250,
        'sl': 61750,
        'position_size': 1000
    }
    
    if notifier.notify_trade_opened(test_trade):
        print("Trade opened notification sent!")
    else:
        print("Failed to send trade opened notification")
    
    # Test 4: Trade Closed (Profit)
    print("\nTesting trade closed notification...")
    test_closed_trade = {
        'id': 123,
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry': 65000,
        'exit_price': 67000,
        'exit_reason': 'tp',
        'pnl': 30.77,
        'pnl_pct': 3.08,
        'duration': '4.2 hours',
        'new_balance': 10030.77,
        'daily_pnl': 30.77,
        'win_rate': 75.0
    }
    
    if notifier.notify_trade_closed(test_closed_trade):
        print("Trade closed notification sent!")
    else:
        print("Failed to send trade closed notification")
    
    # Test 5: System Error
    print("\nTesting error notification...")
    if notifier.notify_error('Test Error', 'This is a test error message'):
        print("Error notification sent!")
    else:
        print("Failed to send error notification")
    
    print("\nAll notification tests completed!")
    print("Check your Telegram to see the test messages.")

if __name__ == "__main__":
    test_notifications()