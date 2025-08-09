"""
Request a new Telegram verification code
"""

import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

async def request_code():
    """Request a new verification code from Telegram"""
    
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    phone = '+14692238202'
    
    print("=" * 60)
    print("REQUESTING NEW TELEGRAM VERIFICATION CODE")
    print("=" * 60)
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    print()
    
    try:
        # Create new client with empty session
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        print("Connecting to Telegram...")
        await client.connect()
        
        print(f"Requesting verification code for {phone}...")
        sent_code = await client.send_code_request(phone)
        
        print("\n" + "=" * 60)
        print("CODE SENT!")
        print("=" * 60)
        print("Check your Telegram app for the verification code")
        print("It should arrive within a few seconds")
        print()
        
        # Now get the code from user
        code = input("Enter the verification code: ").strip()
        
        if not code:
            print("No code entered. Exiting.")
            await client.disconnect()
            return
        
        print(f"\nAuthenticating with code: {code}")
        
        try:
            # Try to sign in
            await client.sign_in(phone, code)
            
            # If successful, save session
            session_string = client.session.save()
            
            print("\n" + "=" * 60)
            print("SUCCESS! Authentication complete!")
            print("=" * 60)
            
            # Save session string to .env files
            env_files = [
                '.env',  # Current directory
                'C:/Users/cmeredith/source/repos/crypto-paper-trading/.env'
            ]
            
            for env_file in env_files:
                if os.path.exists(env_file):
                    # Read existing .env
                    with open(env_file, 'r') as f:
                        content = f.read()
                    
                    # Update or add session string
                    if 'TELEGRAM_SESSION_STRING=' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.startswith('TELEGRAM_SESSION_STRING='):
                                lines[i] = f'TELEGRAM_SESSION_STRING={session_string}'
                                break
                        content = '\n'.join(lines)
                    else:
                        content += f'\nTELEGRAM_SESSION_STRING={session_string}\n'
                    
                    # Write back
                    with open(env_file, 'w') as f:
                        f.write(content)
                    
                    print(f"Updated: {env_file}")
            
            # Test connection
            print("\nTesting connection...")
            me = await client.get_me()
            print(f"Logged in as: {me.first_name} {me.last_name if me.last_name else ''}")
            print(f"Username: @{me.username if me.username else 'No username'}")
            
            # List groups
            print("\nYour groups:")
            dialogs = await client.get_dialogs()
            count = 0
            for dialog in dialogs:
                if dialog.is_group or dialog.is_channel:
                    print(f"  - {dialog.name}")
                    count += 1
                    if count >= 10:
                        print("  ... and more")
                        break
            
            # Check for target groups
            target_groups = ['SMRT Signals - Crypto Channel', 'SMRT Signals - Gold/FX Channel']
            found = []
            for dialog in dialogs:
                if dialog.name in target_groups:
                    found.append(dialog.name)
            
            print(f"\nSignal groups found: {len(found)}/{len(target_groups)}")
            for group in found:
                print(f"  ✓ {group}")
            
            if len(found) < len(target_groups):
                missing = [g for g in target_groups if g not in found]
                print("\nMissing groups:")
                for group in missing:
                    print(f"  ✗ {group}")
                print("\nYou may need to join these groups first.")
            
            print("\n" + "=" * 60)
            print("SETUP COMPLETE!")
            print("You can now run the signal collector.")
            print("=" * 60)
            
        except Exception as e:
            print(f"\nAuthentication failed: {e}")
            if "The phone code you provided has expired" in str(e):
                print("\nThe code expired. Please run this script again for a new code.")
            
        await client.disconnect()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have Telegram app installed")
        print("2. Verify the phone number is correct")
        print("3. Check your internet connection")

if __name__ == "__main__":
    asyncio.run(request_code())