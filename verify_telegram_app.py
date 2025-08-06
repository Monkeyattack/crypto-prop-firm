#!/usr/bin/env python3
"""
Verify Telegram App credentials and troubleshoot issues
"""

import os
import asyncio
import requests
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

def verify_app_online():
    """Check if we can reach Telegram API"""
    print("=== Verifying Telegram API Access ===")
    
    try:
        # Test basic connectivity to Telegram
        response = requests.get("https://api.telegram.org/", timeout=10)
        print(f"[SUCCESS] Can reach Telegram API (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[ERROR] Cannot reach Telegram API: {e}")
        return False

async def test_different_approach():
    """Try different authentication approach"""
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    print(f"\n=== Testing Telegram App Credentials ===")
    print(f"API ID: {api_id}")
    print(f"API Hash: {api_hash}")
    
    # Test 1: Basic connection without authentication
    try:
        print(f"\n[TEST 1] Testing basic connection...")
        client = TelegramClient('verify_session', int(api_id), api_hash)
        await client.connect()
        print(f"[SUCCESS] Basic connection works")
        await client.disconnect()
    except Exception as e:
        print(f"[ERROR] Basic connection failed: {e}")
        return False
    
    # Test 2: Try to send code request
    try:
        print(f"\n[TEST 2] Testing code request...")
        client = TelegramClient('verify_session2', int(api_id), api_hash)
        await client.connect()
        
        phone = os.getenv('TELEGRAM_PHONE_NUMBER')
        print(f"Sending code to: {phone}")
        
        # This should trigger the SMS/call
        sent_code = await client.send_code_request(phone)
        print(f"[SUCCESS] Code sent! Check your phone for SMS/call")
        print(f"Code hash: {sent_code.phone_code_hash[:10]}...")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"[ERROR] Code request failed: {e}")
        
        if "PHONE_NUMBER_INVALID" in str(e):
            print("   - Phone number format might be wrong")
            print("   - Try: +1XXXXXXXXXX (no spaces or dashes)")
        elif "api_id/api_hash combination is invalid" in str(e):
            print("   - API credentials are invalid")
            print("   - Double-check your Telegram app at https://my.telegram.org/apps")
            print("   - Make sure the app is 'Active'")
        elif "FLOOD_WAIT" in str(e):
            print("   - Too many requests, wait a few minutes")
        
        await client.disconnect()
        return False

def main():
    """Main verification"""
    print("🔍 Telegram App Verification Tool")
    print("=" * 50)
    
    # Check .env file
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    if not all([api_id, api_hash, phone]):
        print("[ERROR] Missing credentials in .env file")
        print("Required:")
        print(f"  TELEGRAM_API_ID={api_id or 'MISSING'}")
        print(f"  TELEGRAM_API_HASH={'SET' if api_hash else 'MISSING'}")
        print(f"  TELEGRAM_PHONE_NUMBER={phone or 'MISSING'}")
        return
    
    # Test internet connectivity
    if not verify_app_online():
        print("\n[SOLUTION] Check your internet connection")
        return
    
    # Test Telegram app
    try:
        if asyncio.run(test_different_approach()):
            print(f"\n✅ [SUCCESS] Your Telegram app credentials work!")
            print(f"Next steps:")
            print(f"1. Check your phone for verification code")
            print(f"2. Use the authentication script with the code")
        else:
            print(f"\n❌ [FAILED] Telegram app verification failed")
            print(f"\nTroubleshooting:")
            print(f"1. Go to https://my.telegram.org/apps")
            print(f"2. Make sure your app 'MonkeyAttack Signal Trader' exists")
            print(f"3. Verify the API ID and Hash are correct")
            print(f"4. Try creating a new app if needed")
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")

if __name__ == "__main__":
    main()