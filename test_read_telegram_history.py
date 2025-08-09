"""
Test reading historical messages from Telegram channels
This will help verify we can parse real signals
"""

import asyncio
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

async def read_channel_history():
    """Read recent messages from Gold/FX channel"""
    
    # Load credentials
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    
    # Load session from .env
    session_string = None
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    session_string = line.split('=', 1)[1].strip()
                    break
    
    if not session_string:
        print("No session string found in .env")
        return
    
    print("Connecting to Telegram...")
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("Not authorized!")
            return
        
        print("Connected! Looking for channels...")
        
        # Get dialogs
        dialogs = await client.get_dialogs()
        
        # Find Gold/FX channel
        gold_channel = None
        crypto_channel = None
        
        for dialog in dialogs:
            if "Gold" in dialog.name and "FX" in dialog.name:
                gold_channel = dialog
                print(f"Found Gold/FX channel: {dialog.name}")
            elif "Crypto" in dialog.name and "SMRT" in dialog.name:
                crypto_channel = dialog
                print(f"Found Crypto channel: {dialog.name}")
        
        print("\n" + "="*70)
        
        # Read recent messages from Gold/FX channel
        if gold_channel:
            print(f"RECENT MESSAGES FROM: {gold_channel.name}")
            print("="*70)
            
            # Get last 20 messages
            messages = await client.get_messages(gold_channel, limit=20)
            
            signal_count = 0
            for msg in messages:
                if msg.text:
                    # Look for trading signals (common patterns)
                    text = msg.text.upper()
                    
                    # Check if it might be a signal
                    is_signal = False
                    
                    # Common signal patterns
                    signal_keywords = ['XAUUSD', 'GOLD', 'BUY', 'SELL', 'TP', 'SL', 
                                      'ENTRY', 'TARGET', 'STOP', 'PROFIT']
                    
                    matching_keywords = [kw for kw in signal_keywords if kw in text]
                    
                    if len(matching_keywords) >= 2:  # At least 2 keywords
                        is_signal = True
                    
                    if is_signal:
                        signal_count += 1
                        print(f"\n[POTENTIAL SIGNAL #{signal_count}]")
                        print(f"Time: {msg.date}")
                        print(f"Message ID: {msg.id}")
                        print(f"Text: {msg.text[:500]}")  # First 500 chars
                        print("-" * 50)
            
            if signal_count == 0:
                print("No trading signals found in recent messages")
                print("\nShowing last 5 messages for context:")
                for i, msg in enumerate(messages[:5], 1):
                    if msg.text:
                        print(f"\n[Message {i}]")
                        print(f"Time: {msg.date}")
                        print(f"Text: {msg.text[:200]}...")
        
        else:
            print("Gold/FX channel not found!")
            
        print("\n" + "="*70)
        
        # Also check crypto channel
        if crypto_channel:
            print(f"\nRECENT MESSAGES FROM: {crypto_channel.name}")
            print("="*70)
            
            messages = await client.get_messages(crypto_channel, limit=10)
            
            signal_count = 0
            for msg in messages:
                if msg.text:
                    text = msg.text.upper()
                    
                    # Crypto signal patterns
                    crypto_keywords = ['BTC', 'ETH', 'SOL', 'BUY', 'SELL', 'LONG', 
                                      'SHORT', 'ENTRY', 'TARGET', 'STOP']
                    
                    matching = [kw for kw in crypto_keywords if kw in text]
                    
                    if len(matching) >= 2:
                        signal_count += 1
                        print(f"\n[CRYPTO SIGNAL #{signal_count}]")
                        print(f"Time: {msg.date}")
                        print(f"Text: {msg.text[:300]}")
                        
                        if signal_count >= 3:
                            break
            
            if signal_count == 0:
                print("No crypto signals found in recent messages")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    print("TESTING TELEGRAM CHANNEL HISTORY READING")
    print("="*70)
    asyncio.run(read_channel_history())