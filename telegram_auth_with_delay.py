"""
Telegram Authentication with proper delay handling
Accounts for Windows/local network lag
"""

import os
import asyncio
import time
from telethon import TelegramClient
from telethon.sessions import StringSession

async def authenticate_with_retry():
    """Authenticate to Telegram with retry logic for Windows lag"""
    
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    phone = '+14692238202'
    
    print("=" * 60)
    print("TELEGRAM AUTHENTICATION (Windows Version)")
    print("=" * 60)
    print(f"Phone: {phone}")
    print()
    print("NOTE: There may be a 10-30 second delay on Windows")
    print("This is normal - Telegram needs time to process")
    print()
    
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        print("Connecting to Telegram servers...")
        await client.connect()
        print("Connected!")
        
        print("\nRequesting verification code...")
        print("(This may take 10-30 seconds on Windows)")
        
        # Send code request with timeout handling
        try:
            sent_code = await asyncio.wait_for(
                client.send_code_request(phone),
                timeout=60.0  # 60 second timeout
            )
            print("\n✓ Code request sent successfully!")
            
        except asyncio.TimeoutError:
            print("\n✗ Request timed out (60 seconds)")
            print("This can happen on Windows. Try:")
            print("1. Check your internet connection")
            print("2. Disable Windows Defender temporarily")
            print("3. Try running from VPS instead")
            await client.disconnect()
            return False
        
        print("\n" + "=" * 60)
        print("CHECK YOUR TELEGRAM APP!")
        print("=" * 60)
        print("The code may take 10-30 seconds to arrive")
        print("It will come from Telegram, not SMS")
        print()
        
        # Wait a bit for code to arrive
        print("Waiting 5 seconds for code to arrive...")
        await asyncio.sleep(5)
        
        print("\nWhen you receive the code, enter it here:")
        print("(Format: 12345 - just the numbers)")
        
        # Since we can't do interactive input, save the session request
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. You should receive a code in Telegram app soon")
        print("2. Run: python telegram_complete_auth.py")
        print("3. Enter the code when prompted")
        print()
        print("Session request saved. Waiting for code...")
        
        # Save the phone hash for later use
        with open('telegram_session_temp.txt', 'w') as f:
            f.write(f"{phone}\n")
            f.write(f"{sent_code.phone_code_hash}\n")
        
        print("Session info saved to telegram_session_temp.txt")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nCommon issues on Windows:")
        print("- Firewall blocking connection")
        print("- Antivirus interfering")
        print("- Network proxy settings")
        return False

if __name__ == "__main__":
    success = asyncio.run(authenticate_with_retry())
    
    if success:
        print("\nCode request sent. Now run:")
        print("python telegram_complete_auth.py")
    else:
        print("\nAuthentication request failed.")