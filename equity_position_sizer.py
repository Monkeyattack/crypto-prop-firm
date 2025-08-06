#!/usr/bin/env python3
"""
Equity-Based Position Sizing System
Calculates position sizes based on account balance and risk percentage
"""

import sqlite3
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EquityPositionSizer:
    """Professional position sizing based on account equity and risk management"""
    
    def __init__(self, db_path: str = 'trade_log.db'):
        self.db_path = db_path
        self.initial_capital = 10000.0  # Starting capital
        
    def get_current_account_balance(self) -> float:
        """Calculate current account balance from trades"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total P&L from closed trades
            cursor.execute('''
                SELECT SUM(pnl) as total_pnl
                FROM trades
                WHERE result != 'open' AND pnl IS NOT NULL
            ''')
            
            result = cursor.fetchone()
            total_pnl = result[0] if result and result[0] else 0.0
            
            current_balance = self.initial_capital + total_pnl
            conn.close()
            
            logger.info(f"Current account balance: ${current_balance:.2f} (Initial: ${self.initial_capital}, P&L: ${total_pnl:.2f})")
            return max(current_balance, self.initial_capital * 0.5)  # Minimum 50% of initial capital
            
        except Exception as e:
            logger.error(f"Error calculating account balance: {e}")
            return self.initial_capital
    
    def get_risk_settings(self) -> Dict[str, float]:
        """Get risk management settings from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Default settings
            defaults = {
                'risk_per_trade_pct': 2.0,  # 2% risk per trade
                'max_portfolio_risk_pct': 10.0,  # 10% max total risk
                'max_position_size_pct': 20.0,  # 20% max position size
                'min_position_size_usd': 100.0,  # $100 minimum position
                'max_position_size_usd': 5000.0   # $5000 maximum position
            }
            
            cursor.execute('SELECT settings_json FROM trading_settings WHERE id = 1')
            result = cursor.fetchone()
            
            if result and result[0]:
                import json
                settings = json.loads(result[0])
                
                # Extract risk settings with defaults
                risk_settings = {
                    'risk_per_trade_pct': settings.get('risk_per_trade_pct', defaults['risk_per_trade_pct']),
                    'max_portfolio_risk_pct': settings.get('max_portfolio_risk_pct', defaults['max_portfolio_risk_pct']),
                    'max_position_size_pct': settings.get('max_position_size_pct', defaults['max_position_size_pct']),
                    'min_position_size_usd': settings.get('min_position_size_usd', defaults['min_position_size_usd']),
                    'max_position_size_usd': settings.get('max_position_size_usd', defaults['max_position_size_usd'])
                }
            else:
                risk_settings = defaults
            
            conn.close()
            return risk_settings
            
        except Exception as e:
            logger.error(f"Error getting risk settings: {e}")
            return {
                'risk_per_trade_pct': 2.0,
                'max_portfolio_risk_pct': 10.0,
                'max_position_size_pct': 20.0,
                'min_position_size_usd': 100.0,
                'max_position_size_usd': 5000.0
            }
    
    def calculate_position_size(self, signal: Dict) -> Tuple[float, Dict]:
        """Calculate optimal position size based on signal and risk parameters"""
        try:
            current_balance = self.get_current_account_balance()
            risk_settings = self.get_risk_settings()
            
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            
            if entry_price <= 0 or stop_loss <= 0:
                logger.warning(f"Invalid prices: entry={entry_price}, sl={stop_loss}")
                return 0, {'error': 'Invalid entry or stop loss price'}
            
            # Calculate stop loss distance as percentage
            side = signal.get('side', '').upper()
            if side in ['BUY', 'LONG']:
                sl_distance_pct = abs((entry_price - stop_loss) / entry_price) * 100
            else:  # SELL/SHORT
                sl_distance_pct = abs((stop_loss - entry_price) / entry_price) * 100
            
            # Calculate risk amount per trade
            risk_per_trade_pct = risk_settings['risk_per_trade_pct']
            risk_amount_usd = current_balance * (risk_per_trade_pct / 100)
            
            # Calculate position size based on risk
            position_size_usd = risk_amount_usd / (sl_distance_pct / 100)
            
            # Apply position size limits
            min_position = risk_settings['min_position_size_usd']
            max_position_pct = current_balance * (risk_settings['max_position_size_pct'] / 100)
            max_position_abs = risk_settings['max_position_size_usd']
            max_position = min(max_position_pct, max_position_abs)
            
            # Clamp position size
            position_size_usd = max(min_position, min(position_size_usd, max_position))
            
            # Check if we have enough open position capacity
            open_positions_count = self.get_open_positions_count()
            max_positions = self.calculate_max_positions(risk_settings, current_balance)
            
            if open_positions_count >= max_positions:
                return 0, {'error': f'Max positions reached ({open_positions_count}/{max_positions})'}
            
            # Calculate current portfolio risk
            current_risk_pct = self.get_current_portfolio_risk_pct(current_balance)
            new_risk_pct = current_risk_pct + (risk_amount_usd / current_balance * 100)
            
            if new_risk_pct > risk_settings['max_portfolio_risk_pct']:
                return 0, {'error': f'Portfolio risk limit exceeded ({new_risk_pct:.1f}% > {risk_settings["max_portfolio_risk_pct"]}%)'}
            
            # Calculate actual risk with final position size
            actual_risk_usd = position_size_usd * (sl_distance_pct / 100)
            actual_risk_pct = (actual_risk_usd / current_balance) * 100
            
            sizing_details = {
                'account_balance': current_balance,
                'risk_per_trade_pct': risk_per_trade_pct,
                'risk_amount_usd': risk_amount_usd,
                'sl_distance_pct': sl_distance_pct,
                'position_size_usd': position_size_usd,
                'actual_risk_usd': actual_risk_usd,
                'actual_risk_pct': actual_risk_pct,
                'open_positions': open_positions_count,
                'max_positions': max_positions,
                'current_portfolio_risk_pct': current_risk_pct,
                'new_portfolio_risk_pct': new_risk_pct
            }
            
            logger.info(f"Position sizing: ${position_size_usd:.2f} risk=${actual_risk_usd:.2f} ({actual_risk_pct:.2f}%)")
            return position_size_usd, sizing_details
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0, {'error': str(e)}
    
    def calculate_max_positions(self, risk_settings: Dict, current_balance: float) -> int:
        """Calculate maximum number of concurrent positions"""
        max_portfolio_risk = risk_settings['max_portfolio_risk_pct']
        risk_per_trade = risk_settings['risk_per_trade_pct']
        
        # Maximum positions based on portfolio risk
        max_positions_risk = int(max_portfolio_risk / risk_per_trade)
        
        # Hard limit based on account size (prevent too many small positions)
        min_position_size = risk_settings['min_position_size_usd']
        max_positions_size = int(current_balance * 0.8 / min_position_size)  # Use 80% of balance max
        
        return min(max_positions_risk, max_positions_size, 10)  # Hard cap at 10 positions
    
    def get_open_positions_count(self) -> int:
        """Get number of currently open positions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM trades WHERE result = 'open'")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error getting open positions count: {e}")
            return 0
    
    def get_current_portfolio_risk_pct(self, current_balance: float) -> float:
        """Calculate current portfolio risk from open positions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(position_size * 0.05) as total_risk  -- Assuming 5% max loss per position
                FROM trades 
                WHERE result = 'open'
            ''')
            
            result = cursor.fetchone()
            total_risk = result[0] if result and result[0] else 0.0
            
            conn.close()
            return (total_risk / current_balance) * 100
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return 0.0

# Global instance
position_sizer = EquityPositionSizer()

if __name__ == "__main__":
    # Test the position sizer
    test_signal = {
        'symbol': 'ETHUSDT',
        'side': 'Sell',
        'entry_price': 3668.53,
        'take_profit': 3594.43,
        'stop_loss': 3812.67
    }
    
    sizer = EquityPositionSizer()
    position_size, details = sizer.calculate_position_size(test_signal)
    
    print(f"Position Size: ${position_size:.2f}")
    print("Sizing Details:")
    for key, value in details.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")