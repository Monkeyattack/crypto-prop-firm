"""
Mock MT5 terminal for testing
"""

from unittest.mock import Mock
from datetime import datetime
from typing import Dict, Any, List, Optional
import random


class MockMT5Terminal:
    """Mock MetaTrader 5 terminal for testing"""
    
    def __init__(self):
        self.is_initialized = False
        self.is_logged_in = False
        self.positions = {}
        self.orders = {}
        self.account_info = {
            'login': 12345,
            'balance': 10000.0,
            'equity': 10000.0,
            'margin': 0.0,
            'free_margin': 10000.0,
            'profit': 0.0,
            'currency': 'USD',
            'server': 'TestServer-Demo'
        }
        self.last_order_id = 1000
        self.last_position_id = 2000
        
        # Market prices simulation
        self.symbol_prices = {
            'BTCUSDT': 45000.0,
            'ETHUSDT': 2800.0,
            'ADAUSDT': 0.85,
            'SOLUSD': 167.17
        }
    
    def initialize(self) -> bool:
        """Initialize MT5 connection"""
        self.is_initialized = True
        return True
    
    def login(self, login: int, password: str, server: str) -> bool:
        """Login to MT5 account"""
        if not self.is_initialized:
            return False
        
        self.is_logged_in = True
        self.account_info['login'] = login
        self.account_info['server'] = server
        return True
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        self.is_initialized = False
        self.is_logged_in = False
        self.positions.clear()
        self.orders.clear()
    
    def account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.is_logged_in:
            return None
        return self.account_info.copy()
    
    def symbol_info_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current tick for symbol"""
        if symbol not in self.symbol_prices:
            return None
        
        price = self.symbol_prices[symbol]
        # Add small random spread
        spread = price * 0.0001  # 0.01% spread
        
        return {
            'time': int(datetime.now().timestamp()),
            'bid': price - spread/2,
            'ask': price + spread/2,
            'last': price,
            'volume': random.randint(100, 1000)
        }
    
    def order_send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send trading order"""
        if not self.is_logged_in:
            return {'retcode': 10004, 'comment': 'No connection'}
        
        # Simulate order processing
        order_id = self.last_order_id
        self.last_order_id += 1
        
        symbol = request.get('symbol', 'UNKNOWN')
        action = request.get('action')
        volume = request.get('volume', 0.0)
        price = request.get('price', 0.0)
        
        # Simulate market orders
        if action in [0, 1]:  # BUY or SELL
            current_price = self.symbol_prices.get(symbol, price)
            
            # Create position
            position_id = self.last_position_id
            self.last_position_id += 1
            
            self.positions[position_id] = {
                'ticket': position_id,
                'symbol': symbol,
                'type': action,
                'volume': volume,
                'price_open': current_price,
                'sl': request.get('sl', 0.0),
                'tp': request.get('tp', 0.0),
                'time': int(datetime.now().timestamp()),
                'profit': 0.0,
                'comment': request.get('comment', '')
            }
            
            return {
                'retcode': 10009,  # TRADE_RETCODE_DONE
                'deal': order_id,
                'order': order_id,
                'volume': volume,
                'price': current_price,
                'comment': 'Order executed successfully'
            }
        
        return {'retcode': 10013, 'comment': 'Invalid request'}
    
    def positions_get(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get open positions"""
        if not self.is_logged_in:
            return []
        
        positions = list(self.positions.values())
        
        if symbol:
            positions = [p for p in positions if p['symbol'] == symbol]
        
        # Update profits based on current prices
        for position in positions:
            current_price = self.symbol_prices.get(position['symbol'], position['price_open'])
            
            if position['type'] == 0:  # BUY
                position['profit'] = (current_price - position['price_open']) * position['volume']
            else:  # SELL
                position['profit'] = (position['price_open'] - current_price) * position['volume']
        
        return positions
    
    def position_close_by(self, ticket: int) -> Dict[str, Any]:
        """Close position by ticket"""
        if ticket in self.positions:
            position = self.positions.pop(ticket)
            
            return {
                'retcode': 10009,
                'deal': self.last_order_id,
                'order': self.last_order_id,
                'volume': position['volume'],
                'comment': 'Position closed'
            }
        
        return {'retcode': 10013, 'comment': 'Position not found'}
    
    def update_price(self, symbol: str, price: float):
        """Update symbol price (for testing)"""
        self.symbol_prices[symbol] = price
    
    def simulate_price_movement(self, symbol: str, percentage: float):
        """Simulate price movement (for testing)"""
        if symbol in self.symbol_prices:
            current_price = self.symbol_prices[symbol]
            new_price = current_price * (1 + percentage / 100)
            self.symbol_prices[symbol] = new_price
    
    def check_stops(self):
        """Check and trigger stop losses/take profits"""
        triggered = []
        
        for ticket, position in list(self.positions.items()):
            symbol = position['symbol']
            current_price = self.symbol_prices.get(symbol, position['price_open'])
            
            should_close = False
            close_reason = ""
            
            if position['type'] == 0:  # BUY position
                if position['sl'] > 0 and current_price <= position['sl']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif position['tp'] > 0 and current_price >= position['tp']:
                    should_close = True
                    close_reason = "Take Profit"
            else:  # SELL position
                if position['sl'] > 0 and current_price >= position['sl']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif position['tp'] > 0 and current_price <= position['tp']:
                    should_close = True
                    close_reason = "Take Profit"
            
            if should_close:
                closed_position = self.positions.pop(ticket)
                triggered.append({
                    'ticket': ticket,
                    'symbol': symbol,
                    'close_price': current_price,
                    'reason': close_reason,
                    'position': closed_position
                })
        
        return triggered


# Global mock instance
mock_mt5 = MockMT5Terminal()