#!/usr/bin/env python3
"""
Authenticate with Telegram and generate session string
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def authenticate():
    """Authenticate with Telegram and generate session"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Telegram Authentication ===")
    print(f"Phone: {phone}")
    
    try:
        # Create client with string session
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        # Start the client and authenticate
        await client.start(phone=phone)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Authenticated!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        
        # Generate session string
        session_string = client.session.save()
        print(f"\n[IMPORTANT] Save this session string to your .env file:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        # List relevant groups
        print(f"\n[INFO] Looking for 'SMRT Signals - Crypto Channel'...")
        
        target_group = "SMRT Signals - Crypto Channel"
        found_group = False
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                if target_group.lower() in dialog.title.lower():
                    print(f"[FOUND] {dialog.title}")
                    print(f"   ID: {dialog.entity.id}")
                    found_group = True
                elif "smrt" in dialog.title.lower() or "signal" in dialog.title.lower():
                    print(f"[SIMILAR] {dialog.title}")
                    print(f"   ID: {dialog.entity.id}")
        
        if not found_group:
            print(f"[INFO] Target group not found. All your groups:")
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    print(f"   - {dialog.title}")
        
        await client.disconnect()
        
        print(f"\n[NEXT STEPS]")
        print(f"1. Add the session string to your .env file")
        print(f"2. Update TELEGRAM_MONITORED_GROUPS if needed")
        print(f"3. Run: python telegram_user_client.py")
        
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")

if __name__ == "__main__":
    asyncio.run(authenticate())