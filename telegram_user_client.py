"""
Telegram User Client for Reading Trading Signals
Uses your personal Telegram account to monitor groups you're already a member of
"""

import os
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from signal_processor import SignalProcessor
from live_trading import LiveTradingManager, LiveTradeConfig, TradingMode
from config import Config

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramUserClient:
    """Client using your personal Telegram account to monitor groups"""
    
    def __init__(self):
        # Telegram API credentials (you'll need to get these)
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '0'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', '')
        self.phone_number = os.getenv('TELEGRAM_PHONE_NUMBER', '')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING', '')
        
        # Groups to monitor (names or IDs)
        self.monitored_groups = self._parse_monitored_groups()
        self.admin_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
        # Initialize signal processor and trading manager
        self.signal_processor = SignalProcessor()
        
        # Setup live trading manager
        trading_mode = os.getenv('TRADING_MODE', 'paper')
        live_config = LiveTradeConfig(
            mode=TradingMode(trading_mode),
            exchange=os.getenv('EXCHANGE', 'binance'),
            api_key=os.getenv('API_KEY'),
            api_secret=os.getenv('API_SECRET'),
            testnet=os.getenv('TESTNET', 'true').lower() == 'true',
            max_position_size_usd=float(os.getenv('MAX_POSITION_SIZE_USD', '25.0')),
            daily_loss_limit_usd=float(os.getenv('DAILY_LOSS_LIMIT_USD', '10.0')),
            max_daily_trades=int(os.getenv('MAX_DAILY_TRADES', '5')),
            min_account_balance=float(os.getenv('MIN_ACCOUNT_BALANCE', '500.0'))
        )
        self.live_trader = LiveTradingManager(live_config)
        
        # Statistics
        self.signals_processed = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # Create client
        if self.session_string:
            self.client = TelegramClient(StringSession(self.session_string), self.api_id, self.api_hash)
        else:
            self.client = TelegramClient('trading_session', self.api_id, self.api_hash)
        
        logger.info(f"TelegramUserClient initialized in {trading_mode} mode")
    
    def _parse_monitored_groups(self) -> list:
        """Parse groups to monitor from environment variable"""
        groups_str = os.getenv('TELEGRAM_MONITORED_GROUPS', '')
        if not groups_str:
            logger.warning("No TELEGRAM_MONITORED_GROUPS configured - will monitor all groups")
            return []
        
        # Parse comma-separated list of group names/IDs
        groups = [group.strip() for group in groups_str.split(',') if group.strip()]
        logger.info(f"Monitoring {len(groups)} Telegram groups: {groups}")
        return groups
    
    async def start(self):
        """Start the client and connect"""
        await self.client.start(phone=self.phone_number)
        
        # Save session string for future use (so you don't need to login again)
        if not self.session_string:
            session_string = self.client.session.save()
            logger.info(f"Session string (save this to TELEGRAM_SESSION_STRING in .env):")
            logger.info(f"{session_string}")
        
        logger.info("Successfully connected to Telegram")
        
        # Get user info
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        
        # List all dialogs (chats/groups you're in)
        await self.list_groups()
        
        # Setup message handler
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            await self.handle_message(event)
        
        logger.info("Started monitoring for trading signals...")
        
        # Send startup notification
        await self.notify_admin(
            f"🤖 Trading Signal Monitor Started\n"
            f"Mode: {self.live_trader.config.mode.value.upper()}\n"
            f"Monitoring: {len(self.monitored_groups)} groups\n"
            f"User: {me.first_name} (@{me.username})"
        )
    
    async def list_groups(self):
        """List all groups you're a member of"""
        logger.info("Your Telegram groups:")
        logger.info("-" * 50)
        
        async for dialog in self.client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                group_id = dialog.entity.id
                group_title = dialog.title
                group_username = getattr(dialog.entity, 'username', None)
                
                logger.info(f"📱 {group_title}")
                logger.info(f"   ID: {group_id}")
                if group_username:
                    logger.info(f"   Username: @{group_username}")
                logger.info("")
    
    async def handle_message(self, event):
        """Handle new messages from groups"""
        
        # Get chat info
        chat = await event.get_chat()
        sender = await event.get_sender()
        
        # Skip if not from a group/channel
        if not (hasattr(chat, 'title')):
            return
        
        chat_title = chat.title
        chat_id = chat.id
        message_text = event.message.message
        
        # Skip if no text
        if not message_text:
            return
        
        # Check if we should monitor this group
        if self.monitored_groups:
            should_monitor = False
            for monitored in self.monitored_groups:
                # Check by title
                if monitored.lower() in chat_title.lower():
                    should_monitor = True
                    break
                # Check by ID
                if str(chat_id) == str(monitored):
                    should_monitor = True
                    break
                # Check by username
                if hasattr(chat, 'username') and chat.username:
                    if monitored.replace('@', '') == chat.username:
                        should_monitor = True
                        break
            
            if not should_monitor:
                return
        
        # Log the message
        sender_name = getattr(sender, 'first_name', 'Unknown') if sender else 'Unknown'
        logger.debug(f"Message from {chat_title} by {sender_name}: {message_text[:100]}...")
        
        # Process potential signal
        await self.process_potential_signal(message_text, chat_title, sender_name)
    
    async def process_potential_signal(self, text: str, chat_title: str, sender_name: str):
        """Process a potential trading signal"""
        
        try:
            # Check if this looks like a trading signal
            if not self._looks_like_signal(text):
                return
            
            logger.info(f"🎯 Potential signal detected from {chat_title}")
            
            # Process the signal
            result = self.signal_processor.process_signal(text)
            self.signals_processed += 1
            
            if result["success"]:
                # Parse the signal to get trade data
                parsed_signal = self.signal_processor.parse_signal(text)
                
                if parsed_signal:
                    # Execute trade through live trading manager
                    trade_result = self.live_trader.execute_trade(parsed_signal)
                    
                    if trade_result["success"]:
                        self.successful_trades += 1
                        await self.notify_admin(
                            f"✅ TRADE EXECUTED\n"
                            f"Source: {chat_title}\n"
                            f"Signal: {result['message']}\n"
                            f"Mode: {self.live_trader.config.mode.value.upper()}\n"
                            f"Stats: {self.successful_trades}✅ / {self.failed_trades}❌"
                        )
                    else:
                        self.failed_trades += 1
                        await self.notify_admin(
                            f"❌ TRADE FAILED\n"
                            f"Source: {chat_title}\n"
                            f"Reason: {trade_result.get('reason', 'Unknown')}\n"
                            f"Stats: {self.successful_trades}✅ / {self.failed_trades}❌"
                        )
            else:
                self.failed_trades += 1
                logger.warning(f"Signal rejected: {result['message']}")
                await self.notify_admin(
                    f"⚠️ SIGNAL REJECTED\n"
                    f"Source: {chat_title}\n"
                    f"Reason: {result['message']}\n"
                    f"Errors: {', '.join(result.get('errors', []))}"
                )
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            await self.notify_admin(f"🚨 ERROR processing signal from {chat_title}: {e}")
    
    def _looks_like_signal(self, text: str) -> bool:
        """Quick check if message looks like a trading signal"""
        
        # Convert to lowercase for checking
        text_lower = text.lower()
        
        # Check for common signal patterns
        signal_keywords = [
            'buy', 'sell', 'long', 'short',
            'entry', 'tp', 'sl', 'take profit', 'stop loss',
            'target', 'usdt', 'btc', 'eth'
        ]
        
        # Must contain at least 2 keywords and some numbers
        keyword_count = sum(1 for keyword in signal_keywords if keyword in text_lower)
        has_numbers = bool(re.search(r'\d+\.?\d*', text))
        
        # Check for crypto pairs
        has_crypto_symbol = bool(re.search(r'[A-Z]{2,}USDT|[A-Z]{2,}BTC|[A-Z]{2,}/USDT', text))
        
        return keyword_count >= 2 and has_numbers and (has_crypto_symbol or 'usdt' in text_lower)
    
    async def notify_admin(self, message: str):
        """Send notification to admin (yourself)"""
        
        try:
            if self.admin_chat_id:
                # Send to saved messages or specific chat
                await self.client.send_message(int(self.admin_chat_id), message)
            else:
                # Send to saved messages (your personal chat)
                await self.client.send_message('me', message)
            
            logger.info(f"Admin notification sent: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
    
    async def run(self):
        """Run the client"""
        await self.start()
        
        # Keep the client running
        await self.client.run_until_disconnected()

async def main():
    """Main function"""
    
    try:
        # Setup configuration
        Config.setup_logging()
        Config.validate_config()
        
        # Check if API credentials are configured
        if not os.getenv('TELEGRAM_API_ID') or not os.getenv('TELEGRAM_API_HASH'):
            logger.error("❌ TELEGRAM_API_ID and TELEGRAM_API_HASH must be set!")
            logger.error("   Get them from https://my.telegram.org/apps")
            return
        
        # Create and run client
        client = TelegramUserClient()
        await client.run()
        
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())