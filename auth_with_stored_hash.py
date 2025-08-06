#!/usr/bin/env python3
"""
Authenticate using the stored phone code hash
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def auth_with_hash():
    """Authenticate using stored hash and current code"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    verification_code = "20722"
    stored_hash = "b916863bea362be451"  # From the previous request
    
    print("=== Authenticating with Stored Hash ===")
    print(f"Phone: {phone}")
    print(f"Code: {verification_code}")
    print(f"Hash: {stored_hash}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\n[1/3] Connecting...")
        await client.connect()
        
        print("[2/3] Authenticating with stored hash...")
        # Use the stored phone_code_hash directly
        await client.sign_in(phone, verification_code, phone_code_hash=stored_hash)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Authentication complete!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        
        # Generate session string
        session_string = client.session.save()
        
        print(f"\n[3/3] Session generated!")
        print(f"Session length: {len(session_string)} chars")
        
        # Quick group scan
        print(f"\nScanning groups...")
        group_count = 0
        target_found = False
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                group_count += 1
                if "smrt" in dialog.title.lower() or "signal" in dialog.title.lower():
                    print(f"Found relevant group: {dialog.title}")
                    target_found = True
        
        print(f"Total groups: {group_count}")
        print(f"Relevant groups found: {target_found}")
        
        await client.disconnect()
        
        # Update .env
        print(f"\nUpdating .env file...")
        try:
            with open('.env', 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    lines[i] = f'TELEGRAM_SESSION_STRING={session_string}\n'
                    break
            
            with open('.env', 'w') as f:
                f.writelines(lines)
            
            print("[SUCCESS] .env updated with session string!")
            
        except Exception as e:
            print(f"[ERROR] Could not update .env: {e}")
            print(f"Please add manually:")
            print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        print(f"\n" + "="*50)
        print("TELEGRAM AUTHENTICATION COMPLETE!")
        print("="*50)
        print("System Status: FULLY OPERATIONAL")
        print("\nTo start monitoring signals:")
        print("python telegram_user_client.py")
        print("\nDashboard: http://localhost:8501")
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        
        if "PHONE_CODE_INVALID" in str(e):
            print("Code 20722 is invalid or expired.")
            print("I'll request a fresh code for you...")
            
            # Request fresh code automatically
            try:
                fresh_code = await client.send_code_request(phone)
                print(f"New code sent! Hash: {fresh_code.phone_code_hash}")
                print("Please provide the new verification code when you receive it.")
            except Exception as fresh_error:
                print(f"Failed to request fresh code: {fresh_error}")

if __name__ == "__main__":
    asyncio.run(auth_with_hash())