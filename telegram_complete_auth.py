"""
Complete Telegram authentication with the code you received
Run this AFTER you get the code
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

async def complete_auth():
    """Complete authentication with received code"""
    
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    phone = '+14692238202'
    
    print("=" * 60)
    print("COMPLETE TELEGRAM AUTHENTICATION")
    print("=" * 60)
    
    # Get the code from user
    code = input("Enter the code from Telegram: ").strip()
    
    if not code:
        print("No code entered")
        return False
    
    try:
        # Start fresh session
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        print("\nConnecting...")
        await client.connect()
        
        # Try to sign in with just phone and code
        print(f"Signing in with code: {code}")
        
        try:
            # First try - might need to send code again
            await client.sign_in(phone, code)
            
        except Exception as e:
            if "phone_code_hash" in str(e) or "PHONE_CODE_INVALID" in str(e):
                print("Need to request code again...")
                
                # Request new code
                sent = await client.send_code_request(phone)
                
                # Wait for new code
                new_code = input("Enter the NEW code: ").strip()
                
                # Try with new code
                await client.sign_in(phone, new_code)
        
        # If we get here, we're logged in
        session_string = client.session.save()
        
        print("\n" + "=" * 60)
        print("SUCCESS! Logged in to Telegram")
        print("=" * 60)
        
        # Save session to .env
        env_file = '.env'
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update session string
            found = False
            for i, line in enumerate(lines):
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    lines[i] = f'TELEGRAM_SESSION_STRING={session_string}\n'
                    found = True
                    break
            
            if not found:
                lines.append(f'\nTELEGRAM_SESSION_STRING={session_string}\n')
            
            with open(env_file, 'w') as f:
                f.writelines(lines)
        else:
            # Create .env
            with open(env_file, 'w') as f:
                f.write(f'TELEGRAM_SESSION_STRING={session_string}\n')
        
        print(f"Session saved to {env_file}")
        
        # Test access
        me = await client.get_me()
        print(f"\nLogged in as: {me.first_name}")
        
        # Check groups
        print("\nChecking for signal groups...")
        dialogs = await client.get_dialogs()
        
        target_groups = ['SMRT Signals - Crypto Channel', 'SMRT Signals - Gold/FX Channel']
        found = []
        
        for dialog in dialogs:
            if dialog.name in target_groups:
                found.append(dialog.name)
                print(f"  ✓ Found: {dialog.name}")
        
        if len(found) < len(target_groups):
            print("\nMissing groups:")
            for g in target_groups:
                if g not in found:
                    print(f"  ✗ {g}")
        
        await client.disconnect()
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("You can now run the signal collector")
        print("It will collect signals from Telegram groups")
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        
        if "PHONE_CODE_INVALID" in str(e):
            print("\nThe code was invalid or expired")
            print("Run telegram_auth_with_delay.py to request a new code")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(complete_auth())
    
    if not success:
        print("\nAuthentication failed")
        print("You may need to request a new code")