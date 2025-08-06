#!/usr/bin/env python3
"""
Final Telegram authentication - Run this locally to complete setup
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def complete_authentication():
    """Complete Telegram authentication"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Telegram Authentication - Final Step ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\n[STEP 1] Connecting...")
        await client.connect()
        
        print(f"[STEP 2] Sending verification code to {phone}...")
        sent_code = await client.send_code_request(phone)
        
        print("\n" + "="*60)
        print("CHECK YOUR PHONE FOR VERIFICATION CODE!")
        print("="*60)
        
        code = input("\nEnter the verification code you received: ")
        
        print(f"\n[STEP 3] Authenticating...")
        await client.sign_in(phone, code)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Authenticated successfully!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        
        # Generate session string
        session_string = client.session.save()
        
        print(f"\n" + "="*60)
        print("IMPORTANT: ADD THIS TO YOUR .env FILE")
        print("="*60)
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print("="*60)
        
        # Find target group
        print(f"\n[STEP 4] Looking for your groups...")
        target_group = "SMRT Signals - Crypto Channel"
        found_target = False
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                print(f"Found group: {dialog.title}")
                if target_group.lower() in dialog.title.lower():
                    print(f"   >>> TARGET GROUP FOUND! <<<")
                    found_target = True
        
        if not found_target:
            print(f"\n[WARNING] Target group '{target_group}' not found")
            print("Make sure:")
            print("1. You're a member of the group")
            print("2. The group name is exactly correct")
        
        await client.disconnect()
        
        print(f"\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("Next steps:")
        print("1. Add the session string above to your .env file")
        print("2. Run: python telegram_user_client.py")
        print("3. Monitor for signals from SMRT Signals - Crypto Channel")
        print("4. Check dashboard at http://localhost:8501")
        
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        
        if "PHONE_CODE_INVALID" in str(e):
            print("The verification code was incorrect. Try running the script again.")
        elif "PHONE_CODE_EXPIRED" in str(e):
            print("The verification code expired. Run the script again for a new code.")

if __name__ == "__main__":
    print("IMPORTANT: Run this script locally on your machine to enter the verification code")
    print("The code will be sent to your phone: +14692238202")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
        asyncio.run(complete_authentication())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")