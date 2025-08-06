#!/usr/bin/env python3
"""
Complete Telegram session setup for VPS deployment
Run this on the VPS to authenticate once and save session
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def setup_telegram_session():
    """Set up Telegram session on VPS"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== VPS Telegram Session Setup ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    
    if not api_id or not api_hash or not phone:
        print("ERROR: Missing Telegram credentials in .env file")
        return False
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\nConnecting to Telegram...")
        await client.connect()
        
        print(f"Sending verification code to {phone}...")
        sent_code = await client.send_code_request(phone)
        
        print("\n" + "="*50)
        print("VERIFICATION CODE SENT!")
        print("="*50)
        print("Check your phone for the SMS code")
        print("Enter the code when prompted:")
        
        # Get code from user
        code = input("\nEnter verification code: ").strip()
        
        print("Authenticating...")
        await client.sign_in(phone, code)
        
        # Get user info
        me = await client.get_me()
        print(f"\nSUCCESS! Authenticated as: {me.first_name}")
        
        # Generate session string
        session_string = client.session.save()
        
        # Update .env file
        print("Updating .env file with session string...")
        
        # Read current .env
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Update session string line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('TELEGRAM_SESSION_STRING='):
                lines[i] = f'TELEGRAM_SESSION_STRING={session_string}\n'
                updated = True
                break
        
        if not updated:
            lines.append(f'TELEGRAM_SESSION_STRING={session_string}\n')
        
        # Write back
        with open('.env', 'w') as f:
            f.writelines(lines)
        
        # Find target group
        print("\nScanning for target group...")
        target_found = False
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                if 'smrt' in dialog.title.lower() or 'signal' in dialog.title.lower():
                    print(f"Found relevant group: {dialog.title}")
                    if 'smrt signals - crypto channel' in dialog.title.lower():
                        target_found = True
                        print("  >>> TARGET GROUP FOUND!")
        
        await client.disconnect()
        
        print("\n" + "="*50)
        print("TELEGRAM SETUP COMPLETE!")
        print("="*50)
        print(f"Session saved to .env file")
        print(f"Target group found: {target_found}")
        print(f"Ready for signal monitoring!")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(setup_telegram_session())
        if result:
            print("\nNext steps:")
            print("1. Start the Telegram monitoring service")
            print("2. Test signal detection")
            print("3. Monitor dashboard for incoming signals")
        else:
            print("\nSetup failed. Check credentials and try again.")
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")