#!/usr/bin/env python3
"""
Position Monitor - Monitors open positions and triggers trailing stops
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
import aiohttp
import json
from typing import Dict, List
from trailing_take_profit import TrailingTakeProfitManager
from telegram_notifier import notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionMonitor:
    def __init__(self):
        self.db_path = 'trade_log.db'
        self.trailing_manager = TrailingTakeProfitManager()
        self.binance_ws_url = "wss://stream.binance.com:9443/ws"
        self.price_cache = {}
        
    async def get_open_positions(self) -> List[Dict]:
        """Get all open positions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, side, entry, tp, sl, timestamp
            FROM trades
            WHERE result = 'open'
        ''')
        
        positions = []
        for row in cursor.fetchall():
            positions.append({
                'id': row[0],
                'symbol': row[1],
                'side': row[2],
                'entry': row[3],
                'tp': row[4],
                'sl': row[5],
                'timestamp': row[6]
            })
        
        conn.close()
        return positions
    
    def get_price_streams(self, symbols: List[str]) -> str:
        """Create Binance websocket stream names"""
        streams = []
        for symbol in symbols:
            # Convert to lowercase for Binance
            streams.append(f"{symbol.lower()}@aggTrade")
        return "/".join(streams)
    
    async def monitor_prices(self):
        """Monitor prices via Binance websocket"""
        positions = await self.get_open_positions()
        
        if not positions:
            logger.info("No open positions to monitor")
            return
        
        # Get unique symbols
        symbols = list(set([pos['symbol'] for pos in positions]))
        logger.info(f"Monitoring {len(positions)} positions across {len(symbols)} symbols")
        
        # Connect to Binance websocket
        stream_url = f"{self.binance_ws_url}/{self.get_price_streams(symbols)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(stream_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        
                        # Update price cache
                        symbol = data['s']  # Symbol from stream
                        price = float(data['p'])  # Price from trade
                        
                        self.price_cache[symbol] = price
                        
                        # Check positions for this symbol
                        await self.check_positions(symbol, price)
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {msg.data}")
                        break
    
    async def check_positions(self, symbol: str, current_price: float):
        """Check positions for exit signals"""
        positions = await self.get_open_positions()
        
        for position in positions:
            if position['symbol'] != symbol:
                continue
            
            # Update trailing manager
            exit_signal = self.trailing_manager.update_position(
                position['id'], 
                current_price
            )
            
            if exit_signal['action'] != 'none':
                logger.info(f"Exit signal for {symbol}: {exit_signal}")
                await self.close_position(position, current_price, exit_signal)
    
    async def close_position(self, position: Dict, exit_price: float, exit_signal: Dict):
        """Close a position based on exit signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate P&L
        if position['side'].upper() in ['BUY', 'LONG']:
            pnl = (exit_price - position['entry']) / position['entry'] * 100
        else:
            pnl = (position['entry'] - exit_price) / position['entry'] * 100
        
        # Calculate dollar P&L
        position_size = position.get('position_size', 1000)
        pnl_dollar = position_size * (pnl / 100)
        
        # Update trade record
        cursor.execute('''
            UPDATE trades 
            SET exit_price = ?, result = ?, pnl = ?, exit_time = ?, profit_loss = ?
            WHERE id = ?
        ''', (exit_price, exit_signal['reason'], pnl_dollar, datetime.now(), pnl, position['id']))
        
        # Get updated account stats
        cursor.execute('''
            SELECT COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl) as total_pnl
            FROM trades
            WHERE result != 'open'
        ''')
        stats = cursor.fetchone()
        
        # Calculate win rate
        win_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
        
        # Get today's P&L
        cursor.execute('''
            SELECT SUM(pnl) as daily_pnl
            FROM trades
            WHERE DATE(exit_time) = DATE('now')
            AND result != 'open'
        ''')
        daily_pnl = cursor.fetchone()[0] or 0
        
        conn.commit()
        conn.close()
        
        # Send notification
        try:
            trade_data = {
                'id': position['id'],
                'symbol': position['symbol'],
                'side': position['side'],
                'entry': position['entry'],
                'exit_price': exit_price,
                'exit_reason': exit_signal['reason'],
                'pnl': pnl_dollar,
                'pnl_pct': pnl,
                'duration': self.calculate_duration(position.get('timestamp')),
                'new_balance': 10000 + stats[2],  # Initial capital + total P&L
                'daily_pnl': daily_pnl,
                'win_rate': win_rate
            }
            
            notifier.notify_trade_closed(trade_data)
            
        except Exception as e:
            logger.error(f"Failed to send trade close notification: {e}")
        
        logger.info(f"Closed position {position['id']}: {position['symbol']} at {exit_price} ({pnl:.2f}% P&L) - {exit_signal['reason']}")
    
    def calculate_duration(self, entry_time):
        """Calculate trade duration"""
        try:
            if isinstance(entry_time, str):
                entry_dt = datetime.fromisoformat(entry_time)
            else:
                entry_dt = entry_time
            
            duration = datetime.now() - entry_dt
            hours = duration.total_seconds() / 3600
            
            if hours < 1:
                return f"{int(duration.total_seconds() / 60)} minutes"
            elif hours < 24:
                return f"{hours:.1f} hours"
            else:
                return f"{duration.days} days"
        except:
            return "Unknown"
    
    async def run_monitoring_loop(self):
        """Main monitoring loop with reconnection logic"""
        while True:
            try:
                logger.info("Starting position monitoring...")
                await self.monitor_prices()
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)  # Wait before reconnecting

async def main():
    monitor = PositionMonitor()
    await monitor.run_monitoring_loop()

if __name__ == "__main__":
    asyncio.run(main())