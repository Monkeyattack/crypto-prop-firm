#!/usr/bin/env python3
"""
Simple setup script for Telegram User Client
Helps you configure and test your Telegram integration
"""

import os
import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_telegram():
    """Interactive setup for Telegram user client"""
    
    print("\n[ROBOT] Telegram User Client Setup")
    print("=" * 50)
    
    # Check if API credentials exist
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    if not api_id or not api_hash:
        print("\n❌ Missing Telegram API credentials!")
        print("   1. Go to https://my.telegram.org/apps")
        print("   2. Create a new application")
        print("   3. Add TELEGRAM_API_ID and TELEGRAM_API_HASH to your .env file")
        print("   4. Run this script again")
        return
    
    if not phone:
        print("\n📱 Phone number not found in .env file")
        phone = input("   Enter your phone number (with country code, e.g., +1234567890): ")
        if not phone:
            print("   ❌ Phone number is required")
            return
    
    print(f"\n🔐 Connecting to Telegram...")
    print(f"   API ID: {api_id}")
    print(f"   Phone: {phone}")
    
    try:
        # Create client
        client = TelegramClient('setup_session', int(api_id), api_hash)
        
        # Connect and authenticate
        await client.start(phone=phone)
        
        # Get user info
        me = await client.get_me()
        print(f"\n✅ Successfully connected!")
        print(f"   Name: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username}")
        print(f"   Phone: {me.phone}")
        
        # Generate session string
        session_string = client.session.save()
        print(f"\n🔑 Session string generated (save this to .env):")
        print(f"   TELEGRAM_SESSION_STRING={session_string}")
        
        # List groups
        print(f"\n📱 Your Telegram groups:")
        print("-" * 50)
        
        groups = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                group_info = {
                    'id': dialog.entity.id,
                    'title': dialog.title,
                    'username': getattr(dialog.entity, 'username', None)
                }
                groups.append(group_info)
                
                print(f"📱 {group_info['title']}")
                print(f"   ID: {group_info['id']}")
                if group_info['username']:
                    print(f"   Username: @{group_info['username']}")
                print()
        
        # Generate configuration
        print("\n⚙️ Suggested configuration for .env:")
        print("-" * 50)
        print(f"TELEGRAM_API_ID={api_id}")
        print(f"TELEGRAM_API_HASH={api_hash}")
        print(f"TELEGRAM_PHONE_NUMBER={phone}")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        
        if groups:
            # Show first few groups as examples
            example_groups = groups[:3]
            group_names = ','.join([f'"{g["title"]}"' for g in example_groups])
            print(f"TELEGRAM_MONITORED_GROUPS={group_names}")
            
            print(f"\n💡 Tips:")
            print(f"   - Use group names: \"Group Name 1\",\"Group Name 2\"")
            print(f"   - Or use group IDs: {groups[0]['id']},{groups[1]['id'] if len(groups) > 1 else ''}")
            print(f"   - Mix both: \"Group Name\",{groups[0]['id']}")
        
        # Test signal detection
        print(f"\n🧪 Want to test signal detection? (y/n): ", end="")
        try:
            test_choice = input().lower().strip()
            if test_choice == 'y':
                await test_signal_detection()
        except KeyboardInterrupt:
            pass
        
        await client.disconnect()
        
        print(f"\n🎉 Setup complete!")
        print(f"   1. Update your .env file with the configuration above")
        print(f"   2. Run: python telegram_user_client.py")
        print(f"   3. Start paper trading with automatic signal detection!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return

async def test_signal_detection():
    """Test signal detection with sample messages"""
    
    from signal_processor import SignalProcessor
    
    print(f"\n🧪 Testing signal detection...")
    
    processor = SignalProcessor()
    
    test_signals = [
        """
        Buy BTCUSDT
        Entry: 45000
        TP: 47000
        SL: 43000
        """,
        """
        🚀 LONG SIGNAL 🚀
        Pair: ETHUSDT
        Entry: 2600
        Target: 2750
        Stop Loss: 2450
        """,
        """
        BUY $ADA @ 0.45 | TP: 0.50 | SL: 0.40
        """,
        """
        This is not a trading signal, just a regular message.
        """
    ]
    
    for i, signal in enumerate(test_signals, 1):
        print(f"\n📝 Test Signal {i}:")
        print(f"   {signal.strip()}")
        
        # Test if it looks like a signal
        from telegram_user_client import TelegramUserClient
        client = TelegramUserClient()
        looks_like_signal = client._looks_like_signal(signal)
        
        print(f"   Detected as signal: {'✅ Yes' if looks_like_signal else '❌ No'}")
        
        if looks_like_signal:
            # Try to parse it
            parsed = processor.parse_signal(signal)
            if parsed:
                print(f"   Parsed: {parsed}")
            else:
                print(f"   ⚠️ Could not parse signal format")

def main():
    """Main function"""
    try:
        asyncio.run(setup_telegram())
    except KeyboardInterrupt:
        print(f"\n\n👋 Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")

if __name__ == "__main__":
    main()