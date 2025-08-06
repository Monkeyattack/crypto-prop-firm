#!/usr/bin/env python3
"""
Test Telegram bot functionality
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

class BotTester:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.app = Application.builder().token(bot_token).build()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any message"""
        
        if not update.message:
            return
        
        message = update.message
        chat = message.chat
        user = message.from_user
        
        print(f"\n=== MESSAGE RECEIVED ===")
        print(f"Chat ID: {chat.id}")
        print(f"Chat Type: {chat.type}")
        print(f"Chat Title: {chat.title}")
        print(f"From User: {user.first_name if user else 'Unknown'}")
        print(f"Message: {message.text[:100] if message.text else 'No text'}")
        
        # If it's a private message, respond
        if chat.type == 'private':
            await update.message.reply_text(
                f"Bot is working! Your chat ID: {chat.id}\n"
                f"To use with groups:\n"
                f"1. Add me to your private group 'SMRT Signals - Crypto Channel'\n"
                f"2. Make me an admin\n"
                f"3. Send a message in the group\n"
                f"4. I'll show you the group ID"
            )
    
    async def test_bot(self):
        """Test bot functionality"""
        print("=== Testing Telegram Bot ===")
        print(f"Bot Token: {self.bot_token[:20]}...")
        
        try:
            # Test bot info
            bot = self.app.bot
            bot_info = await bot.get_me()
            print(f"\n[SUCCESS] Bot Info:")
            print(f"Name: {bot_info.first_name}")
            print(f"Username: @{bot_info.username}")
            print(f"ID: {bot_info.id}")
            
            print(f"\n[INFO] Bot is ready to receive messages")
            print(f"[INFO] Send me a private message or add me to your group")
            print(f"[INFO] Press Ctrl+C to stop")
            
            # Add message handler
            self.app.add_handler(MessageHandler(filters.ALL, self.handle_message))
            
            # Start polling
            await self.app.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            print(f"\n[ERROR] Bot test failed: {e}")

def main():
    """Main function"""
    
    # Use the working bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0')
    
    if not bot_token:
        print("[ERROR] No bot token found")
        return
    
    try:
        tester = BotTester(bot_token)
        asyncio.run(tester.test_bot())
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Bot stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    main()