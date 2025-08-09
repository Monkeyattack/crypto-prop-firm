"""
Unit tests for TradingEngine
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sqlite3
import tempfile
import os
from datetime import datetime

from trading_engine import TradingEngine


@pytest.mark.unit
class TestTradingEngine:
    """Test TradingEngine functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        # Initialize database with required tables
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE trading_settings (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                side TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                result TEXT DEFAULT 'open',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                position_size REAL DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE capital_history (
                id INTEGER PRIMARY KEY,
                value REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert initial capital
        cursor.execute("INSERT INTO capital_history (value) VALUES (10000)")
        
        # Insert default settings
        default_settings = [
            ('automated_trading_enabled', 'true'),
            ('max_position_size', '100'),
            ('max_daily_trades', '8'),
            ('max_open_positions', '5'),
            ('stop_loss_pct', '5.0'),
            ('symbol_filtering_enabled', 'false'),
            ('take_profit_strategy', 'scaled'),
            ('tp_level_1_pct', '5.0'),
            ('trailing_enabled', 'true'),
            ('max_exposure_pct', '50'),
            ('min_available_equity_pct', '20')
        ]
        
        cursor.executemany(
            "INSERT INTO trading_settings (key, value) VALUES (?, ?)",
            default_settings
        )
        
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def trading_engine(self, temp_db_path):
        """Create TradingEngine with temporary database"""
        with patch('trading_engine.TrailingTakeProfitManager'), \
             patch('trading_engine.MarketAnalyzer'), \
             patch('trading_engine.position_sizer'):
            
            engine = TradingEngine()
            engine.db_path = temp_db_path
            engine.load_settings()  # Reload with temp DB
            return engine
    
    def test_init(self, trading_engine):
        """Test TradingEngine initialization"""
        assert trading_engine is not None
        assert trading_engine.db_path is not None
        assert hasattr(trading_engine, 'trailing_manager')
        assert hasattr(trading_engine, 'market_analyzer')
        assert hasattr(trading_engine, 'settings')
    
    def test_load_settings(self, trading_engine):
        """Test loading settings from database"""
        trading_engine.load_settings()
        
        assert trading_engine.settings['max_position_size'] == 100
        assert trading_engine.settings['max_daily_trades'] == 8
        assert trading_engine.settings['stop_loss_pct'] == 5.0
        assert trading_engine.settings['automated_trading_enabled'] == 'true'
    
    def test_load_settings_database_error(self, trading_engine):
        """Test loading settings with database error"""
        # Use non-existent database path
        trading_engine.db_path = '/nonexistent/path.db'
        trading_engine.load_settings()
        
        # Should use default settings
        assert 'max_position_size' in trading_engine.settings
        assert trading_engine.settings['max_position_size'] == 100
    
    def test_check_risk_limits_allowed(self, trading_engine):
        """Test risk limits check when trading is allowed"""
        # No open positions, good capital
        risk_check = trading_engine.check_risk_limits()
        
        assert risk_check['can_trade'] is True
        assert risk_check['current_capital'] == 10000.0
        assert risk_check['current_exposure'] == 0.0
        assert risk_check['exposure_pct'] == 0.0
        assert risk_check['open_positions'] == 0
    
    def test_check_risk_limits_max_exposure(self, trading_engine):
        """Test risk limits check with max exposure exceeded"""
        # Add trades to simulate high exposure
        conn = sqlite3.connect(trading_engine.db_path)
        cursor = conn.cursor()
        
        # Add trades with high position sizes
        for i in range(3):
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry, tp, sl, result)
                VALUES (?, 'Buy', 1000, 1100, 900, 'open')
            ''', (f'TEST{i}USDT',))
        
        conn.commit()
        conn.close()
        
        risk_check = trading_engine.check_risk_limits()
        
        assert risk_check['can_trade'] is False
        assert 'Exposure:' in risk_check['reason']
    
    def test_check_risk_limits_max_positions(self, trading_engine):
        """Test risk limits check with max positions exceeded"""
        # Set low max positions
        trading_engine.settings['max_open_positions'] = 2
        
        # Add max positions
        conn = sqlite3.connect(trading_engine.db_path)
        cursor = conn.cursor()
        
        for i in range(3):  # More than max
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry, tp, sl, result)
                VALUES (?, 'Buy', 1000, 1100, 900, 'open')
            ''', (f'TEST{i}USDT',))
        
        conn.commit()
        conn.close()
        
        risk_check = trading_engine.check_risk_limits()
        
        assert risk_check['can_trade'] is False
    
    def test_check_symbol_filter_disabled(self, trading_engine):
        """Test symbol filter when disabled"""
        trading_engine.settings['symbol_filtering_enabled'] = 'false'
        
        result = trading_engine.check_symbol_filter('ANYSYMBOL')
        assert result is True
    
    def test_check_symbol_filter_blacklisted(self, trading_engine):
        """Test symbol filter with blacklisted symbol"""
        trading_engine.settings['symbol_filtering_enabled'] = 'true'
        trading_engine.settings['blacklisted_symbols'] = 'DOGECOIN, SHIB, SAFEMOON'
        
        result = trading_engine.check_symbol_filter('DOGECOIN')
        assert result is False
        
        result = trading_engine.check_symbol_filter('BTCUSDT')
        assert result is True
    
    def test_check_symbol_filter_case_insensitive(self, trading_engine):
        """Test symbol filter is case insensitive"""
        trading_engine.settings['symbol_filtering_enabled'] = 'true'
        trading_engine.settings['blacklisted_symbols'] = 'dogecoin'
        
        result = trading_engine.check_symbol_filter('DOGECOIN')
        assert result is False
        
        result = trading_engine.check_symbol_filter('DoGeCoin')
        assert result is False
    
    @patch('trading_engine.position_sizer')
    def test_process_signal_success(self, mock_position_sizer, trading_engine):
        """Test successful signal processing"""
        # Mock position sizer
        mock_position_sizer.calculate_position_size.return_value = (1000.0, {
            'actual_risk_usd': 50.0,
            'actual_risk_pct': 0.5
        })
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        
        assert result is not None
        assert result['success'] is True
        assert result['symbol'] == 'BTCUSDT'
        assert result['side'] == 'Buy'
        assert result['entry_price'] == 50000.0
        assert result['position_size'] == 1000.0
        
        # Verify trade was added to database
        conn = sqlite3.connect(trading_engine.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades WHERE result = 'open'")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_process_signal_trading_disabled(self, trading_engine):
        """Test signal processing when automated trading is disabled"""
        trading_engine.settings['automated_trading_enabled'] = 'false'
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        assert result is None
    
    def test_process_signal_risk_limits_exceeded(self, trading_engine):
        """Test signal processing when risk limits are exceeded"""
        # Add many open positions to exceed limits
        conn = sqlite3.connect(trading_engine.db_path)
        cursor = conn.cursor()
        
        for i in range(10):  # Exceed max open positions
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry, tp, sl, result)
                VALUES (?, 'Buy', 1000, 1100, 900, 'open')
            ''', (f'TEST{i}USDT',))
        
        conn.commit()
        conn.close()
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        assert result is None
    
    def test_process_signal_symbol_blacklisted(self, trading_engine):
        """Test signal processing with blacklisted symbol"""
        trading_engine.settings['symbol_filtering_enabled'] = 'true'
        trading_engine.settings['blacklisted_symbols'] = 'SCAMCOIN'
        
        signal = {
            'symbol': 'SCAMCOIN',
            'side': 'Buy',
            'entry_price': 1.0
        }
        
        result = trading_engine.process_signal(signal)
        assert result is None
    
    def test_process_signal_missing_fields(self, trading_engine):
        """Test signal processing with missing required fields"""
        signal = {
            'symbol': 'BTCUSDT',
            # Missing 'side' and 'entry_price'
        }
        
        result = trading_engine.process_signal(signal)
        assert result is None
    
    @patch('trading_engine.position_sizer')
    def test_process_signal_zero_position_size(self, mock_position_sizer, trading_engine):
        """Test signal processing when position size calculation fails"""
        # Mock position sizer to return zero size
        mock_position_sizer.calculate_position_size.return_value = (0.0, {
            'error': 'Insufficient capital'
        })
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        
        assert result is not None
        assert result['success'] is False
        assert 'Insufficient capital' in result['reason']
    
    @patch('trading_engine.asyncio')
    @patch('trading_engine.position_sizer')
    def test_process_signal_with_market_analysis(self, mock_position_sizer, mock_asyncio, trading_engine):
        """Test signal processing with market analysis"""
        # Mock position sizer
        mock_position_sizer.calculate_position_size.return_value = (1000.0, {
            'actual_risk_usd': 50.0,
            'actual_risk_pct': 0.5
        })
        
        # Mock market analysis
        mock_loop = Mock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        mock_analysis = {
            'trade_recommendation': 'buy',
            'overall_score': 7.5,
            'volatility_1h': 2.3,
            'volume_ratio': 1.2,
            'recommended_tp_adjustment': 1.1,
            'recommended_sl_adjustment': 0.9
        }
        mock_loop.run_until_complete.return_value = mock_analysis
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        
        assert result is not None
        assert result['success'] is True
        
        # Verify TP/SL were adjusted based on market analysis
        # TP: 5% * 1.1 = 5.5%, SL: 5% * 0.9 = 4.5%
        expected_tp = 50000 * 1.055  # +5.5%
        expected_sl = 50000 * 0.955  # -4.5%
        
        assert result['tp'] == pytest.approx(expected_tp, rel=0.01)
        assert result['sl'] == pytest.approx(expected_sl, rel=0.01)
    
    @patch('trading_engine.asyncio')
    @patch('trading_engine.position_sizer')
    def test_process_signal_poor_market_conditions(self, mock_position_sizer, mock_asyncio, trading_engine):
        """Test signal processing with poor market conditions"""
        # Mock market analysis with poor conditions
        mock_loop = Mock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        mock_analysis = {
            'trade_recommendation': 'strong_sell',
            'overall_score': 2.1
        }
        mock_loop.run_until_complete.return_value = mock_analysis
        
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry_price': 50000.0
        }
        
        result = trading_engine.process_signal(signal)
        
        assert result is not None
        assert result['success'] is False
        assert 'Poor market conditions' in result['reason']
    
    def test_process_signal_buy_price_calculation(self, trading_engine):
        """Test TP/SL price calculation for buy orders"""
        with patch('trading_engine.position_sizer') as mock_position_sizer:
            mock_position_sizer.calculate_position_size.return_value = (1000.0, {})
            
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'entry_price': 50000.0
            }
            
            result = trading_engine.process_signal(signal)
            
            # For buy: TP above entry, SL below entry
            # 5% TP = 50000 * 1.05 = 52500
            # 5% SL = 50000 * 0.95 = 47500
            assert result['tp'] == 52500.0
            assert result['sl'] == 47500.0
    
    def test_process_signal_sell_price_calculation(self, trading_engine):
        """Test TP/SL price calculation for sell orders"""
        with patch('trading_engine.position_sizer') as mock_position_sizer:
            mock_position_sizer.calculate_position_size.return_value = (1000.0, {})
            
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'SELL',
                'entry_price': 50000.0
            }
            
            result = trading_engine.process_signal(signal)
            
            # For sell: TP below entry, SL above entry
            # 5% TP = 50000 * 0.95 = 47500
            # 5% SL = 50000 * 1.05 = 52500
            assert result['tp'] == 47500.0
            assert result['sl'] == 52500.0
    
    def test_process_signal_trailing_strategy(self, trading_engine):
        """Test signal processing with trailing strategy"""
        trading_engine.settings['take_profit_strategy'] = 'trailing'
        trading_engine.settings['tp_level_1_pct'] = 0.75  # Different value for trailing
        
        with patch('trading_engine.position_sizer') as mock_position_sizer:
            mock_position_sizer.calculate_position_size.return_value = (1000.0, {})
            
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'entry_price': 50000.0
            }
            
            result = trading_engine.process_signal(signal)
            
            assert result['strategy'] == 'trailing'
            # Should use 0.75% instead of default 5%
            expected_tp = 50000 * 1.0075
            assert result['tp'] == expected_tp
    
    def test_process_signal_trailing_manager_integration(self, trading_engine):
        """Test that trailing manager is called when enabled"""
        with patch('trading_engine.position_sizer') as mock_position_sizer:
            mock_position_sizer.calculate_position_size.return_value = (1000.0, {})
            
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'entry_price': 50000.0
            }
            
            result = trading_engine.process_signal(signal)
            
            # Verify trailing manager was called
            trading_engine.trailing_manager.track_position.assert_called_once()
            call_args = trading_engine.trailing_manager.track_position.call_args[0]
            assert call_args[1] == 'BTCUSDT'  # symbol
            assert call_args[2] == 'Buy'      # side
            assert call_args[3] == 50000.0    # entry_price
    
    def test_process_signal_trailing_disabled(self, trading_engine):
        """Test signal processing with trailing disabled"""
        trading_engine.settings['trailing_enabled'] = 'false'
        
        with patch('trading_engine.position_sizer') as mock_position_sizer:
            mock_position_sizer.calculate_position_size.return_value = (1000.0, {})
            
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'Buy', 
                'entry_price': 50000.0
            }
            
            result = trading_engine.process_signal(signal)
            
            # Verify trailing manager was NOT called
            trading_engine.trailing_manager.track_position.assert_not_called()
    
    def test_update_positions(self, trading_engine):
        """Test update_positions method (placeholder)"""
        # This is currently a placeholder method
        trading_engine.update_positions()
        # Should not raise any exceptions