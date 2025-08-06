#!/usr/bin/env python3
"""
Simple Telegram verification
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

async def verify_and_authenticate():
    """Verify credentials and authenticate"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Telegram Verification ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    
    try:
        client = TelegramClient('temp_auth', int(api_id), api_hash)
        
        print("\n[STEP 1] Connecting...")
        await client.connect()
        print("[SUCCESS] Connected to Telegram")
        
        print(f"\n[STEP 2] Sending verification code to {phone}...")
        
        # Send verification code
        sent_code = await client.send_code_request(phone)
        print("[SUCCESS] Verification code sent! Check your phone")
        
        # Get the code from user
        code = input("\nEnter the verification code you received: ")
        
        print(f"\n[STEP 3] Signing in with code...")
        await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Authenticated!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        
        # Generate session string
        session_string = client.session.save()
        print(f"\n[IMPORTANT] Add this to your .env file:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        # Find the target group
        print(f"\n[STEP 4] Looking for your groups...")
        target_group = "SMRT Signals - Crypto Channel"
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                print(f"Group: {dialog.title}")
                if target_group.lower() in dialog.title.lower():
                    print(f"   [FOUND TARGET GROUP!]")
                    
        await client.disconnect()
        
        print(f"\n=== SETUP COMPLETE ===")
        print(f"1. Add the session string above to your .env file")
        print(f"2. Run: python telegram_user_client.py")
        print(f"3. The system will monitor '{target_group}' for signals")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        
        if "PHONE_NUMBER_INVALID" in str(e):
            print("Try phone format: +1XXXXXXXXXX")
        elif "api_id/api_hash combination is invalid" in str(e):
            print("Check your API credentials at https://my.telegram.org/apps")
        elif "PHONE_CODE_INVALID" in str(e):
            print("Invalid verification code - try again")

if __name__ == "__main__":
    asyncio.run(verify_and_authenticate())