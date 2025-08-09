"""
Simple Telegram test - sends a test message
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Get credentials
token = os.getenv('TELEGRAM_BOT_TOKEN', '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if not chat_id:
    print("ERROR: No TELEGRAM_CHAT_ID in .env file")
    print("\nRun this first:")
    print("  python get_chat_id.py")
    exit(1)

print(f"Sending test message to chat {chat_id}...")

# Create test message
message = f"""
BREAKOUT AUTOMATION TEST

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you see this message, your automation is configured correctly!

The system will send trade alerts in this format:

BUY BTCUSDT
Entry: 45000
Stop: 44500
Target: 46000
Size: $150

Ready to start? Run:
python breakout_integrated_automation.py
"""

# Send message
url = f'https://api.telegram.org/bot{token}/sendMessage'
response = requests.post(url, json={
    'chat_id': chat_id,
    'text': message
})

if response.status_code == 200:
    print("SUCCESS! Check your Telegram for the test message.")
else:
    print(f"Failed to send message. Error: {response.text}")