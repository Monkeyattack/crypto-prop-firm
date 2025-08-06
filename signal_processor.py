"""
Signal processor for Telegram trading signals
Enhanced version with proper validation, error handling, and risk management
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from database import DatabaseManager, Trade
from config import Config

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Process and validate trading signals from Telegram"""
    
    def __init__(self):
        self.db = DatabaseManager()
        # Multiple signal patterns for different formats
        self.signal_patterns = [
            # Format 1: SMRT Signals format - SYMBOL Side
            re.compile(
                r'(?P<symbol>[A-Z]+USD[T]?)\s+(?P<side>Buy|Sell|Long|Short)(?:\s*\n|\s+)'
                r'(?:.*?\n)*?'  # Allow any content between
                r'(?:Entry|Entry Price):\s*(?P<entry>[\d,.]+)(?:\s*\n|\s+)'
                r'(?:.*?\n)*?'  # Allow any content between
                r'(?:TP|Take Profit|Target):\s*(?P<tp>[\d,.]+)(?:\s*\n|\s+)'
                r'(?:.*?\n)*?'  # Allow any content between
                r'(?:SL|Stop Loss|Stoploss):\s*(?P<sl>[\d,.]+)',
                re.IGNORECASE | re.MULTILINE | re.DOTALL
            ),
            
            # Format 2: Standard Buy/Sell format
            re.compile(
                r'(?P<side>Buy|Sell|Long|Short)\s+(?P<symbol>[\w$]+)\s*\n'
                r'Entry:\s*(?P<entry>[\d,.]+)\s*\n'
                r'(?:TP|Target):\s*(?P<tp>[\d,.]+)\s*\n'
                r'(?:SL|Stop Loss):\s*(?P<sl>[\d,.]+)',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Format 3: Compact format with pipes
            re.compile(
                r'(?P<side>Buy|Sell|Long|Short)\s+[\$]?(?P<symbol>\w+)\s*@\s*(?P<entry>[\d,.]+)\s*\|\s*TP:\s*(?P<tp>[\d,.]+)\s*\|\s*SL:\s*(?P<sl>[\d,.]+)',
                re.IGNORECASE
            ),
            
            # Format 4: Alternative format with "Entry Price", "Take Profit", etc.
            re.compile(
                r'(?P<side>Buy|Sell|Long|Short)\s+(?P<symbol>[\w$]+)\s*\n'
                r'(?:Entry Price|Entry):\s*(?P<entry>[\d,.]+)\s*\n'
                r'(?:Take Profit|Target|TP):\s*(?P<tp>[\d,.]+)\s*\n'
                r'(?:Stop Loss|SL):\s*(?P<sl>[\d,.]+)',
                re.IGNORECASE | re.MULTILINE
            )
        ]
    
    def parse_signal(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse trading signal from Telegram message"""
        try:
            # Clean the message
            message = message.strip()
            
            # Try each pattern until one matches
            match = None
            for pattern in self.signal_patterns:
                match = pattern.search(message)
                if match:
                    break
            
            if not match:
                logger.warning(f"Could not parse signal from message: {message}")
                return None
            
            # Extract values
            side = match.group('side').lower()
            # Normalize side values
            if side in ['long', 'buy']:
                side = 'Buy'
            elif side in ['short', 'sell']:
                side = 'Sell'
            else:
                side = match.group('side').title()
            
            # Clean symbol (remove $ if present)
            symbol = match.group('symbol').upper().replace('$', '')
            
            signal_data = {
                'symbol': symbol,
                'side': side,
                'entry_price': self._parse_price(match.group('entry')),
                'take_profit': self._parse_price(match.group('tp')),
                'stop_loss': self._parse_price(match.group('sl'))
            }
            
            logger.info(f"Parsed signal: {signal_data}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float, handling commas"""
        try:
            # Remove commas and convert to float
            cleaned_price = price_str.replace(',', '')
            return float(cleaned_price)
        except ValueError as e:
            logger.error(f"Error parsing price '{price_str}': {e}")
            raise
    
    def validate_signal(self, signal_data: Dict[str, Any]) -> Tuple[bool, list]:
        """Validate signal data and return validation result"""
        errors = []
        
        try:
            # Create Trade object for validation
            trade = Trade(
                symbol=signal_data['symbol'],
                side=signal_data['side'],
                entry=signal_data['entry'],
                tp=signal_data['tp'],
                sl=signal_data['sl']
            )
            
            # Use Trade's built-in validation
            trade_errors = trade.validate()
            if trade_errors:
                errors.extend(trade_errors)
            
            # Additional business logic validation
            
            # Check if symbol is in allowed list (if configured)
            allowed_symbols = getattr(Config, 'ALLOWED_SYMBOLS', None)
            if allowed_symbols and signal_data['symbol'] not in allowed_symbols:
                errors.append(f"Symbol {signal_data['symbol']} not in allowed list")
            
            # Check risk-reward ratio
            risk_reward_ratio = self._calculate_risk_reward_ratio(
                signal_data['entry'], signal_data['tp'], signal_data['sl'], signal_data['side']
            )
            
            min_rr_ratio = getattr(Config, 'MIN_RISK_REWARD_RATIO', 1.0)
            if risk_reward_ratio < min_rr_ratio:
                errors.append(f"Risk-reward ratio {risk_reward_ratio:.2f} below minimum {min_rr_ratio}")
            
            # Check for duplicate signals
            if self._is_duplicate_signal(signal_data):
                errors.append("Duplicate signal detected")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False, [f"Validation error: {e}"]
    
    def _calculate_risk_reward_ratio(self, entry: float, tp: float, sl: float, side: str) -> float:
        """Calculate risk-reward ratio"""
        try:
            if side.lower() == 'buy':
                risk = entry - sl
                reward = tp - entry
            else:  # sell
                risk = sl - entry
                reward = entry - tp
            
            if risk <= 0:
                return 0
            
            return reward / risk
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio: {e}")
            return 0
    
    def _is_duplicate_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Check if this is a duplicate signal"""
        try:
            # Get recent trades for the same symbol
            trades_df = self.db.get_trades_df(limit=10)
            
            if trades_df.empty:
                return False
            
            # Check for open trades with same symbol and similar entry price
            open_trades = trades_df[
                (trades_df['symbol'] == signal_data['symbol']) &
                (trades_df['result'] == 'open')
            ]
            
            for _, trade in open_trades.iterrows():
                # Check if entry prices are within 1% of each other
                price_diff = abs(trade['entry'] - signal_data['entry']) / trade['entry']
                if price_diff < 0.01:  # 1% threshold
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate signal: {e}")
            return False
    
    def process_signal(self, message: str) -> Dict[str, Any]:
        """Process complete signal from message to trade execution"""
        result = {
            'success': False,
            'message': '',
            'trade_id': None,
            'errors': []
        }
        
        try:
            # Parse signal
            signal_data = self.parse_signal(message)
            if not signal_data:
                result['message'] = 'Failed to parse signal'
                result['errors'] = ['Invalid signal format']
                return result
            
            # Validate signal
            is_valid, validation_errors = self.validate_signal(signal_data)
            if not is_valid:
                result['message'] = 'Signal validation failed'
                result['errors'] = validation_errors
                return result
            
            # Check risk management constraints
            risk_check = self._check_risk_management()
            if not risk_check['allowed']:
                result['message'] = 'Risk management check failed'
                result['errors'] = [risk_check['reason']]
                return result
            
            # Create and add trade
            trade = Trade(
                symbol=signal_data['symbol'],
                side=signal_data['side'],
                entry=signal_data['entry'],
                tp=signal_data['tp'],
                sl=signal_data['sl'],
                timestamp=datetime.now().isoformat()
            )
            
            if self.db.add_trade(trade):
                result['success'] = True
                result['message'] = f"Trade added: {trade.symbol} {trade.side} @ {trade.entry}"
                logger.info(result['message'])
            else:
                result['message'] = 'Failed to add trade to database'
                result['errors'] = ['Database error']
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            result['message'] = f'Processing error: {e}'
            result['errors'] = [str(e)]
            return result
    
    def _check_risk_management(self) -> Dict[str, Any]:
        """Check risk management constraints"""
        try:
            # Check maximum open trades
            trades_df = self.db.get_trades_df()
            if not trades_df.empty:
                open_trades_count = len(trades_df[trades_df['result'] == 'open'])
                if open_trades_count >= Config.MAX_OPEN_TRADES:
                    return {
                        'allowed': False,
                        'reason': f'Maximum open trades ({Config.MAX_OPEN_TRADES}) reached'
                    }
            
            # Check current capital
            current_capital = self.db.get_current_capital()
            min_capital = Config.INITIAL_CAPITAL * 0.5  # Don't trade below 50% of initial
            
            if current_capital < min_capital:
                return {
                    'allowed': False,
                    'reason': f'Capital too low: ${current_capital:.2f} < ${min_capital:.2f}'
                }
            
            return {'allowed': True, 'reason': 'OK'}
            
        except Exception as e:
            logger.error(f"Error checking risk management: {e}")
            return {'allowed': False, 'reason': f'Risk management check error: {e}'}
    
    def simulate_trade_outcome(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate trade outcome for testing purposes"""
        try:
            # This is a simplified simulation - in reality you'd use market data
            import random
            
            # Simulate market movement
            entry_price = trade_data['entry']
            tp_price = trade_data['tp']
            sl_price = trade_data['sl']
            
            # Simple random outcome based on risk-reward ratio
            rr_ratio = self._calculate_risk_reward_ratio(
                entry_price, tp_price, sl_price, trade_data['side']
            )
            
            # Higher RR ratio = higher chance of success
            win_probability = min(0.7, 0.4 + (rr_ratio * 0.1))
            
            outcome = 'tp' if random.random() < win_probability else 'sl'
            exit_price = tp_price if outcome == 'tp' else sl_price
            
            # Calculate PnL
            trade = Trade(
                symbol=trade_data['symbol'],
                side=trade_data['side'],
                entry=entry_price,
                tp=tp_price,
                sl=sl_price
            )
            
            pnl = trade.calculate_pnl(exit_price)
            
            return {
                'outcome': outcome,
                'exit_price': exit_price,
                'pnl': pnl,
                'win_probability': win_probability
            }
            
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            return {'outcome': 'error', 'pnl': 0}

# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    Config.setup_logging()
    
    # Test signal processing
    processor = SignalProcessor()
    
    # Test message
    test_message = """
    Buy BTCUSDT
    Entry: 45,000
    TP: 47,000
    SL: 43,000
    """
    
    result = processor.process_signal(test_message)
    print(f"Processing result: {result}")