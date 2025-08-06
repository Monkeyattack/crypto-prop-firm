#!/usr/bin/env python3
"""
Test Telegram API credentials
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

async def test_api():
    """Test API credentials"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    print("=== Testing Telegram API Credentials ===")
    print(f"API ID: {api_id}")
    print(f"API Hash: {api_hash[:10]}..." if api_hash else "None")
    
    if not api_id or not api_hash:
        print("\n[ERROR] Missing credentials in .env file")
        return
    
    try:
        client = TelegramClient('test_session', int(api_id), api_hash)
        await client.connect()
        
        if await client.is_user_authorized():
            print("\n[SUCCESS] Already authorized!")
        else:
            print(f"\n[INFO] Not authorized yet - need to authenticate with phone")
            print(f"[INFO] This is normal for first setup")
        
        await client.disconnect()
        print("[INFO] Connection test successful")
        
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\nPossible issues:")
        print("1. Invalid API ID or API Hash")
        print("2. Network connectivity issues")
        print("3. Need to create Telegram application at https://my.telegram.org/apps")

if __name__ == "__main__":
    asyncio.run(test_api())