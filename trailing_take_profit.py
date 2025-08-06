#!/usr/bin/env python3
"""
Trailing Take Profit System - Dynamic profit taking based on price movement
"""

import logging
from datetime import datetime
import sqlite3
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class TrailingTakeProfitManager:
    def __init__(self):
        self.active_positions = {}  # Track highest prices reached
        self.db_path = 'trade_log.db'
        
        # Default trailing parameters (can be overridden from settings)
        self.default_config = {
            'target_profit_pct': 5.0,      # Target profit percentage
            'activation_pct': 4.5,         # Start trailing after this profit %
            'trail_distance_pct': 1.5,     # Trail by this percentage
            'min_profit_pct': 3.5,         # Minimum profit to take
            'scale_out_levels': [          # Scaled exit levels
                {'pct': 5.0, 'size': 0.5},   # Exit 50% at 5%
                {'pct': 7.0, 'size': 0.3},   # Exit 30% at 7%
                {'pct': 10.0, 'size': 0.2}   # Exit 20% at 10%
            ]
        }
        
        self.load_settings()
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trailing_positions (
                trade_id INTEGER PRIMARY KEY,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                highest_price REAL,
                highest_profit_pct REAL,
                trailing_activated BOOLEAN,
                partial_exits TEXT,
                last_update DATETIME,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_settings(self):
        """Load trailing settings from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT key, value FROM trading_settings 
                WHERE key LIKE 'trailing_%'
            ''')
            
            settings = {}
            for key, value in cursor.fetchall():
                clean_key = key.replace('trailing_', '')
                try:
                    settings[clean_key] = float(value)
                except ValueError:
                    settings[clean_key] = value
            
            # Update config with database settings
            if settings:
                self.default_config.update(settings)
            
            conn.close()
        except Exception as e:
            logger.error(f"Error loading trailing settings: {e}")
    
    def track_position(self, trade_id: int, symbol: str, side: str, entry_price: float):
        """Start tracking a new position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trailing_positions 
                (trade_id, symbol, side, entry_price, highest_price, 
                 highest_profit_pct, trailing_activated, partial_exits, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_id, symbol, side, entry_price, entry_price, 
                0.0, False, '{}', datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Started tracking position: {symbol} @ {entry_price}")
            
        except Exception as e:
            logger.error(f"Error tracking position: {e}")
    
    def update_position(self, trade_id: int, current_price: float) -> Dict:
        """Update position with current price and check for exit signals"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get position data
            cursor.execute('''
                SELECT symbol, side, entry_price, highest_price, 
                       highest_profit_pct, trailing_activated, partial_exits
                FROM trailing_positions 
                WHERE trade_id = ?
            ''', (trade_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'action': 'none', 'reason': 'position not found'}
            
            symbol, side, entry_price, highest_price, highest_profit_pct, trailing_activated, partial_exits = result
            
            # Calculate current profit
            if side.upper() in ['BUY', 'LONG']:
                current_profit_pct = ((current_price - entry_price) / entry_price) * 100
                new_highest = max(current_price, highest_price)
            else:  # SELL, SHORT
                current_profit_pct = ((entry_price - current_price) / entry_price) * 100
                new_highest = min(current_price, highest_price)
            
            new_highest_profit = max(current_profit_pct, highest_profit_pct)
            
            # Update highest values
            cursor.execute('''
                UPDATE trailing_positions 
                SET highest_price = ?, highest_profit_pct = ?, last_update = ?
                WHERE trade_id = ?
            ''', (new_highest, new_highest_profit, datetime.now(), trade_id))
            
            # Check exit conditions
            exit_signal = self.check_exit_conditions(
                current_profit_pct, 
                new_highest_profit, 
                trailing_activated,
                partial_exits
            )
            
            # Update trailing activation if needed
            if not trailing_activated and current_profit_pct >= self.default_config['activation_pct']:
                cursor.execute('''
                    UPDATE trailing_positions 
                    SET trailing_activated = 1 
                    WHERE trade_id = ?
                ''', (trade_id,))
                logger.info(f"Trailing activated for {symbol} at {current_profit_pct:.2f}% profit")
            
            conn.commit()
            conn.close()
            
            return {
                'action': exit_signal['action'],
                'reason': exit_signal['reason'],
                'current_profit_pct': current_profit_pct,
                'highest_profit_pct': new_highest_profit,
                'trailing_active': trailing_activated or current_profit_pct >= self.default_config['activation_pct']
            }
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return {'action': 'none', 'reason': 'error'}
    
    def check_exit_conditions(self, current_profit: float, highest_profit: float, 
                            trailing_active: bool, partial_exits: str) -> Dict:
        """Check if position should be exited based on trailing logic"""
        
        # Check scaled exit levels
        import json
        exits_done = json.loads(partial_exits) if partial_exits else {}
        
        for level in self.default_config['scale_out_levels']:
            level_pct = level['pct']
            level_size = level['size']
            
            if current_profit >= level_pct and str(level_pct) not in exits_done:
                return {
                    'action': 'partial_exit',
                    'size': level_size,
                    'reason': f'scaled_exit_{level_pct}%',
                    'level': level_pct
                }
        
        # Check trailing stop
        if trailing_active:
            trail_distance = self.default_config['trail_distance_pct']
            stop_level = highest_profit - trail_distance
            
            if current_profit <= stop_level and current_profit >= self.default_config['min_profit_pct']:
                return {
                    'action': 'full_exit',
                    'reason': f'trailing_stop_hit',
                    'profit': current_profit
                }
        
        # Check if we've dropped below minimum profit after being in profit
        if highest_profit >= self.default_config['activation_pct']:
            if current_profit < self.default_config['min_profit_pct']:
                return {
                    'action': 'full_exit',
                    'reason': 'profit_protection',
                    'profit': current_profit
                }
        
        return {'action': 'none', 'reason': 'conditions_not_met'}
    
    def record_partial_exit(self, trade_id: int, level: float, size: float):
        """Record a partial exit"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT partial_exits FROM trailing_positions WHERE trade_id = ?', (trade_id,))
            result = cursor.fetchone()
            
            if result:
                import json
                exits = json.loads(result[0]) if result[0] else {}
                exits[str(level)] = size
                
                cursor.execute('''
                    UPDATE trailing_positions 
                    SET partial_exits = ? 
                    WHERE trade_id = ?
                ''', (json.dumps(exits), trade_id))
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording partial exit: {e}")
    
    def get_position_status(self, trade_id: int) -> Optional[Dict]:
        """Get current status of a tracked position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, side, entry_price, highest_price, 
                       highest_profit_pct, trailing_activated, partial_exits, last_update
                FROM trailing_positions 
                WHERE trade_id = ?
            ''', (trade_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'symbol': result[0],
                    'side': result[1],
                    'entry_price': result[2],
                    'highest_price': result[3],
                    'highest_profit_pct': result[4],
                    'trailing_activated': result[5],
                    'partial_exits': result[6],
                    'last_update': result[7]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position status: {e}")
            return None

# Backtesting function to optimize trailing parameters
def backtest_trailing_parameters(historical_data, test_params):
    """Backtest different trailing parameter combinations"""
    results = []
    
    for params in test_params:
        total_profit = 0
        trades_count = 0
        winning_trades = 0
        
        for signal in historical_data:
            # Simulate price movement
            entry_price = signal['entry_price']
            
            # Simulate reaching various profit levels
            max_profit_reached = signal.get('max_profit_pct', 10)  # Simulated max profit
            
            # Check if trailing would have been activated
            if max_profit_reached >= params['activation_pct']:
                # Calculate exit point based on trailing
                exit_profit = max(
                    params['min_profit_pct'],
                    max_profit_reached - params['trail_distance_pct']
                )
                
                if exit_profit > 0:
                    winning_trades += 1
                    total_profit += exit_profit
            else:
                # No trailing, check if hit target
                if max_profit_reached >= params['target_profit_pct']:
                    winning_trades += 1
                    total_profit += params['target_profit_pct']
                else:
                    # Assume stop loss hit
                    total_profit -= 5  # Assume 5% stop loss
            
            trades_count += 1
        
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
        avg_profit = total_profit / trades_count if trades_count > 0 else 0
        
        results.append({
            'params': params,
            'total_profit': total_profit,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'trades_count': trades_count
        })
    
    return results