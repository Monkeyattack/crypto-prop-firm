#!/usr/bin/env python3
"""
Telegram login with pause for code input
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

# Global variables to store session info
client_session = None
sent_code_info = None

async def step1_request_code():
    """Step 1: Connect and request verification code"""
    global client_session, sent_code_info
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Telegram Login - Step 1 ===")
    print(f"Phone: {phone}")
    
    try:
        # Create client with string session
        client_session = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\n[CONNECTING] Connecting to Telegram...")
        await client_session.connect()
        
        print("[REQUESTING] Sending verification code...")
        sent_code_info = await client_session.send_code_request(phone)
        
        print(f"\n" + "="*60)
        print("VERIFICATION CODE SENT TO YOUR PHONE!")
        print("="*60)
        print(f"Phone: {phone}")
        print(f"Code Hash: {sent_code_info.phone_code_hash}")
        print("="*60)
        print("\nWAITING FOR YOUR CODE...")
        print("When you receive the SMS, tell me:")
        print("'The code is: XXXXX'")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to request code: {e}")
        return False

async def step2_complete_auth(verification_code):
    """Step 2: Complete authentication with user's code"""
    global client_session, sent_code_info
    
    if not client_session or not sent_code_info:
        print("[ERROR] No active session. Run step 1 first.")
        return False
    
    print(f"\n=== Telegram Login - Step 2 ===")
    print(f"Using code: {verification_code}")
    
    try:
        print("[AUTHENTICATING] Signing in with your code...")
        await client_session.sign_in(
            phone=os.getenv('TELEGRAM_PHONE_NUMBER'),
            code=verification_code,
            phone_code_hash=sent_code_info.phone_code_hash
        )
        
        # Get user info
        me = await client_session.get_me()
        print(f"\n[SUCCESS] Authentication complete!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        
        # Generate session string
        session_string = client_session.session.save()
        print(f"\n[SESSION] Generated session string")
        print(f"Length: {len(session_string)} characters")
        
        # Find groups
        print(f"\n[SCANNING] Looking for your groups...")
        target_group = "SMRT Signals - Crypto Channel"
        groups_found = []
        target_found = False
        
        async for dialog in client_session.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                groups_found.append(dialog.title)
                if any(word in dialog.title.lower() for word in ['smrt', 'signal', 'crypto']):
                    print(f"[FOUND] {dialog.title}")
                    if target_group.lower() in dialog.title.lower():
                        target_found = True
                        print(f"   >>> TARGET GROUP LOCATED! <<<")
        
        print(f"\n[SUMMARY]")
        print(f"Total groups: {len(groups_found)}")
        print(f"Target group found: {'YES' if target_found else 'Similar groups found'}")
        
        # Close connection
        await client_session.disconnect()
        
        # Update .env file
        print(f"\n[UPDATING] Saving session to .env file...")
        try:
            with open('.env', 'r') as f:
                content = f.read()
            
            # Replace session string line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    lines[i] = f'TELEGRAM_SESSION_STRING={session_string}'
                    break
            
            with open('.env', 'w') as f:
                f.write('\n'.join(lines))
            
            print("[SUCCESS] Session saved to .env file!")
            
        except Exception as e:
            print(f"[WARNING] Could not update .env automatically: {e}")
            print(f"\nPlease add this line to your .env file:")
            print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        print(f"\n" + "="*60)
        print("🎉 TELEGRAM INTEGRATION COMPLETE! 🎉")
        print("="*60)
        print("Your crypto paper trading system is now FULLY OPERATIONAL!")
        print("\nTo start monitoring signals:")
        print("  python telegram_user_client.py")
        print("\nDashboard:")
        print("  http://localhost:8501")
        print("\nTarget group:")
        print(f"  {target_group}")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        
        if "PHONE_CODE_INVALID" in str(e):
            print("The verification code was invalid or expired.")
            print("We'll need to start over with a fresh code.")
        elif "PHONE_CODE_EXPIRED" in str(e):
            print("The verification code expired.")
            print("We'll need to request a new one.")
        
        return False

# Main execution
async def main():
    """Main execution flow"""
    print("Starting Telegram authentication process...")
    
    # Step 1: Request code
    success = await step1_request_code()
    
    if success:
        print("\n[WAITING] Please check your phone and provide the verification code...")
    else:
        print("[FAILED] Could not request verification code")

if __name__ == "__main__":
    asyncio.run(main())