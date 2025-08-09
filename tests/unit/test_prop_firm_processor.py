"""
Unit tests for PropFirmSignalProcessor
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sqlite3
import tempfile
import os

from prop_firm_signal_processor import PropFirmSignalProcessor


@pytest.mark.unit
class TestPropFirmSignalProcessor:
    """Test PropFirmSignalProcessor functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def processor(self, temp_db_path):
        """Create PropFirmSignalProcessor with temp database"""
        return PropFirmSignalProcessor(temp_db_path)
    
    def test_init(self, processor):
        """Test PropFirmSignalProcessor initialization"""
        assert processor is not None
        assert processor.rules['min_risk_reward'] == 1.5
        assert processor.rules['max_risk_percent'] == 2.0
        assert processor.rules['daily_loss_limit'] == 500.0
        assert processor.rules['max_drawdown'] == 600.0
        assert processor.rules['account_size'] == 10000.0
    
    def test_calculate_risk_reward_ratio_buy(self, processor):
        """Test RR calculation for buy orders"""
        rr = processor.calculate_risk_reward_ratio(100, 110, 95, 'BUY')
        assert rr == 2.0  # Risk: 5, Reward: 10
        
        rr = processor.calculate_risk_reward_ratio(100, 105, 98, 'LONG')
        assert rr == 2.5  # Risk: 2, Reward: 5
    
    def test_calculate_risk_reward_ratio_sell(self, processor):
        """Test RR calculation for sell orders"""
        rr = processor.calculate_risk_reward_ratio(100, 95, 105, 'SELL')
        assert rr == 1.0  # Risk: 5, Reward: 5
        
        rr = processor.calculate_risk_reward_ratio(100, 90, 102, 'SHORT')
        assert rr == 5.0  # Risk: 2, Reward: 10
    
    def test_calculate_risk_reward_ratio_invalid(self, processor):
        """Test RR calculation with invalid inputs"""
        # Zero risk
        rr = processor.calculate_risk_reward_ratio(100, 110, 100, 'BUY')
        assert rr == 0.0
        
        # Negative risk (SL above entry for buy)
        rr = processor.calculate_risk_reward_ratio(100, 110, 105, 'BUY')
        assert rr == 0.0
    
    def test_calculate_position_size_valid(self, processor):
        """Test position size calculation with valid inputs"""
        # 2% risk on $10K account = $200 max risk
        # Entry 100, SL 95 = $5 risk per unit
        # Position size = $200 / $5 = 40 units = $4000
        size = processor.calculate_position_size(100, 95, 2.0)
        assert size == 4000.0  # 40 * 100
        
        # 1% risk
        size = processor.calculate_position_size(100, 95, 1.0)
        assert size == 2000.0  # 20 * 100
    
    def test_calculate_position_size_zero_risk(self, processor):
        """Test position size calculation with zero price risk"""
        size = processor.calculate_position_size(100, 100, 2.0)  # Same entry and SL
        assert size == 0.0
    
    def test_calculate_position_size_max_limit(self, processor):
        """Test position size doesn't exceed account limit"""
        # Very small risk should be capped at 95% of account
        size = processor.calculate_position_size(100, 99.99, 2.0)  # 0.01 risk
        assert size == 9500.0  # 95% of $10K account
    
    def setup_test_database(self, processor):
        """Setup test database with required tables"""
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        
        # Create required tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prop_firm_status (
                id INTEGER PRIMARY KEY,
                is_trading_allowed INTEGER DEFAULT 1,
                current_balance REAL DEFAULT 10000,
                daily_pnl REAL DEFAULT 0,
                daily_trades INTEGER DEFAULT 0,
                daily_loss_limit REAL DEFAULT 500,
                max_drawdown_limit REAL DEFAULT 600,
                profit_target REAL DEFAULT 1000,
                evaluation_passed INTEGER DEFAULT 0,
                evaluation_failed INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                daily_reset_time TEXT DEFAULT CURRENT_TIMESTAMP,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                raw_message TEXT,
                prop_firm_processed INTEGER DEFAULT 0,
                prop_firm_decision TEXT,
                prop_firm_reason TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prop_firm_decisions (
                id INTEGER PRIMARY KEY,
                signal_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                risk_reward_ratio REAL,
                position_size_usd REAL,
                risk_percent REAL,
                decision TEXT,
                reason TEXT,
                daily_loss REAL,
                daily_loss_limit REAL,
                current_drawdown REAL,
                max_drawdown_limit REAL,
                daily_trades_count INTEGER,
                alert_message TEXT
            )
        """)
        
        # Insert initial status
        cursor.execute("""
            INSERT OR REPLACE INTO prop_firm_status (id, current_balance)
            VALUES (1, 10000)
        """)
        
        conn.commit()
        conn.close()
    
    def test_get_current_status_initial(self, processor):
        """Test getting current status when first initialized"""
        self.setup_test_database(processor)
        
        status = processor.get_current_status()
        
        assert status['is_trading_allowed'] is True
        assert status['current_balance'] == 10000.0
        assert status['daily_pnl'] == 0.0
        assert status['daily_trades'] == 0
    
    def test_evaluate_signal_valid_acceptance(self, processor):
        """Test signal evaluation that should be accepted"""
        self.setup_test_database(processor)
        
        # Create valid signal tuple
        signal = (
            1,                              # id
            datetime.now().isoformat(),     # timestamp
            'BTCUSDT',                      # symbol
            'BUY',                          # side
            45000.0,                        # entry
            47250.0,                        # tp
            42750.0,                        # sl
            'Test signal'                   # raw_message
        )
        
        decision = processor.evaluate_signal(signal)
        
        assert decision['decision'] == 'ACCEPTED'
        assert decision['symbol'] == 'BTCUSDT'
        assert decision['side'] == 'BUY'
        assert decision['risk_reward_ratio'] == 2.0  # (47250-45000)/(45000-42750)
        assert decision['position_size_usd'] > 0
        assert 'Trade approved' in decision['reason']
    
    def test_evaluate_signal_low_rr_rejection(self, processor):
        """Test signal evaluation rejected for low RR ratio"""
        self.setup_test_database(processor)
        
        # Create signal with low RR ratio
        signal = (
            1,
            datetime.now().isoformat(),
            'BTCUSDT',
            'BUY',
            45000.0,
            45500.0,  # Low TP for poor RR
            42750.0,
            'Test signal'
        )
        
        decision = processor.evaluate_signal(signal)
        
        assert decision['decision'] == 'REJECTED'
        assert 'R:R ratio' in decision['reason']
        assert 'below minimum' in decision['reason']
    
    def test_evaluate_signal_invalid_prices(self, processor):
        """Test signal evaluation with invalid prices"""
        self.setup_test_database(processor)
        
        # Create signal with zero prices
        signal = (
            1,
            datetime.now().isoformat(),
            'BTCUSDT',
            'BUY',
            0,      # Invalid entry
            47250.0,
            42750.0,
            'Test signal'
        )
        
        decision = processor.evaluate_signal(signal)
        
        assert decision['decision'] == 'REJECTED'
        assert 'Invalid signal data' in decision['reason']
    
    def test_evaluate_signal_trading_suspended(self, processor):
        """Test signal evaluation when trading is suspended"""
        self.setup_test_database(processor)
        
        # Disable trading
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE prop_firm_status 
            SET is_trading_allowed = 0
            WHERE id = 1
        """)
        conn.commit()
        conn.close()
        
        signal = (
            1,
            datetime.now().isoformat(),
            'BTCUSDT',
            'BUY',
            45000.0,
            47250.0,
            42750.0,
            'Test signal'
        )
        
        decision = processor.evaluate_signal(signal)
        
        assert decision['decision'] == 'REJECTED'
        assert 'Trading suspended' in decision['reason']
    
    def test_create_telegram_message(self, processor):
        """Test Telegram message creation"""
        decision = {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'entry_price': 45000.0,
            'take_profit': 47250.0,
            'stop_loss': 42750.0,
            'risk_reward_ratio': 2.0,
            'position_size_usd': 4000.0,
            'risk_percent': 2.0
        }
        
        message = processor.create_telegram_message(decision)
        
        assert 'PROP FIRM TRADE ALERT' in message
        assert 'BTCUSDT' in message
        assert 'BUY' in message
        assert '$45000.0000' in message
        assert 'R:R Ratio: 2.00' in message
        assert '$4000.00' in message
        assert 'MANUAL EXECUTION REQUIRED' in message
    
    def test_process_new_signals(self, processor):
        """Test processing new signals from database"""
        self.setup_test_database(processor)
        
        # Insert test signals
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        
        signals_data = [
            (datetime.now().isoformat(), 'BTCUSDT', 'BUY', 45000, 47250, 42750, 'Signal 1'),
            (datetime.now().isoformat(), 'ETHUSDT', 'BUY', 2800, 2850, 2750, 'Signal 2'),
        ]
        
        for signal_data in signals_data:
            cursor.execute("""
                INSERT INTO signal_log (timestamp, symbol, side, entry_price, take_profit, stop_loss, raw_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, signal_data)
        
        conn.commit()
        conn.close()
        
        # Process signals
        decisions = processor.process_new_signals()
        
        assert len(decisions) == 2
        assert decisions[0]['symbol'] == 'BTCUSDT'
        assert decisions[1]['symbol'] == 'ETHUSDT'
        
        # Check signals are marked as processed
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prop_firm_processed FROM signal_log")
        processed_flags = [row[0] for row in cursor.fetchall()]
        assert all(flag == 1 for flag in processed_flags)
        conn.close()
    
    def test_get_daily_stats_empty(self, processor):
        """Test daily stats with no decisions"""
        self.setup_test_database(processor)
        
        stats = processor.get_daily_stats()
        
        assert stats['total_signals'] == 0
        assert stats['accepted'] == 0
        assert stats['rejected'] == 0
        assert stats['acceptance_rate'] == 0
    
    def test_get_daily_stats_with_decisions(self, processor):
        """Test daily stats with some decisions"""
        self.setup_test_database(processor)
        
        # Insert test decisions for today
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        decisions_data = [
            (today, 'BTCUSDT', 'BUY', 'ACCEPTED', 'Good trade', 2.0),
            (today, 'ETHUSDT', 'BUY', 'REJECTED', 'Low RR', 1.0),
            (today, 'ADAUSDT', 'SELL', 'ACCEPTED', 'Good trade', 3.0),
        ]
        
        for decision_data in decisions_data:
            cursor.execute("""
                INSERT INTO prop_firm_decisions (timestamp, symbol, side, decision, reason, risk_reward_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, decision_data)
        
        conn.commit()
        conn.close()
        
        stats = processor.get_daily_stats()
        
        assert stats['total_signals'] == 3
        assert stats['accepted'] == 2
        assert stats['rejected'] == 1
        assert stats['acceptance_rate'] == pytest.approx(66.67, rel=0.01)
        assert stats['avg_rr_accepted'] == 2.5  # (2.0 + 3.0) / 2
    
    def test_perform_daily_reset(self, processor):
        """Test daily reset functionality"""
        self.setup_test_database(processor)
        
        # Set some daily values
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE prop_firm_status 
            SET daily_pnl = -100.0,
                daily_trades = 5
            WHERE id = 1
        """)
        conn.commit()
        conn.close()
        
        # Perform reset
        processor.perform_daily_reset()
        
        # Check values are reset
        status = processor.get_current_status()
        assert status['daily_pnl'] == 0.0
        assert status['daily_trades'] == 0
    
    def test_log_decision(self, processor):
        """Test decision logging to database"""
        self.setup_test_database(processor)
        
        decision = {
            'signal_id': 1,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'entry_price': 45000.0,
            'take_profit': 47250.0,
            'stop_loss': 42750.0,
            'risk_reward_ratio': 2.0,
            'position_size_usd': 4000.0,
            'risk_percent': 2.0,
            'decision': 'ACCEPTED',
            'reason': 'Good trade'
        }
        
        result = processor.log_decision(decision)
        
        # Check decision was logged
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prop_firm_decisions WHERE signal_id = 1")
        logged_decision = cursor.fetchone()
        conn.close()
        
        assert logged_decision is not None
        assert logged_decision[3] == 'BTCUSDT'  # symbol
        assert logged_decision[11] == 'ACCEPTED'  # decision
    
    def test_get_recent_decisions(self, processor):
        """Test getting recent decisions"""
        self.setup_test_database(processor)
        
        # Insert some decisions
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        
        decisions_data = [
            ('BTCUSDT', 'BUY', 'ACCEPTED', 'Good trade', 2.0, 4000.0, 'Alert sent'),
            ('ETHUSDT', 'SELL', 'REJECTED', 'Low RR', 1.0, 0.0, ''),
        ]
        
        for decision_data in decisions_data:
            cursor.execute("""
                INSERT INTO prop_firm_decisions 
                (symbol, side, decision, reason, risk_reward_ratio, position_size_usd, alert_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, decision_data)
        
        conn.commit()
        conn.close()
        
        decisions = processor.get_recent_decisions(limit=10)
        
        assert len(decisions) == 2
        assert decisions[0]['symbol'] == 'ETHUSDT'  # Most recent first
        assert decisions[0]['decision'] == 'REJECTED'
        assert decisions[1]['symbol'] == 'BTCUSDT'
        assert decisions[1]['has_alert'] is True  # Has alert message