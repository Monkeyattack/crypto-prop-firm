#!/usr/bin/env python3
"""
Price Simulator - Simulates price movements for testing trailing stops
"""

import time
import sqlite3
import random
import logging
from datetime import datetime
from trailing_take_profit import TrailingTakeProfitManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceSimulator:
    def __init__(self):
        self.db_path = 'trading.db'
        self.trailing_manager = TrailingTakeProfitManager()
        
    def get_open_positions(self):
        """Get all open positions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, side, entry, tp, sl
            FROM trades
            WHERE result = 'open'
        ''')
        
        positions = cursor.fetchall()
        conn.close()
        return positions
    
    def simulate_price_movement(self, entry_price: float, direction: str = 'up', 
                               volatility: float = 0.001) -> float:
        """Simulate realistic price movement"""
        # Base movement
        if direction == 'up':
            trend = random.uniform(0, volatility)
        else:
            trend = random.uniform(-volatility, 0)
        
        # Add noise
        noise = random.uniform(-volatility/3, volatility/3)
        
        # Calculate new price
        price_change = entry_price * (trend + noise)
        new_price = entry_price + price_change
        
        return new_price
    
    def run_simulation(self, duration_minutes: int = 5):
        """Run price simulation for open positions"""
        logger.info(f"Starting price simulation for {duration_minutes} minutes...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            positions = self.get_open_positions()
            
            if not positions:
                logger.info("No open positions to simulate")
                break
            
            for pos_id, symbol, side, entry, tp, sl in positions:
                # Simulate price movement
                # 70% chance of moving toward TP for testing
                if random.random() < 0.7:
                    direction = 'up' if side in ['BUY', 'LONG'] else 'down'
                else:
                    direction = 'down' if side in ['BUY', 'LONG'] else 'up'
                
                # Get current price (start from entry if first time)
                current_price = getattr(self, f'_price_{symbol}', entry)
                
                # Simulate new price
                new_price = self.simulate_price_movement(
                    current_price, 
                    direction,
                    volatility=0.002  # 0.2% volatility
                )
                
                # Store price
                setattr(self, f'_price_{symbol}', new_price)
                
                # Calculate profit
                if side in ['BUY', 'LONG']:
                    profit_pct = ((new_price - entry) / entry) * 100
                else:
                    profit_pct = ((entry - new_price) / entry) * 100
                
                logger.info(f"{symbol}: ${new_price:.2f} ({profit_pct:+.3f}% from entry)")
                
                # Update trailing stop
                exit_signal = self.trailing_manager.update_position(pos_id, new_price)
                
                if exit_signal['action'] != 'none':
                    logger.info(f"EXIT SIGNAL: {exit_signal}")
                    self.close_position(pos_id, new_price, exit_signal['reason'])
            
            # Wait before next update
            time.sleep(2)  # Update every 2 seconds
        
        logger.info("Simulation complete")
    
    def close_position(self, trade_id: int, exit_price: float, reason: str):
        """Close a position"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get position details
        cursor.execute('SELECT entry, side FROM trades WHERE id = ?', (trade_id,))
        entry, side = cursor.fetchone()
        
        # Calculate P&L
        if side in ['BUY', 'LONG']:
            pnl = (exit_price - entry) / entry * 100
        else:
            pnl = (entry - exit_price) / entry * 100
        
        # Update trade
        cursor.execute('''
            UPDATE trades 
            SET exit = ?, result = ?, pnl = ?
            WHERE id = ?
        ''', (exit_price, reason, pnl, trade_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"POSITION CLOSED: Trade #{trade_id} at ${exit_price:.2f} ({pnl:+.2f}%) - {reason}")

if __name__ == "__main__":
    simulator = PriceSimulator()
    simulator.run_simulation(duration_minutes=2)