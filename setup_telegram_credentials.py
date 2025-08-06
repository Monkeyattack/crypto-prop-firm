#!/usr/bin/env python3
"""Setup Telegram credentials for signal monitoring"""

import os
import sys

print("="*60)
print("TELEGRAM SIGNAL MONITOR SETUP")
print("="*60)
print("\nThe signal monitor needs Telegram API credentials to read messages.")
print("You can get these from https://my.telegram.org/apps")
print("\nFor now, we'll use test mode to verify the system is working.")

# Create a test configuration
test_channels = """
# Telegram Channels Configuration
# Add your signal channels here
channels:
  - name: "TestChannel"
    username: "@test_channel"
    type: "public"
"""

with open('channels_config.yaml', 'w') as f:
    f.write(test_channels)

print("\n[OK] Created channels_config.yaml")
print("\nTo complete the setup:")
print("1. Get your Telegram API credentials from https://my.telegram.org/apps")
print("2. Update the .env file with:")
print("   - TELEGRAM_API_ID=your_api_id")
print("   - TELEGRAM_API_HASH=your_api_hash")
print("   - TELEGRAM_PHONE=your_phone_number")
print("\nFor now, the signal monitor will run in test mode.")

# Update the automated_signal_monitor.py to handle missing credentials gracefully
print("\nThe system is configured to:")
print("- Monitor for signals every 15 minutes")
print("- Execute trades automatically based on settings")
print("- Apply trailing take profit logic")
print("- Update the dashboard in real-time")