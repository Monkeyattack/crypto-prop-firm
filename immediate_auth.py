#!/usr/bin/env python3
"""
Immediate authentication - request code and wait for immediate input
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def immediate_auth():
    """Request code and authenticate immediately"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print("=== Immediate Telegram Authentication ===")
    print("This will request a fresh code and wait for immediate input")
    print(f"Phone: {phone}")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        
        print("\nStep 1: Connecting...")
        await client.connect()
        
        print("Step 2: Requesting fresh verification code...")
        sent_code = await client.send_code_request(phone)
        
        print(f"\n" + "="*50)
        print("FRESH CODE SENT TO YOUR PHONE!")
        print(f"Phone: {phone}")
        print("="*50)
        print("Waiting for code input...")
        
        # Wait a moment for the SMS to arrive
        print("Waiting 5 seconds for SMS delivery...")
        await asyncio.sleep(5)
        
        print(f"\n" + "="*50)
        print("READY FOR VERIFICATION CODE")
        print("="*50)
        print("Please provide the verification code NOW:")
        print("Reply with: 'CODE: XXXXX'")
        print("(I'll check for your response shortly)")
        print("="*50)
        
        # Store session info for the next script
        session_info = {
            'phone_code_hash': sent_code.phone_code_hash,
            'timestamp': str(asyncio.get_event_loop().time())
        }
        
        # Save session info to file for next step
        with open('temp_session_info.txt', 'w') as f:
            f.write(f"phone_code_hash:{sent_code.phone_code_hash}\n")
            f.write(f"timestamp:{session_info['timestamp']}\n")
        
        await client.disconnect()
        
        print(f"\nSession prepared and waiting...")
        print(f"Code hash: {sent_code.phone_code_hash[:20]}...")
        print(f"\nWhen you provide the code, I'll authenticate immediately!")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: Failed to request code: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(immediate_auth())