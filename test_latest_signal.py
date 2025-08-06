#!/usr/bin/env python3
"""
Test parsing of the latest signal and send notification
"""

import os
import sys
from signal_processor import SignalProcessor
from telegram_notifier import notifier
from dotenv import load_dotenv

load_dotenv()

def test_latest_signal():
    """Test parsing and notification for latest signal format"""
    
    # Use the exact format we see from SMRT Signals based on the logs
    test_signal_message = """ETHUSDT Sell
Entry: 3668.53
TP: 3594.425694
SL: 3812.6694622932"""
    
    print("Testing signal parsing with latest SMRT format:")
    print(f"Message:\n{test_signal_message}")
    print("-" * 50)
    
    # Parse the signal
    processor = SignalProcessor()
    signal_data = processor.parse_signal(test_signal_message)
    
    if signal_data:
        print("✅ Signal parsed successfully!")
        print(f"Symbol: {signal_data['symbol']}")
        print(f"Side: {signal_data['side']}")
        print(f"Entry: {signal_data['entry_price']}")
        print(f"Take Profit: {signal_data['take_profit']}")
        print(f"Stop Loss: {signal_data['stop_loss']}")
        
        # Add additional fields for notification
        signal_data['channel'] = 'SMRT Signals - Crypto Channel'
        signal_data['risk_reward_ratio'] = '1:1.5'
        signal_data['position_size'] = 1000
        signal_data['modified_tp'] = signal_data['take_profit']
        signal_data['modified_sl'] = signal_data['stop_loss']
        
        print("\nSending test notification to Telegram...")
        
        # Send notification
        success = notifier.notify_new_signal(signal_data)
        
        if success:
            print("✅ Test notification sent successfully!")
            print("Check your Telegram to verify the parsing is correct.")
        else:
            print("❌ Failed to send notification")
            
    else:
        print("❌ Failed to parse signal")
        return False
    
    return True

if __name__ == "__main__":
    test_latest_signal()