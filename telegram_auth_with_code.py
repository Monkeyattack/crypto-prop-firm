#!/usr/bin/env python3
"""
Complete Telegram authentication with verification code
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def authenticate_with_code():
    """Complete authentication with verification code"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    verification_code = "14289"
    
    print("=== Completing Telegram Authentication ===")
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    print(f"Code: {verification_code}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\n[STEP 1] Connecting...")
        await client.connect()
        
        print(f"[STEP 2] Sending verification code...")
        sent_code = await client.send_code_request(phone)
        
        print(f"[STEP 3] Authenticating with code {verification_code}...")
        await client.sign_in(phone, verification_code, phone_code_hash=sent_code.phone_code_hash)
        
        # Get user info
        me = await client.get_me()
        print(f"\n[SUCCESS] Authentication complete!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        print(f"Phone: {me.phone}")
        
        # Generate session string
        session_string = client.session.save()
        
        print(f"\n" + "="*70)
        print("SESSION STRING GENERATED - ADD TO .env FILE:")
        print("="*70)
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print("="*70)
        
        # Find target group
        print(f"\n[STEP 4] Searching for your groups...")
        target_group = "SMRT Signals - Crypto Channel"
        found_target = False
        all_groups = []
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                group_info = {
                    'title': dialog.title,
                    'id': dialog.entity.id,
                    'username': getattr(dialog.entity, 'username', None)
                }
                all_groups.append(group_info)
                
                print(f"Found: {dialog.title}")
                if target_group.lower() in dialog.title.lower() or "smrt" in dialog.title.lower():
                    print(f"   >>> POTENTIAL TARGET GROUP! <<<")
                    found_target = True
        
        print(f"\n[GROUPS SUMMARY]")
        print(f"Total groups found: {len(all_groups)}")
        
        if found_target:
            print(f"[SUCCESS] Found potential target group!")
        else:
            print(f"[INFO] Target group '{target_group}' not found by exact name")
            print("This might be normal - check the group names above")
        
        await client.disconnect()
        
        # Update .env file automatically
        print(f"\n[STEP 5] Updating .env file...")
        try:
            # Read current .env
            with open('.env', 'r') as f:
                lines = f.readlines()
            
            # Update session string line
            updated_lines = []
            session_updated = False
            
            for line in lines:
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    updated_lines.append(f'TELEGRAM_SESSION_STRING={session_string}\n')
                    session_updated = True
                else:
                    updated_lines.append(line)
            
            # Write back to .env
            with open('.env', 'w') as f:
                f.writelines(updated_lines)
            
            print(f"[SUCCESS] .env file updated automatically!")
            
        except Exception as e:
            print(f"[WARNING] Could not auto-update .env: {e}")
            print("Please add the session string manually")
        
        print(f"\n" + "="*70)
        print("TELEGRAM SETUP COMPLETE!")
        print("="*70)
        print("Next steps:")
        print("1. Session string added to .env file")
        print("2. Run: python telegram_user_client.py")
        print("3. Monitor signals from your Telegram groups")
        print("4. Check dashboard: http://localhost:8501")
        print("\nYour crypto paper trading system is now FULLY OPERATIONAL!")
        
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        
        if "PHONE_CODE_INVALID" in str(e):
            print("The verification code 14289 was incorrect or expired.")
            print("Try running telegram_authenticate_final.py for a new code.")
        elif "PHONE_CODE_EXPIRED" in str(e):
            print("The verification code expired.")
            print("Run telegram_authenticate_final.py to get a new code.")
        else:
            print("Try running telegram_authenticate_final.py to start fresh.")

if __name__ == "__main__":
    asyncio.run(authenticate_with_code())