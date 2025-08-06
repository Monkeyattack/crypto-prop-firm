"""
Telegram Bot for Reading Trading Signals from Private Groups
This bot monitors specified Telegram groups/channels for trading signals
"""

import os
import logging
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from signal_processor import SignalProcessor
from live_trading import LiveTradingManager, LiveTradeConfig, TradingMode
from config import Config

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramSignalBot:
    """Bot to monitor Telegram groups for trading signals"""
    
    def __init__(self):
        # Initialize from environment variables
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.allowed_groups = self._parse_allowed_groups()
        self.admin_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
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
        
        logger.info(f"TelegramSignalBot initialized in {trading_mode} mode")
    
    def _parse_allowed_groups(self) -> list:
        """Parse allowed groups from environment variable"""
        groups_str = os.getenv('TELEGRAM_ALLOWED_GROUPS', '')
        if not groups_str:
            logger.warning("No TELEGRAM_ALLOWED_GROUPS configured - bot will process all messages")
            return []
        
        # Parse comma-separated list of group IDs/usernames
        groups = [group.strip() for group in groups_str.split(',') if group.strip()]
        logger.info(f"Monitoring {len(groups)} Telegram groups: {groups}")
        return groups
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages from Telegram groups"""
        
        if not update.message or not update.message.text:
            return
        
        message = update.message
        chat_id = message.chat_id
        chat_title = message.chat.title or "Private Chat"
        user = message.from_user
        text = message.text
        
        # Log the message for debugging
        logger.info(f"Received message from {chat_title} (ID: {chat_id}) by {user.first_name}: {text[:100]}...")
        
        # Check if message is from allowed group (if configured)
        if self.allowed_groups and not self._is_allowed_group(chat_id, message.chat.username):
            logger.debug(f"Ignoring message from non-allowed group: {chat_title}")
            return
        
        # Try to process as trading signal
        await self._process_potential_signal(text, chat_title, user.first_name or "Unknown")
    
    def _is_allowed_group(self, chat_id: int, chat_username: Optional[str]) -> bool:
        """Check if the group is in the allowed list"""
        chat_id_str = str(chat_id)
        
        for allowed in self.allowed_groups:
            # Check by chat ID
            if allowed == chat_id_str:
                return True
            # Check by username (with or without @)
            if chat_username and (allowed == chat_username or allowed == f"@{chat_username}"):
                return True
        
        return False
    
    async def _process_potential_signal(self, text: str, chat_title: str, user_name: str):
        """Process a potential trading signal"""
        
        try:
            # Check if this looks like a trading signal
            if not self._looks_like_signal(text):
                logger.debug("Message doesn't look like a trading signal")
                return
            
            logger.info(f"Processing potential signal from {chat_title}")
            
            # Process the signal
            result = self.signal_processor.process_signal(text)
            self.signals_processed += 1
            
            if result["success"]:
                # Execute trade through live trading manager
                trade_result = await self._execute_signal_trade(result, text)
                
                if trade_result["success"]:
                    self.successful_trades += 1
                    await self._notify_admin(
                        f"✅ TRADE EXECUTED\n"
                        f"Source: {chat_title}\n"
                        f"Signal: {result['message']}\n"
                        f"Mode: {self.live_trader.config.mode.value.upper()}\n"
                        f"Stats: {self.successful_trades}✅ / {self.failed_trades}❌ / {self.signals_processed}📊"
                    )
                else:
                    self.failed_trades += 1
                    await self._notify_admin(
                        f"❌ TRADE FAILED\n"
                        f"Source: {chat_title}\n"
                        f"Reason: {trade_result.get('reason', 'Unknown error')}\n"
                        f"Stats: {self.successful_trades}✅ / {self.failed_trades}❌ / {self.signals_processed}📊"
                    )
            else:
                self.failed_trades += 1
                await self._notify_admin(
                    f"⚠️ SIGNAL REJECTED\n"
                    f"Source: {chat_title}\n"
                    f"Reason: {result['message']}\n"
                    f"Errors: {', '.join(result.get('errors', []))}"
                )
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            await self._notify_admin(f"🚨 ERROR processing signal from {chat_title}: {e}")
    
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
        has_crypto_symbol = bool(re.search(r'[A-Z]{3,}USDT|[A-Z]{3,}BTC', text))
        
        return keyword_count >= 2 and has_numbers and has_crypto_symbol
    
    async def _execute_signal_trade(self, signal_result: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Execute the trade using the live trading manager"""
        
        try:
            # Parse the original signal to extract trade data
            parsed_signal = self.signal_processor.parse_signal(original_text)
            
            if not parsed_signal:
                return {"success": False, "reason": "Could not parse signal data"}
            
            # Execute through live trading manager
            trade_result = self.live_trader.execute_trade(parsed_signal)
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error executing signal trade: {e}")
            return {"success": False, "reason": str(e)}
    
    async def _notify_admin(self, message: str):
        """Send notification to admin"""
        
        if not self.admin_chat_id:
            logger.warning("No admin chat ID configured for notifications")
            return
        
        try:
            # This would send a message to the admin
            # For now, just log it
            logger.info(f"ADMIN NOTIFICATION: {message}")
            
            # In a full implementation, you'd send this via the bot API
            # await context.bot.send_message(chat_id=self.admin_chat_id, text=message)
            
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot commands"""
        
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        
        # Only allow admin to use commands
        if str(user_id) != self.admin_chat_id:
            return
        
        command = update.message.text.lower()
        
        if command == '/status':
            status_msg = (
                f"🤖 Telegram Signal Bot Status\n\n"
                f"Mode: {self.live_trader.config.mode.value.upper()}\n"
                f"Signals Processed: {self.signals_processed}\n"
                f"Successful Trades: {self.successful_trades}\n"
                f"Failed Trades: {self.failed_trades}\n"
                f"Monitored Groups: {len(self.allowed_groups)}\n"
                f"Running Since: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await update.message.reply_text(status_msg)
        
        elif command == '/stop':
            await update.message.reply_text("🛑 Stopping signal processing...")
            # This would gracefully stop the bot
        
        elif command == '/emergency':
            self.live_trader.enable_emergency_stop()
            await update.message.reply_text("🚨 EMERGENCY STOP ACTIVATED - All trading halted!")
    
    def run(self):
        """Start the Telegram bot"""
        
        logger.info("Starting Telegram Signal Bot...")
        
        # Create application
        app = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.COMMAND, self.handle_command))
        
        # Start the bot
        logger.info("Bot is running! Monitoring for trading signals...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot"""
    
    try:
        # Setup configuration
        Config.setup_logging()
        Config.validate_config()
        
        # Create and run bot
        bot = TelegramSignalBot()
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()