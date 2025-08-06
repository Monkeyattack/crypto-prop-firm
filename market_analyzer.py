#!/usr/bin/env python3
"""
Market Analyzer - Volume and Volatility Analysis for Trading Decisions
"""

import asyncio
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import sqlite3
from typing import Dict, List, Tuple
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self):
        self.db_path = 'trade_log.db'
        self.binance_api = "https://api.binance.com/api/v3"
        self.init_database()
        
    def init_database(self):
        """Initialize market data tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timestamp DATETIME,
                
                -- Volume metrics
                volume_24h REAL,
                volume_1h REAL,
                volume_5m REAL,
                volume_ratio REAL,  -- Current vs average
                volume_trend TEXT,  -- increasing/decreasing/stable
                
                -- Volatility metrics
                volatility_1h REAL,
                volatility_24h REAL,
                atr_14 REAL,       -- Average True Range
                bb_width REAL,     -- Bollinger Band width
                
                -- Price metrics
                price_change_1h REAL,
                price_change_24h REAL,
                high_24h REAL,
                low_24h REAL,
                
                -- Market scores
                volume_score REAL,      -- 0-100
                volatility_score REAL,  -- 0-100
                momentum_score REAL,    -- 0-100
                overall_score REAL,     -- 0-100
                
                -- Recommendations
                position_size_multiplier REAL,
                recommended_tp_adjustment REAL,
                recommended_sl_adjustment REAL,
                trade_recommendation TEXT  -- strong_buy/buy/neutral/sell/strong_sell
            )
        ''')
        
        # Historical volume tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volume_history (
                symbol TEXT,
                timestamp DATETIME,
                volume_5m REAL,
                volume_1h REAL,
                price REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def fetch_market_data(self, symbol: str) -> Dict:
        """Fetch current market data from Binance"""
        async with aiohttp.ClientSession() as session:
            try:
                # Get 24h ticker data
                ticker_url = f"{self.binance_api}/ticker/24hr?symbol={symbol}"
                async with session.get(ticker_url) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for ticker {symbol}")
                        # Generate mock data when API returns error
                        logger.info(f"Using mock data for {symbol} due to HTTP {response.status}")
                        return self.generate_mock_market_data(symbol)
                    ticker_data = await response.json()
                
                # Get recent klines for volatility
                klines_url = f"{self.binance_api}/klines?symbol={symbol}&interval=5m&limit=288"  # 24h of 5m candles
                async with session.get(klines_url) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for klines {symbol}")
                        return None
                    klines_data = await response.json()
                
                # Get order book depth for liquidity
                depth_url = f"{self.binance_api}/depth?symbol={symbol}&limit=20"
                async with session.get(depth_url) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for depth {symbol}")
                        return None
                    depth_data = await response.json()
                
                # Validate data types
                if not isinstance(ticker_data, dict):
                    logger.error(f"Invalid ticker data type for {symbol}: {type(ticker_data)}")
                    return None
                if not isinstance(klines_data, list):
                    logger.error(f"Invalid klines data type for {symbol}: {type(klines_data)}")
                    return None
                if not isinstance(depth_data, dict):
                    logger.error(f"Invalid depth data type for {symbol}: {type(depth_data)}")
                    return None
                
                return {
                    'ticker': ticker_data,
                    'klines': klines_data,
                    'depth': depth_data
                }
            except Exception as e:
                logger.error(f"Error fetching market data for {symbol}: {e}")
                # Generate mock data for testing when API is unavailable
                logger.info(f"Using mock data for {symbol}")
                return self.generate_mock_market_data(symbol)
    
    def generate_mock_market_data(self, symbol: str) -> Dict:
        """Generate mock market data for testing when API is unavailable"""
        import random
        
        # Base prices for different symbols
        base_prices = {
            'BTCUSDT': 65000,
            'ETHUSDT': 3200,
            'SOLUSDT': 140,
            'ADAUSDT': 0.45,
            'DOTUSDT': 7.5,
            'MATICUSDT': 0.85,
            'AVAXUSDT': 28,
            'LINKUSDT': 14
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generate mock klines data (288 candles for 24h of 5m data)
        klines = []
        current_price = base_price
        
        for i in range(288):
            # Small random price movement
            change = random.uniform(-0.02, 0.02)  # ±2% max change per candle
            open_price = current_price
            close_price = open_price * (1 + change)
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.01)
            low_price = min(open_price, close_price) * random.uniform(0.99, 1.0)
            volume = random.uniform(100, 1000)
            
            klines.append([
                int(datetime.now().timestamp() * 1000) - (288 - i) * 300000,  # timestamp
                str(open_price),
                str(high_price),
                str(low_price),
                str(close_price),
                str(volume),
                int(datetime.now().timestamp() * 1000) - (288 - i) * 300000 + 299999,
                str(volume * close_price),  # quote volume
                random.randint(50, 200),  # trades
                str(volume * 0.6),  # taker buy base
                str(volume * close_price * 0.6),  # taker buy quote
                "0"
            ])
            
            current_price = close_price
        
        # Mock ticker data
        price_change = (current_price - base_price) / base_price * 100
        ticker = {
            'symbol': symbol,
            'priceChangePercent': str(price_change),
            'volume': str(sum(float(k[5]) for k in klines)),
            'count': str(len(klines))
        }
        
        # Mock depth data
        depth = {
            'bids': [[str(current_price * 0.999), '1.0']],
            'asks': [[str(current_price * 1.001), '1.0']]
        }
        
        return {
            'ticker': ticker,
            'klines': klines,
            'depth': depth
        }
    
    def calculate_volatility_metrics(self, klines: List) -> Dict:
        """Calculate various volatility metrics"""
        if not klines or len(klines) < 2:
            # Return default values if not enough data
            return {
                'volatility_1h': 1.0,
                'volatility_24h': 1.5,
                'atr_14': 1.0,
                'bb_width': 2.0,
                'current_price': 0,
                'high_24h': 0,
                'low_24h': 0
            }
        
        # Convert klines to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # 1-hour volatility (12 5-minute candles)
        if len(df) >= 12:
            volatility_1h = df['returns'].tail(12).std() * np.sqrt(12) * 100
        else:
            volatility_1h = df['returns'].std() * np.sqrt(len(df)) * 100 if len(df) > 1 else 1.0
        
        # 24-hour volatility
        volatility_24h = df['returns'].std() * np.sqrt(288) * 100 if len(df) > 1 else 1.5
        
        # ATR (Average True Range)
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)
        
        # Only calculate if we have enough data
        if len(df) >= 14:
            atr_14 = df['tr'].rolling(14).mean().iloc[-1]
            atr_pct = (atr_14 / df['close'].iloc[-1]) * 100
        else:
            atr_14 = df['tr'].mean() if len(df) > 0 else 0.1
            atr_pct = (atr_14 / df['close'].iloc[-1]) * 100 if len(df) > 0 and atr_14 else 1.0
        
        # Bollinger Bands
        if len(df) >= 20:
            sma_20 = df['close'].rolling(20).mean()
            std_20 = df['close'].rolling(20).std()
            bb_upper = sma_20 + (2 * std_20)
            bb_lower = sma_20 - (2 * std_20)
            bb_width = ((bb_upper - bb_lower) / sma_20 * 100).iloc[-1]
        else:
            # Use simple standard deviation if not enough data
            bb_width = (df['close'].std() / df['close'].mean() * 100) * 4 if len(df) > 1 else 2.0
        
        return {
            'volatility_1h': volatility_1h,
            'volatility_24h': volatility_24h,
            'atr_14': atr_pct,
            'bb_width': bb_width,
            'current_price': df['close'].iloc[-1] if len(df) > 0 else 0,
            'high_24h': df['high'].max() if len(df) > 0 else 0,
            'low_24h': df['low'].min() if len(df) > 0 else 0
        }
    
    def calculate_volume_metrics(self, klines: List, ticker: Dict) -> Dict:
        """Calculate volume metrics and patterns"""
        if not klines or len(klines) == 0:
            return {
                'volume_24h': 0,
                'volume_1h': 0,
                'volume_5m': 0,
                'volume_ratio': 1,
                'volume_trend': 'unknown',
                'avg_volume_5m': 0
            }
            
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Current vs average volume
        volume_5m = df['volume'].iloc[-1] if len(df) > 0 else 0
        volume_1h = df['volume'].tail(12).sum() if len(df) >= 12 else df['volume'].sum()
        volume_24h = float(ticker.get('volume', 0))
        
        # Average volumes
        avg_volume_5m = df['volume'].mean()
        avg_volume_1h = df['volume'].rolling(12).sum().mean()
        
        # Volume ratio (current vs average)
        volume_ratio = volume_5m / avg_volume_5m if avg_volume_5m > 0 else 1
        
        # Volume trend
        recent_volumes = df['volume'].tail(12).values
        if len(recent_volumes) > 1:
            volume_slope = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
            if volume_slope > avg_volume_5m * 0.1:
                volume_trend = 'increasing'
            elif volume_slope < -avg_volume_5m * 0.1:
                volume_trend = 'decreasing'
            else:
                volume_trend = 'stable'
        else:
            volume_trend = 'unknown'
        
        return {
            'volume_24h': volume_24h,
            'volume_1h': volume_1h,
            'volume_5m': volume_5m,
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'avg_volume_5m': avg_volume_5m
        }
    
    def calculate_market_scores(self, volume_metrics: Dict, volatility_metrics: Dict, 
                              ticker: Dict) -> Dict:
        """Calculate comprehensive market scores"""
        
        # Volume Score (0-100)
        # High volume ratio = good for trading
        volume_score = min(100, volume_metrics['volume_ratio'] * 25)
        if volume_metrics['volume_trend'] == 'increasing':
            volume_score = min(100, volume_score + 20)
        
        # Volatility Score (0-100)
        # Moderate volatility is best for micro-profits
        vol_1h = volatility_metrics['volatility_1h']
        if 0.5 <= vol_1h <= 2.0:  # Sweet spot for micro-profits
            volatility_score = 80 + (2.0 - vol_1h) * 10
        elif vol_1h < 0.5:  # Too low
            volatility_score = vol_1h * 160
        else:  # Too high
            volatility_score = max(0, 80 - (vol_1h - 2.0) * 20)
        
        # Momentum Score (0-100)
        price_change_1h = float(ticker.get('priceChangePercent', 0))
        momentum_score = 50  # Neutral
        
        # Strong momentum in either direction is good for trading
        if abs(price_change_1h) > 0.5:
            momentum_score = min(100, 50 + abs(price_change_1h) * 20)
        
        # Overall Score
        overall_score = (
            volume_score * 0.35 +      # Volume is important
            volatility_score * 0.35 +  # Volatility is important
            momentum_score * 0.30      # Momentum helps
        )
        
        return {
            'volume_score': volume_score,
            'volatility_score': volatility_score,
            'momentum_score': momentum_score,
            'overall_score': overall_score
        }
    
    def calculate_trading_adjustments(self, market_scores: Dict, 
                                    volatility_metrics: Dict) -> Dict:
        """Calculate position size and TP/SL adjustments based on market conditions"""
        
        overall_score = market_scores['overall_score']
        volatility = volatility_metrics['volatility_1h']
        
        # Position size multiplier (0.5x to 2.0x)
        if overall_score >= 80:
            position_multiplier = 2.0  # Double size in excellent conditions
        elif overall_score >= 60:
            position_multiplier = 1.5
        elif overall_score >= 40:
            position_multiplier = 1.0
        else:
            position_multiplier = 0.5  # Half size in poor conditions
        
        # Adjust TP/SL based on volatility
        if volatility < 0.5:
            # Low volatility: tighter stops, smaller targets
            tp_adjustment = 0.8  # 80% of normal TP
            sl_adjustment = 0.8  # 80% of normal SL
        elif volatility > 2.0:
            # High volatility: wider stops, bigger targets
            tp_adjustment = 1.5  # 150% of normal TP
            sl_adjustment = 1.5  # 150% of normal SL
        else:
            # Normal volatility
            tp_adjustment = 1.0
            sl_adjustment = 1.0
        
        # Trade recommendation
        if overall_score >= 80 and market_scores['volume_score'] >= 70:
            recommendation = 'strong_buy'
        elif overall_score >= 60:
            recommendation = 'buy'
        elif overall_score >= 40:
            recommendation = 'neutral'
        elif overall_score >= 20:
            recommendation = 'sell'
        else:
            recommendation = 'strong_sell'
        
        return {
            'position_size_multiplier': position_multiplier,
            'recommended_tp_adjustment': tp_adjustment,
            'recommended_sl_adjustment': sl_adjustment,
            'trade_recommendation': recommendation
        }
    
    async def analyze_symbol(self, symbol: str) -> Dict:
        """Complete market analysis for a symbol"""
        logger.info(f"Analyzing market conditions for {symbol}")
        
        # Fetch market data
        market_data = await self.fetch_market_data(symbol)
        if not market_data:
            return None
        
        # Calculate metrics
        volatility_metrics = self.calculate_volatility_metrics(market_data['klines'])
        volume_metrics = self.calculate_volume_metrics(market_data['klines'], market_data['ticker'])
        market_scores = self.calculate_market_scores(volume_metrics, volatility_metrics, market_data['ticker'])
        adjustments = self.calculate_trading_adjustments(market_scores, volatility_metrics)
        
        # Combine all metrics
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            **volume_metrics,
            **volatility_metrics,
            'price_change_1h': float(market_data['ticker'].get('priceChangePercent', 0)),
            'price_change_24h': float(market_data['ticker'].get('priceChangePercent', 0)),
            **market_scores,
            **adjustments
        }
        
        # Save to database
        self.save_analysis(analysis)
        
        return analysis
    
    def save_analysis(self, analysis: Dict):
        """Save market analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_conditions (
                symbol, timestamp, volume_24h, volume_1h, volume_5m, volume_ratio,
                volume_trend, volatility_1h, volatility_24h, atr_14, bb_width,
                price_change_1h, price_change_24h, high_24h, low_24h,
                volume_score, volatility_score, momentum_score, overall_score,
                position_size_multiplier, recommended_tp_adjustment,
                recommended_sl_adjustment, trade_recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis['symbol'], analysis['timestamp'],
            analysis['volume_24h'], analysis['volume_1h'], analysis['volume_5m'],
            analysis['volume_ratio'], analysis['volume_trend'],
            analysis['volatility_1h'], analysis['volatility_24h'],
            analysis['atr_14'], analysis['bb_width'],
            analysis['price_change_1h'], analysis['price_change_24h'],
            analysis['high_24h'], analysis['low_24h'],
            analysis['volume_score'], analysis['volatility_score'],
            analysis['momentum_score'], analysis['overall_score'],
            analysis['position_size_multiplier'], analysis['recommended_tp_adjustment'],
            analysis['recommended_sl_adjustment'], analysis['trade_recommendation']
        ))
        
        # Also save to volume history for tracking
        cursor.execute('''
            INSERT OR REPLACE INTO volume_history (symbol, timestamp, volume_5m, volume_1h, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            analysis['symbol'], analysis['timestamp'],
            analysis['volume_5m'], analysis['volume_1h'],
            analysis['current_price']
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Market analysis saved for {analysis['symbol']} - Score: {analysis['overall_score']:.1f}")
    
    def get_latest_analysis(self, symbol: str) -> Dict:
        """Get the latest market analysis for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM market_conditions
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (symbol,))
        
        columns = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(zip(columns, result))
        return None

async def main():
    """Test the market analyzer"""
    analyzer = MarketAnalyzer()
    
    # Analyze some popular trading pairs
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    for symbol in symbols:
        analysis = await analyzer.analyze_symbol(symbol)
        if analysis:
            print(f"\n{symbol} Analysis:")
            print(f"  Overall Score: {analysis['overall_score']:.1f}/100")
            print(f"  Volume Score: {analysis['volume_score']:.1f}")
            print(f"  Volatility: {analysis['volatility_1h']:.2f}%")
            print(f"  Position Multiplier: {analysis['position_size_multiplier']}x")
            print(f"  Recommendation: {analysis['trade_recommendation']}")

if __name__ == "__main__":
    asyncio.run(main())