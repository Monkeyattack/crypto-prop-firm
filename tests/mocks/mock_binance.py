"""
Mock Binance WebSocket and API for testing
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any, Optional
from datetime import datetime
import random


class MockBinanceWebSocket:
    """Mock Binance WebSocket for testing"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSD']
        self.prices = {
            'BTCUSDT': 45000.0,
            'ETHUSDT': 2800.0,
            'ADAUSDT': 0.85,
            'SOLUSD': 167.17
        }
        self.is_connected = False
        self.price_updates = []
        self.subscribers = []
        
    async def connect(self, url: str):
        """Mock WebSocket connection"""
        self.is_connected = True
        return self
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.is_connected = False
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        """Generate mock price updates"""
        if not self.is_connected:
            raise StopAsyncIteration
        
        # Wait a bit to simulate real-time data
        await asyncio.sleep(0.1)
        
        # Pick random symbol and update price
        symbol = random.choice(self.symbols)
        current_price = self.prices[symbol]
        
        # Simulate price movement (-0.5% to +0.5%)
        change_pct = random.uniform(-0.005, 0.005)
        new_price = current_price * (1 + change_pct)
        self.prices[symbol] = new_price
        
        # Create mock message
        mock_msg = Mock()
        mock_msg.type = 1  # TEXT message type
        mock_msg.data = json.dumps({
            's': symbol,
            'p': f"{new_price:.8f}",
            'q': f"{random.uniform(0.1, 10):.8f}",
            't': int(datetime.now().timestamp() * 1000)
        })
        
        return mock_msg
    
    def set_price(self, symbol: str, price: float):
        """Set specific price for testing"""
        self.prices[symbol] = price
    
    def simulate_price_movement(self, symbol: str, percentage: float):
        """Simulate price movement for testing"""
        if symbol in self.prices:
            self.prices[symbol] *= (1 + percentage / 100)
    
    def get_current_price(self, symbol: str) -> float:
        """Get current mock price"""
        return self.prices.get(symbol, 0.0)


class MockBinanceAPI:
    """Mock Binance REST API for testing"""
    
    def __init__(self):
        self.ws = MockBinanceWebSocket()
        self.order_book = {}
        self.trade_history = []
        self.should_fail = False
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Mock symbol info endpoint"""
        if self.should_fail:
            raise Exception("API Error: Connection timeout")
        
        return {
            'symbol': symbol,
            'status': 'TRADING',
            'baseAsset': symbol[:-4] if symbol.endswith('USDT') else symbol[:-3],
            'quoteAsset': 'USDT' if symbol.endswith('USDT') else 'USD',
            'filters': [
                {
                    'filterType': 'PRICE_FILTER',
                    'minPrice': '0.00000100',
                    'maxPrice': '1000000.00000000',
                    'tickSize': '0.00000100'
                }
            ]
        }
    
    async def get_ticker_24hr(self, symbol: str) -> Dict[str, Any]:
        """Mock 24hr ticker stats"""
        if self.should_fail:
            raise Exception("API Error: Rate limit exceeded")
        
        current_price = self.ws.get_current_price(symbol)
        change_24h = random.uniform(-0.1, 0.1)  # -10% to +10%
        
        return {
            'symbol': symbol,
            'priceChange': f"{current_price * change_24h:.8f}",
            'priceChangePercent': f"{change_24h * 100:.2f}",
            'weightedAvgPrice': f"{current_price:.8f}",
            'prevClosePrice': f"{current_price / (1 + change_24h):.8f}",
            'lastPrice': f"{current_price:.8f}",
            'lastQty': f"{random.uniform(0.1, 100):.8f}",
            'bidPrice': f"{current_price * 0.9999:.8f}",
            'askPrice': f"{current_price * 1.0001:.8f}",
            'openPrice': f"{current_price / (1 + change_24h):.8f}",
            'highPrice': f"{current_price * 1.05:.8f}",
            'lowPrice': f"{current_price * 0.95:.8f}",
            'volume': f"{random.uniform(1000, 100000):.8f}",
            'quoteVolume': f"{random.uniform(1000000, 100000000):.2f}",
            'openTime': int((datetime.now().timestamp() - 86400) * 1000),
            'closeTime': int(datetime.now().timestamp() * 1000),
            'firstId': random.randint(1000000, 9999999),
            'lastId': random.randint(1000000, 9999999),
            'count': random.randint(10000, 100000)
        }
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Mock klines/candlestick data"""
        if self.should_fail:
            raise Exception("API Error: Invalid symbol")
        
        current_price = self.ws.get_current_price(symbol)
        klines = []
        
        # Generate mock kline data
        base_time = int(datetime.now().timestamp() * 1000) - (limit * 60000)  # 1min intervals
        
        for i in range(limit):
            # Simulate price movement
            open_price = current_price * (1 + random.uniform(-0.02, 0.02))
            high_price = open_price * (1 + random.uniform(0, 0.01))
            low_price = open_price * (1 - random.uniform(0, 0.01))
            close_price = open_price * (1 + random.uniform(-0.005, 0.005))
            
            klines.append([
                base_time + (i * 60000),  # Open time
                f"{open_price:.8f}",      # Open
                f"{high_price:.8f}",      # High
                f"{low_price:.8f}",       # Low
                f"{close_price:.8f}",     # Close
                f"{random.uniform(100, 1000):.8f}",  # Volume
                base_time + ((i + 1) * 60000) - 1,   # Close time
                f"{random.uniform(10000, 100000):.2f}",  # Quote asset volume
                random.randint(100, 1000),            # Number of trades
                f"{random.uniform(50, 500):.8f}",     # Taker buy base asset volume
                f"{random.uniform(5000, 50000):.2f}", # Taker buy quote asset volume
                "0"  # Unused field
            ])
        
        return klines
    
    def set_should_fail(self, fail: bool):
        """Set whether API calls should fail"""
        self.should_fail = fail


