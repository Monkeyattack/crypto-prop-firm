#!/usr/bin/env python3
"""
Trading Engine - Processes signals with risk management and settings integration
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional
from trailing_take_profit import TrailingTakeProfitManager
from market_analyzer import MarketAnalyzer
from equity_position_sizer import position_sizer
import asyncio

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self):
        self.db_path = 'trade_log.db'
        self.trailing_manager = TrailingTakeProfitManager()
        self.market_analyzer = MarketAnalyzer()
        self.load_settings()
        
    def load_settings(self):
        """Load trading settings from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all settings
            cursor.execute('SELECT key, value FROM trading_settings')
            self.settings = {}
            for key, value in cursor.fetchall():
                try:
                    # Try to convert to float/int if possible
                    if '.' in value:
                        self.settings[key] = float(value)
                    else:
                        self.settings[key] = int(value)
                except ValueError:
                    # Keep as string if conversion fails
                    self.settings[key] = value
            
            conn.close()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Use defaults
            self.settings = {
                'max_position_size': 100,
                'max_daily_trades': 8,
                'max_open_positions': 5,
                'stop_loss_pct': 5.0,
                'symbol_filtering_enabled': 'true'
            }
    
    def check_risk_limits(self) -> Dict:
        """Check if we can take new trades based on equity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current capital
            cursor.execute('''
                SELECT value FROM capital_history 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            result = cursor.fetchone()
            current_capital = float(result[0]) if result else 10000.0
            
            # Calculate current exposure
            cursor.execute('''
                SELECT SUM(entry * 100) FROM trades 
                WHERE result = 'open'
            ''')
            result = cursor.fetchone()
            current_exposure = float(result[0]) if result and result[0] else 0.0
            
            # Count open positions
            cursor.execute('''
                SELECT COUNT(*) FROM trades 
                WHERE result = 'open'
            ''')
            open_positions = cursor.fetchone()[0]
            
            conn.close()
            
            # Calculate percentages
            exposure_pct = (current_exposure / current_capital * 100) if current_capital > 0 else 0
            available_capital = current_capital - current_exposure
            available_pct = (available_capital / current_capital * 100) if current_capital > 0 else 0
            
            # Check limits
            max_exposure_pct = float(self.settings.get('max_exposure_pct', 50))
            min_available_pct = float(self.settings.get('min_available_equity_pct', 20))
            
            can_trade = (
                exposure_pct < max_exposure_pct and
                available_pct > min_available_pct and
                open_positions < int(self.settings.get('max_open_positions', 50))
            )
            
            return {
                'can_trade': can_trade,
                'current_capital': current_capital,
                'current_exposure': current_exposure,
                'exposure_pct': exposure_pct,
                'available_capital': available_capital,
                'available_pct': available_pct,
                'open_positions': open_positions,
                'max_exposure_pct': max_exposure_pct,
                'reason': 'ok' if can_trade else f'Exposure: {exposure_pct:.1f}% (max {max_exposure_pct}%)'
            }
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {'can_trade': False, 'reason': 'error'}
    
    def check_symbol_filter(self, symbol: str) -> bool:
        """Check if symbol is allowed for trading"""
        if self.settings.get('symbol_filtering_enabled', 'true') != 'true':
            return True
        
        # Get blacklisted symbols
        blacklist = self.settings.get('blacklisted_symbols', '').split(',')
        blacklist = [s.strip().upper() for s in blacklist if s.strip()]
        
        if symbol.upper() in blacklist:
            logger.info(f"Symbol {symbol} is blacklisted")
            return False
        
        return True
    
    def process_signal(self, signal: Dict) -> Optional[Dict]:
        """Process a trading signal"""
        try:
            # Reload settings for each signal
            self.load_settings()
            
            # Check if automated trading is enabled
            if self.settings.get('automated_trading_enabled', 'false') != 'true':
                logger.info("Automated trading is disabled")
                return None
            
            # Check risk limits
            risk_check = self.check_risk_limits()
            if not risk_check['can_trade']:
                logger.warning(f"Risk limits exceeded: {risk_check}")
                return None
            
            # Check symbol filter
            if not self.check_symbol_filter(signal['symbol']):
                return None
            
            # Validate signal data
            required_fields = ['symbol', 'side', 'entry_price']
            if not all(field in signal for field in required_fields):
                logger.error(f"Missing required fields in signal: {signal}")
                return None
            
            # Apply strategy settings
            strategy = self.settings.get('take_profit_strategy', 'scaled')
            
            if strategy == 'scaled':
                # Use scaled exit levels
                take_profit = self.settings.get('tp_level_1_pct', 5.0)
            elif strategy == 'trailing':
                # Use trailing target
                take_profit = self.settings.get('tp_level_1_pct', 0.75)
            else:
                # Fixed strategy
                take_profit = self.settings.get('tp_level_1_pct', 5.0)
            
            stop_loss = self.settings.get('stop_loss_pct', 5.0)
            
            # Use equity-based position sizing
            symbol = signal['symbol'].upper()
            
            # Get market analysis
            market_analysis = None
            try:
                # Run async market analysis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                market_analysis = loop.run_until_complete(
                    self.market_analyzer.analyze_symbol(symbol)
                )
                loop.close()
            except Exception as e:
                logger.error(f"Error getting market analysis: {e}")
            
            # Apply market conditions to TP/SL
            if market_analysis:
                # Skip trade if market conditions are poor
                if market_analysis.get('trade_recommendation') == 'strong_sell':
                    logger.warning(f"Market conditions poor for {symbol} (score: {market_analysis.get('overall_score', 0):.1f})")
                    return {'success': False, 'reason': 'Poor market conditions'}
                
                # Adjust TP/SL based on volatility
                tp_adjustment = market_analysis.get('recommended_tp_adjustment', 1.0)
                sl_adjustment = market_analysis.get('recommended_sl_adjustment', 1.0)
                
                take_profit *= tp_adjustment
                stop_loss *= sl_adjustment
                
                logger.info(f"Market analysis for {symbol}: Score={market_analysis.get('overall_score', 0):.1f}, Vol={market_analysis.get('volatility_1h', 0):.2f}%, Volume Ratio={market_analysis.get('volume_ratio', 1):.2f}")
            
            # Calculate actual prices first
            entry_price = float(signal['entry_price'])
            
            if signal['side'].upper() in ['BUY', 'LONG']:
                tp_price = entry_price * (1 + take_profit / 100)
                sl_price = entry_price * (1 - stop_loss / 100)
            else:
                tp_price = entry_price * (1 - take_profit / 100)
                sl_price = entry_price * (1 + stop_loss / 100)
            
            # Create enhanced signal with calculated prices for position sizer
            enhanced_signal = {
                **signal,
                'entry_price': entry_price,
                'take_profit': tp_price,
                'stop_loss': sl_price
            }
            
            # Calculate equity-based position size
            position_size, sizing_details = position_sizer.calculate_position_size(enhanced_signal)
            
            if position_size <= 0:
                error_msg = sizing_details.get('error', 'Position size calculation failed')
                logger.warning(f"Cannot execute trade: {error_msg}")
                return {'success': False, 'reason': error_msg, 'sizing_details': sizing_details}
            
            logger.info(f"Equity-based position sizing: {symbol} - ${position_size:.2f} (Risk: ${sizing_details.get('actual_risk_usd', 0):.2f}, {sizing_details.get('actual_risk_pct', 0):.2f}%)")
            
            # Create trade record
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry, tp, sl, result, timestamp, position_size)
                VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            ''', (
                signal['symbol'],
                signal['side'],
                entry_price,
                tp_price,
                sl_price,
                datetime.now(),
                position_size
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Start tracking with trailing manager if enabled
            if self.settings.get('trailing_enabled', 'true') == 'true':
                self.trailing_manager.track_position(
                    trade_id, 
                    signal['symbol'], 
                    signal['side'], 
                    entry_price
                )
            
            logger.info(f"Trade executed: {signal['symbol']} {signal['side']} @ {entry_price}")
            
            return {
                'success': True,
                'trade_id': trade_id,
                'symbol': signal['symbol'],
                'side': signal['side'],
                'entry_price': entry_price,
                'tp': tp_price,
                'sl': sl_price,
                'position_size': position_size,
                'strategy': strategy,
                'sizing_details': sizing_details
            }
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return None
    
    def update_positions(self):
        """Update all open positions with current prices"""
        # This would be called periodically to check trailing stops
        # For now, it's a placeholder for price feed integration
        pass

if __name__ == "__main__":
    engine = TradingEngine()
    print("Trading engine initialized")