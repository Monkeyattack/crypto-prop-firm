#!/usr/bin/env python3
"""
Simple script to get Telegram group IDs
Run this script and then send a message in your group mentioning the bot
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GroupIDBot:
    """Simple bot to discover group IDs"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.discovered_groups = set()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any message and log group information"""
        
        if not update.message:
            return
        
        message = update.message
        chat = message.chat
        user = message.from_user
        
        # Log detailed information about the chat
        chat_info = {
            'chat_id': chat.id,
            'chat_type': chat.type,
            'chat_title': chat.title,
            'chat_username': chat.username,
            'user_name': user.first_name if user else 'Unknown',
            'message_text': message.text[:50] + '...' if len(message.text) > 50 else message.text
        }
        
        print(f"\n📱 MESSAGE RECEIVED:")
        print(f"   Chat ID: {chat_info['chat_id']}")
        print(f"   Chat Type: {chat_info['chat_type']}")
        print(f"   Chat Title: {chat_info['chat_title']}")
        print(f"   Chat Username: @{chat_info['chat_username']}" if chat_info['chat_username'] else "   Chat Username: None")
        print(f"   From User: {chat_info['user_name']}")
        print(f"   Message: {chat_info['message_text']}")
        
        # If it's a group or supergroup, save the ID
        if chat.type in ['group', 'supergroup']:
            if chat.id not in self.discovered_groups:
                self.discovered_groups.add(chat.id)
                print(f"\n✅ NEW GROUP DISCOVERED!")
                print(f"   Add this to your .env file:")
                print(f"   TELEGRAM_ALLOWED_GROUPS={chat.id}")
                
                if len(self.discovered_groups) > 1:
                    all_groups = ','.join(map(str, self.discovered_groups))
                    print(f"\n📋 ALL DISCOVERED GROUPS:")
                    print(f"   TELEGRAM_ALLOWED_GROUPS={all_groups}")
        
        # Send a confirmation reply if it's a private message
        if chat.type == 'private':
            await update.message.reply_text(
                f"👋 Hello! I can help you find group IDs.\n\n"
                f"To get a group ID:\n"
                f"1. Add me to your private group\n"
                f"2. Make me an admin (required to read messages)\n"
                f"3. Send any message in the group\n"
                f"4. I'll show you the group ID\n\n"
                f"Your chat ID: {chat.id}"
            )

def main():
    """Main function"""
    
    # Get bot token from environment or use your Crypto Trading Bot
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0')
    
    if not bot_token:
        print("❌ No TELEGRAM_BOT_TOKEN found!")
        print("   Set it in your .env file or as an environment variable")
        return
    
    print(f"🤖 Starting Group ID Discovery Bot...")
    print(f"   Bot Token: {bot_token[:10]}...")
    print(f"\n📋 INSTRUCTIONS:")
    print(f"   1. Add your bot to the private groups you want to monitor")
    print(f"   2. Make the bot an admin in each group")
    print(f"   3. Send a message in each group (mention the bot: @your_bot_name)")
    print(f"   4. The group ID will be displayed here")
    print(f"   5. Press Ctrl+C to stop when done")
    print(f"\n🔍 Listening for messages...")
    
    try:
        # Create bot
        bot = GroupIDBot(bot_token)
        
        # Create application
        app = Application.builder().token(bot_token).build()
        
        # Add message handler
        app.add_handler(MessageHandler(filters.ALL, bot.handle_message))
        
        # Start the bot
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        print(f"\n👋 Bot stopped by user")
        if bot.discovered_groups:
            print(f"\n📋 SUMMARY - Discovered Groups:")
            for group_id in bot.discovered_groups:
                print(f"   {group_id}")
            all_groups = ','.join(map(str, bot.discovered_groups))
            print(f"\n📝 Copy this to your .env file:")
            print(f"   TELEGRAM_ALLOWED_GROUPS={all_groups}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()