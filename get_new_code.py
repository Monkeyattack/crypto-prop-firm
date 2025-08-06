#!/usr/bin/env python3
"""
Get a fresh verification code for Telegram
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def get_fresh_code():
    """Request a new verification code"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Getting Fresh Telegram Verification Code ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\n[STEP 1] Connecting to Telegram...")
        await client.connect()
        
        print(f"[STEP 2] Requesting new verification code for {phone}...")
        sent_code = await client.send_code_request(phone)
        
        print(f"\n" + "="*60)
        print("NEW VERIFICATION CODE SENT!")
        print("="*60)
        print(f"Check your phone: {phone}")
        print("You should receive an SMS with a new 5-digit code")
        print("="*60)
        
        print(f"\nCode hash: {sent_code.phone_code_hash}")
        print(f"Phone code hash (for reference): {sent_code.phone_code_hash[:20]}...")
        
        await client.disconnect()
        
        print(f"\n[NEXT STEP]")
        print(f"When you receive the new code, tell me:")
        print(f"'The new verification code is: XXXXX'")
        print(f"And I'll complete the authentication immediately!")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to request code: {e}")
        
        if "FLOOD_WAIT" in str(e):
            print("Too many requests. Wait a few minutes before trying again.")
        else:
            print("Check your internet connection and API credentials.")

if __name__ == "__main__":
    asyncio.run(get_fresh_code())