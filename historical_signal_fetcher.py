#!/usr/bin/env python3
"""
Historical Signal Fetcher - Pull past signals from Telegram group
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import sqlite3
import re
import json
from signal_processor import SignalProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HistoricalSignalFetcher:
    def __init__(self):
        load_dotenv()
        
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING')
        self.target_groups = os.getenv('TELEGRAM_MONITORED_GROUPS', '').split(',')
        
        self.client = None
        self.signal_processor = SignalProcessor()
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize database for historical signals"""
        conn = sqlite3.connect('trading.db')
        cursor = conn.cursor()
        
        # Create historical_signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER UNIQUE,
                channel_name TEXT,
                message_text TEXT,
                message_date DATETIME,
                signal_type TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                parsed_successfully BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized for historical signals")
    
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
    
    async def fetch_historical_signals(self, days_back=30, limit=1000):
        """Fetch historical signals from target groups"""
        if not await self.connect():
            return False
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Fetching signals from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        total_messages = 0
        total_signals = 0
        
        try:
            # Find target groups
            async for dialog in self.client.iter_dialogs():
                if not (dialog.is_group or dialog.is_channel):
                    continue
                
                group_name = dialog.title.lower()
                
                # Check if this is one of our target groups
                target_found = False
                for target in self.target_groups:
                    if target.strip().lower() in group_name:
                        target_found = True
                        break
                
                if not target_found:
                    continue
                
                logger.info(f"Processing group: {dialog.title}")
                
                # Fetch messages from this group
                messages_processed = 0
                signals_found = 0
                
                async for message in self.client.iter_messages(
                    dialog,
                    offset_date=end_date,
                    reverse=True,
                    limit=limit
                ):
                    if message.date < start_date:
                        continue
                    
                    if not message.text:
                        continue
                    
                    messages_processed += 1
                    
                    # Try to parse as signal
                    signal_data = self.signal_processor.parse_signal(message.text)
                    
                    if signal_data:
                        signals_found += 1
                        await self.store_historical_signal(
                            message.id,
                            dialog.title,
                            message.text,
                            message.date,
                            signal_data
                        )
                    else:
                        # Store unparsed message for analysis
                        await self.store_historical_signal(
                            message.id,
                            dialog.title,
                            message.text,
                            message.date,
                            None
                        )
                
                total_messages += messages_processed
                total_signals += signals_found
                
                logger.info(f"Group {dialog.title}: {messages_processed} messages, {signals_found} signals")
        
        except Exception as e:
            logger.error(f"Error fetching historical signals: {e}")
            return False
        
        finally:
            await self.client.disconnect()
        
        logger.info(f"Historical fetch complete: {total_messages} messages, {total_signals} signals")
        return True
    
    async def store_historical_signal(self, message_id, channel_name, message_text, message_date, signal_data):
        """Store historical signal in database"""
        conn = sqlite3.connect('trading.db')
        cursor = conn.cursor()
        
        try:
            if signal_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO historical_signals 
                    (message_id, channel_name, message_text, message_date, signal_type, 
                     symbol, side, entry_price, take_profit, stop_loss, parsed_successfully)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_id,
                    channel_name,
                    message_text,
                    message_date,
                    signal_data.get('signal_type', 'unknown'),
                    signal_data.get('symbol', ''),
                    signal_data.get('side', ''),
                    signal_data.get('entry_price', 0),
                    signal_data.get('take_profit', 0),
                    signal_data.get('stop_loss', 0),
                    True
                ))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO historical_signals 
                    (message_id, channel_name, message_text, message_date, parsed_successfully)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    message_id,
                    channel_name,
                    message_text,
                    message_date,
                    False
                ))
            
            conn.commit()
            
        except sqlite3.IntegrityError:
            # Message already exists
            pass
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
        finally:
            conn.close()
    
    def get_historical_signals_stats(self):
        """Get statistics about historical signals"""
        conn = sqlite3.connect('trading.db')
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM historical_signals')
        total_messages = cursor.fetchone()[0]
        
        # Parsed signals
        cursor.execute('SELECT COUNT(*) FROM historical_signals WHERE parsed_successfully = 1')
        parsed_signals = cursor.fetchone()[0]
        
        # Date range
        cursor.execute('SELECT MIN(message_date), MAX(message_date) FROM historical_signals')
        date_range = cursor.fetchone()
        
        # Symbols
        cursor.execute('SELECT symbol, COUNT(*) FROM historical_signals WHERE parsed_successfully = 1 GROUP BY symbol ORDER BY COUNT(*) DESC')
        symbols = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_messages': total_messages,
            'parsed_signals': parsed_signals,
            'date_range': date_range,
            'top_symbols': symbols[:10]
        }

async def main():
    """Main function to fetch historical signals"""
    fetcher = HistoricalSignalFetcher()
    
    print("=== Historical Signal Fetcher ===")
    print("This will fetch historical signals from your Telegram groups")
    
    # Get user input for fetch parameters
    try:
        days_back = int(input("How many days back to fetch? (default 30): ") or "30")
        limit = int(input("Maximum messages per group? (default 1000): ") or "1000")
    except ValueError:
        days_back = 30
        limit = 1000
    
    print(f"\nFetching last {days_back} days with limit of {limit} messages per group...")
    
    # Fetch signals
    success = await fetcher.fetch_historical_signals(days_back, limit)
    
    if success:
        print("\n=== Fetch Complete ===")
        stats = fetcher.get_historical_signals_stats()
        
        print(f"Total messages: {stats['total_messages']}")
        print(f"Parsed signals: {stats['parsed_signals']}")
        
        if stats['date_range'][0] and stats['date_range'][1]:
            print(f"Date range: {stats['date_range'][0]} to {stats['date_range'][1]}")
        
        if stats['top_symbols']:
            print("\nTop symbols:")
            for symbol, count in stats['top_symbols']:
                print(f"  {symbol}: {count} signals")
        
        print(f"\nNext step: Run backtesting analysis")
        print("python backtesting_engine.py")
    else:
        print("Failed to fetch historical signals")

if __name__ == "__main__":
    asyncio.run(main())