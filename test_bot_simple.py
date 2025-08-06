#!/usr/bin/env python3
"""
Test bot approach for signal monitoring
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.app = Application.builder().token(bot_token).build()
        self.groups_found = {}
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any message and log group information"""
        
        if not update.message:
            return
        
        message = update.message
        chat = message.chat
        user = message.from_user
        
        # Log message details
        print(f"\n=== MESSAGE RECEIVED ===")
        print(f"Chat ID: {chat.id}")
        print(f"Chat Type: {chat.type}")
        print(f"Chat Title: {chat.title or 'N/A'}")
        print(f"From: {user.first_name if user else 'Unknown'}")
        print(f"Message: {message.text[:100] if message.text else 'No text'}...")
        
        # Store group info
        if chat.type in ['group', 'supergroup']:
            if chat.id not in self.groups_found:
                self.groups_found[chat.id] = {
                    'title': chat.title,
                    'type': chat.type,
                    'message_count': 0
                }
            
            self.groups_found[chat.id]['message_count'] += 1
            
            print(f"[GROUP LOGGED] {chat.title}")
            print(f"   ID: {chat.id}")
            print(f"   Messages seen: {self.groups_found[chat.id]['message_count']}")
            
            # Check if this looks like a signal
            if message.text:
                text = message.text.lower()
                signal_keywords = ['buy', 'sell', 'long', 'short', 'entry', 'tp', 'sl']
                if any(keyword in text for keyword in signal_keywords):
                    print(f"   >>> POTENTIAL SIGNAL DETECTED! <<<")
                    print(f"       Content: {message.text[:200]}...")
        
        # Respond to private messages
        if chat.type == 'private':
            await update.message.reply_text(
                f"Bot is working!\n\n"
                f"Your chat ID: {chat.id}\n\n"
                f"Groups found so far: {len(self.groups_found)}\n\n"
                f"To monitor signals:\n"
                f"1. Add me to 'SMRT Signals - Crypto Channel'\n"
                f"2. Make me admin with message reading permission\n"
                f"3. Send a message in the group"
            )
    
    async def start_monitoring(self):
        """Start the bot and monitor for messages"""
        
        print("=== Starting Telegram Bot ===")
        print(f"Bot Token: {self.bot_token[:20]}...")
        
        try:
            # Test bot connection first
            bot = self.app.bot
            bot_info = await bot.get_me()
            
            print(f"\n[SUCCESS] Bot connected!")
            print(f"Name: {bot_info.first_name}")
            print(f"Username: @{bot_info.username}")
            print(f"ID: {bot_info.id}")
            
            print(f"\n[INFO] Bot is ready to receive messages")
            print(f"[INFO] Add the bot to 'SMRT Signals - Crypto Channel' as admin")
            print(f"[INFO] Send a test message in the group")
            print(f"[INFO] Press Ctrl+C to stop and see results")
            
            # Add message handler
            self.app.add_handler(MessageHandler(filters.ALL, self.handle_message))
            
            # Start polling
            await self.app.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except KeyboardInterrupt:
            print(f"\n\n=== BOT STOPPED BY USER ===")
            await self.show_results()
        except Exception as e:
            print(f"\n[ERROR] Bot failed: {e}")
            return False
    
    async def show_results(self):
        """Show discovered groups and results"""
        
        print(f"\n=== RESULTS ===")
        print(f"Groups discovered: {len(self.groups_found)}")
        
        if self.groups_found:
            print(f"\nGroups found:")
            for group_id, info in self.groups_found.items():
                print(f"  - {info['title']}")
                print(f"    ID: {group_id}")
                print(f"    Messages: {info['message_count']}")
                print()
            
            print(f"To use these groups in your .env file:")
            group_ids = ','.join(str(gid) for gid in self.groups_found.keys())
            print(f"TELEGRAM_ALLOWED_GROUPS={group_ids}")
        else:
            print(f"\nNo groups found yet.")
            print(f"Make sure to:")
            print(f"1. Add the bot to your trading groups")
            print(f"2. Make the bot an admin")
            print(f"3. Send messages in the groups")

async def main():
    """Main function"""
    
    # Use your working bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0')
    
    if not bot_token:
        print("[ERROR] No bot token found")
        return
    
    print("=== Telegram Bot Signal Monitor ===")
    print("This will test if the bot approach works for signal monitoring")
    print("\nBot method advantages:")
    print("- No verification codes needed")
    print("- More reliable connection")
    print("- Easier to set up")
    print("\nStarting bot...")
    
    signal_bot = SignalBot(bot_token)
    await signal_bot.start_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot monitoring stopped.")
    except Exception as e:
        print(f"\nError: {e}")