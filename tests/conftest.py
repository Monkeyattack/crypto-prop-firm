"""
pytest configuration and shared fixtures
"""

import os
import sys
import tempfile
import shutil
import sqlite3
from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager, Trade
from signal_processor import SignalProcessor
from prop_firm_signal_processor import PropFirmSignalProcessor
from telegram_notifier import TelegramNotifier
from trading_engine import TradingEngine


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_trading.db')
    
    yield db_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager with temporary database"""
    return DatabaseManager(temp_db)


@pytest.fixture
def sample_trade():
    """Create a sample trade for testing"""
    return Trade(
        symbol="BTCUSDT",
        side="Buy",
        entry=50000.0,
        tp=52500.0,  # +5%
        sl=47500.0,  # -5%
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def sample_trades():
    """Create multiple sample trades for testing"""
    trades = []
    base_time = datetime.now()
    
    for i in range(5):
        trades.append(Trade(
            symbol=f"TEST{i}USDT",
            side="Buy" if i % 2 == 0 else "Sell",
            entry=1000.0 + i * 100,
            tp=(1000.0 + i * 100) * (1.05 if i % 2 == 0 else 0.95),
            sl=(1000.0 + i * 100) * (0.95 if i % 2 == 0 else 1.05),
            timestamp=(base_time - timedelta(minutes=i*10)).isoformat()
        ))
    
    return trades


@pytest.fixture
def signal_processor(temp_db):
    """Create SignalProcessor with temporary database"""
    with patch('signal_processor.DatabaseManager') as mock_db_class:
        mock_db_class.return_value = DatabaseManager(temp_db)
        return SignalProcessor()


@pytest.fixture
def prop_firm_processor(temp_db):
    """Create PropFirmSignalProcessor with temporary database"""
    return PropFirmSignalProcessor(temp_db)


@pytest.fixture
def mock_telegram_notifier():
    """Create a mock Telegram notifier"""
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': '12345'
    }):
        notifier = TelegramNotifier()
        notifier.send_message = Mock(return_value=True)
        return notifier


@pytest.fixture
def trading_engine(temp_db):
    """Create TradingEngine with temporary database"""
    with patch('trading_engine.TradingEngine.load_settings'):
        engine = TradingEngine()
        engine.db_path = temp_db
        engine.settings = {
            'automated_trading_enabled': 'true',
            'max_open_positions': 5,
            'max_exposure_pct': 50,
            'min_available_equity_pct': 20,
            'symbol_filtering_enabled': 'false',
            'take_profit_strategy': 'scaled',
            'tp_level_1_pct': 5.0,
            'stop_loss_pct': 5.0,
            'trailing_enabled': 'true'
        }
        return engine


@pytest.fixture
def valid_signal_messages():
    """Sample valid signal messages for testing"""
    return [
        """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750""",
        
        """Buy ETHUSDT
Entry Price: 2800
Take Profit: 2940
Stop Loss: 2660""",
        
        """Sell ADAUSDT @ 0.85 | TP: 0.81 | SL: 0.89""",
        
        """SOLUSD Long
Entry: 167.17
Target: 175.53
Stoploss: 158.81"""
    ]


@pytest.fixture
def invalid_signal_messages():
    """Sample invalid signal messages for testing"""
    return [
        "This is not a signal",
        "Buy BTCUSDT without prices",
        "ETHUSDT Entry: abc TP: 2940 SL: 2660",  # Invalid price
        "",  # Empty message
        "Buy INVALID\nEntry: -1000\nTP: 1100\nSL: 900"  # Negative entry
    ]


@pytest.fixture
def mock_binance_websocket():
    """Mock Binance WebSocket connection"""
    mock_ws = Mock()
    mock_session = Mock()
    mock_session.ws_connect.return_value.__aenter__.return_value = mock_ws
    
    # Mock price data
    price_data = [
        {'s': 'BTCUSDT', 'p': '45500'},  # +1.11%
        {'s': 'ETHUSDT', 'p': '2850'},   # +1.79%
        {'s': 'ADAUSDT', 'p': '0.82'},   # -3.53%
    ]
    
    mock_ws.__aiter__.return_value = [
        Mock(type=1, data='{"s": "BTCUSDT", "p": "45500"}'),
        Mock(type=1, data='{"s": "ETHUSDT", "p": "2850"}'),
        Mock(type=1, data='{"s": "ADAUSDT", "p": "0.82"}'),
    ]
    
    return mock_session


@pytest.fixture
def mock_mt5():
    """Mock MT5 terminal for testing"""
    mock_mt5 = Mock()
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.order_send.return_value = Mock(retcode=10009)  # TRADE_RETCODE_DONE
    mock_mt5.positions_get.return_value = []
    mock_mt5.shutdown.return_value = None
    return mock_mt5


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        'TELEGRAM_BOT_TOKEN': 'test_token_12345',
        'TELEGRAM_CHAT_ID': '987654321',
        'MT5_LOGIN': '12345',
        'MT5_PASSWORD': 'test_password',
        'MT5_SERVER': 'test_server',
    }
    
    with patch.dict(os.environ, test_env):
        yield


# Pytest markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.stress = pytest.mark.stress