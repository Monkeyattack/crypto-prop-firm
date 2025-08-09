"""
Complete Telegram Login with Your Code
Run this and enter the code Telegram sent you
"""

import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Add parent directory to path to import from crypto-paper-trading
sys.path.append('C:/Users/cmeredith/source/repos/crypto-paper-trading')

async def complete_login():
    """Complete Telegram login with the code you received"""
    
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    phone = '+14692238202'
    
    print("=" * 60)
    print("TELEGRAM LOGIN COMPLETION")
    print("=" * 60)
    print(f"Phone: {phone}")
    print()
    
    # Get the code from user
    code = input("Enter the verification code Telegram sent you: ").strip()
    
    if not code:
        print("No code entered. Exiting.")
        return
    
    try:
        # Create client
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        print("\nConnecting to Telegram...")
        await client.connect()
        
        # Try to sign in with the code
        print(f"Authenticating with code: {code}")
        await client.sign_in(phone, code)
        
        # Get session string
        session_string = client.session.save()
        
        print("\n" + "=" * 60)
        print("SUCCESS! Authentication complete!")
        print("=" * 60)
        
        # Save to .env file in BOTH directories
        env_files = [
            'C:/Users/cmeredith/source/repos/crypto-prop-firm/.env',
            'C:/Users/cmeredith/source/repos/crypto-paper-trading/.env'
        ]
        
        for env_file in env_files:
            if os.path.exists(env_file):
                # Read existing .env
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                # Update or add session string
                found = False
                for i, line in enumerate(lines):
                    if line.startswith('TELEGRAM_SESSION_STRING='):
                        lines[i] = f'TELEGRAM_SESSION_STRING={session_string}\n'
                        found = True
                        break
                
                if not found:
                    # Add it if not found
                    for i, line in enumerate(lines):
                        if 'TELEGRAM_SESSION_STRING' in line:
                            lines[i] = f'TELEGRAM_SESSION_STRING={session_string}  # Generated session\n'
                            found = True
                            break
                
                # Write back
                with open(env_file, 'w') as f:
                    f.writelines(lines)
                
                print(f"Updated: {env_file}")
        
        # Test that we can access groups
        print("\nTesting access to groups...")
        dialogs = await client.get_dialogs()
        
        print("\nYour Telegram groups:")
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                print(f"  - {dialog.name}")
        
        # Look for our target groups
        target_groups = ['SMRT Signals - Crypto Channel', 'SMRT Signals - Gold/FX Channel']
        found_groups = []
        
        for dialog in dialogs:
            if dialog.name in target_groups:
                found_groups.append(dialog.name)
        
        print(f"\nTarget groups found: {len(found_groups)}/{len(target_groups)}")
        for group in found_groups:
            print(f"  ✓ {group}")
        
        await client.disconnect()
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("1. Run the signal collector: python telegram_signal_collector.py")
        print("2. It will now collect signals from both Crypto and Gold/FX channels")
        print("3. The paper trader will process them automatically")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nIf the code expired, run this script again to get a new one.")
        return

if __name__ == "__main__":
    asyncio.run(complete_login())