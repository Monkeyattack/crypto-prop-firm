#!/usr/bin/env python3
"""
Fix message tracking to prevent reprocessing old signals
Set tracking to current latest message ID in the channel
"""

import asyncio
import os
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_message_tracking():
    """Fix message tracking to prevent reprocessing old signals"""
    load_dotenv()
    
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    session_string = os.getenv('TELEGRAM_SESSION_STRING')
    monitored_groups = ['SMRT Signals - Crypto Channel']
    
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("Telegram session not authorized")
            return
        
        logger.info("Connected to Telegram successfully")
        
        # Find the monitored channel and get the latest message ID
        async for dialog in client.iter_dialogs():
            if not (dialog.is_group or dialog.is_channel):
                continue
            
            group_name = dialog.title
            if 'SMRT Signals' not in group_name:
                continue
            
            logger.info(f"Found channel: {group_name}")
            
            # Get the latest message ID from the channel
            latest_message = None
            async for message in client.iter_messages(dialog, limit=1):
                latest_message = message
                break
            
            if latest_message:
                latest_id = latest_message.id
                logger.info(f"Latest message ID in {group_name}: {latest_id}")
                
                # Update the database to track from this point forward
                conn = sqlite3.connect('trade_log.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_messages 
                    (channel_name, last_message_id, last_check_time)
                    VALUES (?, ?, datetime('now'))
                ''', (group_name, latest_id))
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Updated message tracking for {group_name} to message ID {latest_id}")
                logger.info("🔒 System will now only process NEW signals going forward")
            else:
                logger.warning(f"No messages found in {group_name}")
        
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Error fixing message tracking: {e}")

def main():
    """Run the message tracking fix"""
    print("🔧 Fixing message tracking to prevent reprocessing old signals...")
    asyncio.run(fix_message_tracking())

if __name__ == "__main__":
    main()