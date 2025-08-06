#!/usr/bin/env python3
"""
VPS Telegram authentication - automated setup
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

async def vps_telegram_auth():
    """Set up Telegram on VPS with your credentials"""
    
    load_dotenv()
    
    api_id = "27540855"
    api_hash = "0ad0e0e612829f4642c373ff0334df1e"
    phone = "+14692238202"
    
    print("=== VPS Telegram Authentication ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\nConnecting to Telegram...")
        await client.connect()
        
        print(f"Sending verification code to {phone}...")
        sent_code = await client.send_code_request(phone)
        
        print("\n" + "="*50)
        print("VERIFICATION CODE SENT!")
        print("="*50)
        print("Check your phone: +14692238202")
        print("Enter the code below:")
        
        # Interactive code input
        code = input("\nEnter verification code: ").strip()
        
        print("Authenticating...")
        await client.sign_in(phone, code)
        
        # Get user info
        me = await client.get_me()
        print(f"\nSUCCESS! Authenticated as: {me.first_name}")
        
        # Generate session string
        session_string = client.session.save()
        
        # Update .env file
        print("Updating .env file...")
        
        # Read current .env
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Update session string
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
        
        # Scan for target group
        print("\nScanning for SMRT Signals - Crypto Channel...")
        target_found = False
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                if 'smrt' in dialog.title.lower() and 'signal' in dialog.title.lower():
                    print(f"FOUND: {dialog.title}")
                    target_found = True
        
        await client.disconnect()
        
        print("\n" + "="*50)
        print("TELEGRAM AUTHENTICATION COMPLETE!")
        print("="*50)
        print(f"Session saved: YES")
        print(f"Target group found: {'YES' if target_found else 'PARTIAL'}")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(vps_telegram_auth())
    if result:
        print("\nREADY FOR SIGNAL MONITORING!")
        print("Run: python telegram_user_client.py")
    else:
        print("\nAuthentication failed.")