#!/usr/bin/env python3
"""
Automated Signal Monitor - Pull signals every 15 minutes and process them
"""

import os
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import time
from signal_processor import SignalProcessor
from trading_engine import TradingEngine
from telegram_notifier import notifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomatedSignalMonitor:
    def __init__(self):
        load_dotenv()
        
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING')
        self.monitored_groups = os.getenv('TELEGRAM_MONITORED_GROUPS', '').split(',')
        
        self.client = None
        self.signal_processor = SignalProcessor()
        self.trading_engine = TradingEngine()
        
        # Track last processed message IDs to avoid duplicates
        self.last_message_ids = {}
        self.load_last_processed_ids()
        
    def load_last_processed_ids(self):
        """Load last processed message IDs from database"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_messages (
                    channel_name TEXT PRIMARY KEY,
                    last_message_id INTEGER,
                    last_check_time DATETIME
                )
            ''')
            
            cursor.execute('SELECT channel_name, last_message_id FROM processed_messages')
            for row in cursor.fetchall():
                self.last_message_ids[row[0]] = row[1]
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error loading last processed IDs: {e}")
    
    def save_last_processed_id(self, channel_name, message_id):
        """Save last processed message ID to database"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO processed_messages 
                (channel_name, last_message_id, last_check_time)
                VALUES (?, ?, ?)
            ''', (channel_name, message_id, datetime.now()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving last processed ID: {e}")
    
    async def connect(self):
        """Connect to Telegram"""
        try:
            self.client = TelegramClient(
                StringSession(self.session_string),
                self.api_id,
                self.api_hash
            )
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("Telegram session not authorized")
                return False
            
            me = await self.client.get_me()
            logger.info(f"Connected as: {me.first_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
    
    async def check_for_new_signals(self):
        """Check for new signals in monitored groups"""
        if not self.client or not self.client.is_connected():
            if not await self.connect():
                return
        
        new_signals = []
        
        try:
            # Find monitored groups
            async for dialog in self.client.iter_dialogs():
                if not (dialog.is_group or dialog.is_channel):
                    continue
                
                group_name = dialog.title
                group_name_lower = group_name.lower()
                
                # Check if this is one of our monitored groups
                monitored = False
                for target in self.monitored_groups:
                    if target.strip().lower() in group_name_lower:
                        monitored = True
                        break
                
                if not monitored:
                    continue
                
                # Get last processed message ID for this group
                last_id = self.last_message_ids.get(group_name, 0)
                
                # Fetch new messages
                messages_found = 0
                async for message in self.client.iter_messages(dialog, min_id=last_id, limit=50):
                    if message.id <= last_id:
                        continue
                    
                    if not message.text:
                        continue
                    
                    messages_found += 1
                    
                    # Try to parse as signal
                    signal_data = self.signal_processor.parse_signal(message.text)
                    
                    if signal_data:
                        signal_data['channel'] = group_name
                        signal_data['message_id'] = message.id
                        signal_data['timestamp'] = message.date
                        new_signals.append(signal_data)
                        
                        # Notify about new signal
                        try:
                            notifier.notify_new_signal(signal_data)
                        except Exception as e:
                            logger.error(f"Failed to send new signal notification: {e}")
                        
                        logger.info(f"New signal found in {group_name}: {signal_data['symbol']} {signal_data['side']}")
                    
                    # Update last processed ID
                    if message.id > last_id:
                        self.last_message_ids[group_name] = message.id
                
                # Save last processed ID
                if group_name in self.last_message_ids:
                    self.save_last_processed_id(group_name, self.last_message_ids[group_name])
                
                if messages_found > 0:
                    logger.info(f"Checked {group_name}: {messages_found} new messages, {len([s for s in new_signals if s['channel'] == group_name])} signals")
        
        except Exception as e:
            logger.error(f"Error checking for signals: {e}")
            # Notify about signal reading failure
            try:
                notifier.notify_error('Signal Reading Failed', str(e))
            except:
                pass
        
        return new_signals
    
    async def process_new_signals(self, signals):
        """Process new signals through trading engine"""
        for signal in signals:
            try:
                # Log signal to database
                self.log_signal_to_db(signal)
                
                # Check if trading is enabled
                if not self.is_trading_enabled():
                    logger.info(f"Trading disabled, skipping signal: {signal['symbol']}")
                    continue
                
                # Process through trading engine
                logger.info(f"Processing signal: {signal['symbol']} {signal['side']} @ {signal['entry_price']}")
                result = self.trading_engine.process_signal(signal)
                
                if result and result.get('success'):
                    # Notify successful trade
                    try:
                        trade_data = {
                            'id': result.get('trade_id'),
                            'symbol': signal['symbol'],
                            'side': signal['side'],
                            'entry': result.get('entry_price', signal['entry_price']),
                            'tp': signal['take_profit'],
                            'sl': signal['stop_loss'],
                            'position_size': result.get('position_size', 1000)
                        }
                        notifier.notify_trade_opened(trade_data)
                        notifier.notify_signal_processed(signal, True)
                    except Exception as e:
                        logger.error(f"Failed to send trade notification: {e}")
                    
                    logger.info(f"Trade executed: {result}")
                else:
                    # Notify failed trade
                    try:
                        notifier.notify_signal_processed(
                            signal, 
                            False, 
                            result.get('reason', 'Trade execution failed') if result else 'No result from trading engine'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send trade failure notification: {e}")
                    
                    logger.warning(f"Trade not executed for signal: {signal['symbol']}")
                    
            except Exception as e:
                logger.error(f"Error processing signal: {e}")
    
    def log_signal_to_db(self, signal):
        """Log signal to database for tracking"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT,
                    message_id INTEGER,
                    timestamp DATETIME,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    take_profit REAL,
                    stop_loss REAL,
                    signal_type TEXT,
                    processed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO signal_log 
                (channel, message_id, timestamp, symbol, side, entry_price, 
                 take_profit, stop_loss, signal_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.get('channel'),
                signal.get('message_id'),
                signal.get('timestamp'),
                signal.get('symbol'),
                signal.get('side'),
                signal.get('entry_price'),
                signal.get('take_profit'),
                signal.get('stop_loss'),
                signal.get('signal_type', 'spot')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
    
    def is_trading_enabled(self):
        """Check if automated trading is enabled"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute("SELECT value FROM trading_settings WHERE key = 'automated_trading_enabled'")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0].lower() == 'true'
            return False  # Default to disabled
            
        except Exception as e:
            logger.error(f"Error checking trading status: {e}")
            return False
    
    async def run_monitoring_loop(self):
        """Run the monitoring loop"""
        logger.info("Starting automated signal monitoring...")
        
        # Initial connection
        if not await self.connect():
            logger.error("Failed to connect to Telegram")
            return
        
        check_interval = 900  # 15 minutes in seconds
        
        while True:
            try:
                logger.info("Checking for new signals...")
                
                # Check for new signals
                new_signals = await self.check_for_new_signals()
                
                if new_signals:
                    logger.info(f"Found {len(new_signals)} new signals")
                    await self.process_new_signals(new_signals)
                else:
                    logger.info("No new signals found")
                
                # Update last check time
                self.update_last_check_time()
                
                # Wait for next check
                logger.info(f"Next check in {check_interval/60} minutes...")
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def update_last_check_time(self):
        """Update last check timestamp"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            # Get current settings
            cursor.execute('SELECT settings_json FROM trading_settings WHERE id = 1')
            result = cursor.fetchone()
            
            if result and result[0]:
                import json
                settings = json.loads(result[0])
                settings['last_signal_check'] = datetime.now().isoformat()
                
                # Update settings with new timestamp
                cursor.execute('''
                    UPDATE trading_settings 
                    SET settings_json = ?, updated_at = ?
                    WHERE id = 1
                ''', (json.dumps(settings), datetime.now()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating last check time: {e}")

async def main():
    """Main function to run the automated monitor"""
    monitor = AutomatedSignalMonitor()
    await monitor.run_monitoring_loop()

if __name__ == "__main__":
    asyncio.run(main())