class MockClientSession:
    """Mock aiohttp ClientSession for WebSocket testing"""
    
    def __init__(self):
        self.ws = MockBinanceWebSocket()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def ws_connect(self, url: str):
        """Mock WebSocket connection"""
        return self.ws.connect(url)


# Mock market data provider
class MockMarketDataProvider:
    """Provides mock market data for testing"""
    
    def __init__(self):
        self.api = MockBinanceAPI()
        self.historical_data = {}
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        return self.api.ws.get_current_price(symbol)
    
    async def get_price_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get price history for symbol"""
        klines = await self.api.get_klines(symbol, '1h', hours)
        
        history = []
        for kline in klines:
            history.append({
                'timestamp': kline[0],
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        return history
    
    async def simulate_market_conditions(self, condition: str):
        """Simulate different market conditions"""
        if condition == 'volatile':
            # Increase price volatility
            for symbol in self.api.ws.symbols:
                change = random.uniform(-0.05, 0.05)  # ±5%
                self.api.ws.simulate_price_movement(symbol, change * 100)
        
        elif condition == 'trending_up':
            # Simulate upward trend
            for symbol in self.api.ws.symbols:
                change = random.uniform(0.01, 0.03)  # +1% to +3%
                self.api.ws.simulate_price_movement(symbol, change * 100)
        
        elif condition == 'trending_down':
            # Simulate downward trend
            for symbol in self.api.ws.symbols:
                change = random.uniform(-0.03, -0.01)  # -1% to -3%
                self.api.ws.simulate_price_movement(symbol, change * 100)
        
        elif condition == 'stable':
            # Minimal price movement
            for symbol in self.api.ws.symbols:
                change = random.uniform(-0.001, 0.001)  # ±0.1%
                self.api.ws.simulate_price_movement(symbol, change * 100)


# Global mock instances
mock_binance_ws = MockBinanceWebSocket()
mock_binance_api = MockBinanceAPI()
mock_client_session = MockClientSession()
mock_market_data = MockMarketDataProvider()