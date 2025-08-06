#!/usr/bin/env python3
"""
Simple Telegram setup script for Windows
"""

import os
import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_telegram():
    """Setup Telegram user client"""
    
    print("\n=== Telegram User Client Setup ===")
    
    # Get credentials from .env
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    if not api_id or not api_hash:
        print("\n[ERROR] Missing Telegram API credentials!")
        print("   1. Make sure .env file has TELEGRAM_API_ID and TELEGRAM_API_HASH")
        print("   2. Run this script again")
        return
    
    if not phone:
        phone = input("Enter your phone number (with country code, e.g., +1234567890): ")
        if not phone:
            print("   [ERROR] Phone number is required")
            return
    
    print(f"\n[INFO] Connecting to Telegram...")
    print(f"   API ID: {api_id}")
    print(f"   Phone: {phone}")
    
    try:
        # Create client
        client = TelegramClient('temp_session', int(api_id), api_hash)
        
        # Connect and authenticate
        await client.start(phone=phone)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Connected!")
        print(f"   Name: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username}")
        print(f"   Phone: {me.phone}")
        
        # Generate session string
        session_string = client.session.save()
        print(f"\n[INFO] Session string generated:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        # List groups
        print(f"\n[INFO] Your Telegram groups:")
        print("-" * 50)
        
        groups = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                group_info = {
                    'id': dialog.entity.id,
                    'title': dialog.title,
                    'username': getattr(dialog.entity, 'username', None)
                }
                groups.append(group_info)
                
                print(f"Group: {group_info['title']}")
                print(f"   ID: {group_info['id']}")
                if group_info['username']:
                    print(f"   Username: @{group_info['username']}")
                print()
        
        # Generate configuration
        print("\n[INFO] Add this to your .env file:")
        print("-" * 50)
        print(f"TELEGRAM_API_ID={api_id}")
        print(f"TELEGRAM_API_HASH={api_hash}")
        print(f"TELEGRAM_PHONE_NUMBER={phone}")
        print(f'TELEGRAM_SESSION_STRING={session_string}')
        print(f'TELEGRAM_MONITORED_GROUPS="SMRT Signals - Crypto Channel"')
        
        await client.disconnect()
        
        print(f"\n[SUCCESS] Setup complete!")
        print(f"   1. Add the session string to your .env file")
        print(f"   2. Run: python telegram_user_client.py")
        print(f"   3. Start monitoring for signals!")
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        return

def main():
    """Main function"""
    try:
        asyncio.run(setup_telegram())
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Setup cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")

if __name__ == "__main__":
    main()