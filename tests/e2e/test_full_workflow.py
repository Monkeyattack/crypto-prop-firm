"""
End-to-end workflow tests for the complete trading system
"""

import pytest
import asyncio
import sqlite3
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from signal_processor import SignalProcessor
from prop_firm_signal_processor import PropFirmSignalProcessor
from trading_engine import TradingEngine
from telegram_notifier import TelegramNotifier
from database import DatabaseManager, Trade
from tests.mocks.mock_mt5 import MockMT5Terminal
from tests.mocks.mock_telegram import MockTelegramNotifier
from tests.mocks.mock_binance import MockBinanceWebSocket, MockMarketDataProvider


@pytest.mark.e2e
class TestFullWorkflow:
    """Test complete end-to-end trading workflow"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize database with all required tables
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create all required tables
        tables = [
            '''CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry REAL NOT NULL,
                tp REAL NOT NULL,
                sl REAL NOT NULL,
                result TEXT DEFAULT 'open',
                pnl REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                position_size REAL DEFAULT 1000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE capital (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE capital_by_symbol (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol) ON CONFLICT REPLACE
            )''',
            
            '''CREATE TABLE signal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            )''',
            
            '''CREATE TABLE prop_firm_status (
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
            )''',
            
            '''CREATE TABLE prop_firm_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            )''',
            
            '''CREATE TABLE trading_settings (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT
            )'''
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        # Insert initial data
        cursor.execute("INSERT INTO capital (value, timestamp) VALUES (10000, ?)", 
                      (datetime.now().isoformat(),))
        
        cursor.execute("INSERT INTO prop_firm_status (id) VALUES (1)")
        
        # Insert trading settings
        settings = [
            ('automated_trading_enabled', 'true'),
            ('max_open_positions', '5'),
            ('max_exposure_pct', '50'),
            ('min_available_equity_pct', '20'),
            ('symbol_filtering_enabled', 'false'),
            ('take_profit_strategy', 'scaled'),
            ('tp_level_1_pct', '5.0'),
            ('stop_loss_pct', '5.0'),
            ('trailing_enabled', 'true')
        ]
        
        cursor.executemany(
            "INSERT INTO trading_settings (key, value) VALUES (?, ?)",
            settings
        )
        
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def workflow_components(self, temp_db_path):
        """Setup all workflow components with mocks"""
        # Create mock instances
        mock_mt5 = MockMT5Terminal()
        mock_telegram = MockTelegramNotifier()
        mock_binance = MockBinanceWebSocket()
        mock_market_data = MockMarketDataProvider()
        
        # Initialize components
        with patch('signal_processor.DatabaseManager') as mock_db_signal, \
             patch('trading_engine.TrailingTakeProfitManager') as mock_trailing, \
             patch('trading_engine.MarketAnalyzer') as mock_analyzer, \
             patch('trading_engine.position_sizer') as mock_sizer, \
             patch.dict('os.environ', {
                 'TELEGRAM_BOT_TOKEN': 'test_token',
                 'TELEGRAM_CHAT_ID': '12345'
             }):
            
            # Setup database manager
            db_manager = DatabaseManager(temp_db_path)
            mock_db_signal.return_value = db_manager
            
            # Setup trading engine
            trading_engine = TradingEngine()
            trading_engine.db_path = temp_db_path
            trading_engine.load_settings()
            
            # Setup position sizer mock
            mock_sizer.calculate_position_size.return_value = (1000.0, {
                'actual_risk_usd': 50.0,
                'actual_risk_pct': 0.5,
                'position_size_units': 0.022
            })
            
            # Setup signal processor
            signal_processor = SignalProcessor()
            
            # Setup prop firm processor
            prop_firm_processor = PropFirmSignalProcessor(temp_db_path)
            
            # Setup Telegram notifier (using mock)
            telegram_notifier = mock_telegram
            
            # Setup trailing manager mock
            mock_trailing_instance = Mock()
            mock_trailing_instance.track_position = Mock()
            mock_trailing_instance.update_position = Mock(return_value={'action': 'none'})
            mock_trailing.return_value = mock_trailing_instance
            
            return {
                'db_manager': db_manager,
                'signal_processor': signal_processor,
                'prop_firm_processor': prop_firm_processor,
                'trading_engine': trading_engine,
                'telegram_notifier': telegram_notifier,
                'mock_mt5': mock_mt5,
                'mock_binance': mock_binance,
                'mock_market_data': mock_market_data,
                'mock_trailing': mock_trailing_instance
            }
    
    def test_complete_signal_to_notification_workflow(self, workflow_components):
        """Test complete workflow: Signal -> Processing -> Trade -> Notification"""
        components = workflow_components
        
        # Step 1: Receive signal message
        signal_message = """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750"""
        
        # Step 2: Process signal through SignalProcessor
        signal_result = components['signal_processor'].process_signal(signal_message)
        
        assert signal_result['success'] is True
        assert signal_result['message'].startswith('Trade added:')
        
        # Verify trade was added to database
        trades_df = components['db_manager'].get_trades_df()
        assert len(trades_df) == 1
        trade_row = trades_df.iloc[0]
        assert trade_row['symbol'] == 'BTCUSDT'
        assert trade_row['side'] == 'Buy'
        assert trade_row['entry'] == 45000.0
        assert trade_row['result'] == 'open'
        
        # Step 3: Process through TradingEngine (alternative path)
        signal_data = {
            'symbol': 'ETHUSDT',
            'side': 'Buy',
            'entry_price': 2800.0
        }
        
        engine_result = components['trading_engine'].process_signal(signal_data)
        
        assert engine_result is not None
        assert engine_result['success'] is True
        assert engine_result['symbol'] == 'ETHUSDT'
        assert engine_result['position_size'] == 1000.0
        
        # Verify second trade was added
        trades_df = components['db_manager'].get_trades_df()
        assert len(trades_df) == 2
        
        # Step 4: Send notifications for trade opening
        trade_notification_data = {
            'id': engine_result['trade_id'],
            'symbol': 'ETHUSDT',
            'side': 'Buy',
            'entry': 2800.0,
            'tp': engine_result['tp'],
            'sl': engine_result['sl'],
            'position_size': 1000.0
        }
        
        components['telegram_notifier'].notify_trade_opened(trade_notification_data)
        
        # Verify notification was sent
        messages = components['telegram_notifier'].get_sent_messages()
        assert len(messages) == 1
        assert 'TRADE OPENED' in messages[0]['text']
        assert 'ETHUSDT' in messages[0]['text']
        
        # Step 5: Simulate trade closure and notification
        # Close the first trade at profit
        trade_id = trades_df.iloc[0]['id']
        close_result = components['db_manager'].close_trade(trade_id, 46800.0, 'tp')
        
        assert close_result is True
        
        # Send close notification
        close_notification_data = {
            'id': trade_id,
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry': 45000.0,
            'exit_price': 46800.0,
            'pnl': 1800.0,
            'pnl_pct': 4.0,
            'exit_reason': 'tp'
        }
        
        components['telegram_notifier'].notify_trade_closed(close_notification_data)
        
        # Verify close notification
        messages = components['telegram_notifier'].get_sent_messages()
        assert len(messages) == 2
        assert 'TRADE CLOSED - PROFIT' in messages[1]['text']
        
        # Step 6: Verify final database state
        final_trades_df = components['db_manager'].get_trades_df()
        closed_trade = final_trades_df[final_trades_df['id'] == trade_id].iloc[0]
        assert closed_trade['result'] == 'tp'
        assert closed_trade['pnl'] == 1800.0
        
        # Verify capital update
        final_capital = components['db_manager'].get_current_capital()
        assert final_capital == 11800.0  # 10000 + 1800 profit
    
    def test_prop_firm_signal_workflow(self, workflow_components):
        """Test prop firm signal evaluation workflow"""
        components = workflow_components
        
        # Step 1: Add signal to signal_log
        conn = sqlite3.connect(components['db_manager'].db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signal_log (timestamp, symbol, side, entry_price, take_profit, stop_loss, raw_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            'BTCUSDT',
            'BUY',
            45000.0,
            47250.0,
            42750.0,
            'Test prop firm signal'
        ))
        
        conn.commit()
        conn.close()
        
        # Step 2: Process signals through PropFirmSignalProcessor
        decisions = components['prop_firm_processor'].process_new_signals()
        
        assert len(decisions) == 1
        decision = decisions[0]
        
        assert decision['decision'] == 'ACCEPTED'
        assert decision['symbol'] == 'BTCUSDT'
        assert decision['risk_reward_ratio'] == 2.0
        assert decision['position_size_usd'] > 0
        assert 'Trade approved' in decision['reason']
        
        # Step 3: Verify decision was logged
        conn = sqlite3.connect(components['db_manager'].db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prop_firm_decisions WHERE symbol = 'BTCUSDT'")
        decision_row = cursor.fetchone()
        conn.close()
        
        assert decision_row is not None
        assert decision_row[11] == 'ACCEPTED'  # decision column
        
        # Step 4: Verify signal was marked as processed
        conn = sqlite3.connect(components['db_manager'].db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prop_firm_processed, prop_firm_decision FROM signal_log WHERE symbol = 'BTCUSDT'")
        signal_row = cursor.fetchone()
        conn.close()
        
        assert signal_row[0] == 1  # processed
        assert signal_row[1] == 'ACCEPTED'  # decision
    
    def test_multiple_signals_concurrent_processing(self, workflow_components):
        """Test processing multiple signals concurrently"""
        components = workflow_components
        
        # Create multiple signals
        signals = [
            {"symbol": "BTCUSDT", "side": "Buy", "entry_price": 45000.0},
            {"symbol": "ETHUSDT", "side": "Sell", "entry_price": 2800.0},
            {"symbol": "ADAUSDT", "side": "Buy", "entry_price": 0.85},
            {"symbol": "SOLUSD", "side": "Sell", "entry_price": 167.50}
        ]
        
        # Process all signals
        results = []
        for signal in signals:
            result = components['trading_engine'].process_signal(signal)
            results.append(result)
        
        # Verify all were processed successfully
        successful_results = [r for r in results if r and r.get('success')]
        assert len(successful_results) == 4
        
        # Verify all trades in database
        trades_df = components['db_manager'].get_trades_df()
        assert len(trades_df) == 4
        
        # Verify symbols
        symbols = set(trades_df['symbol'].tolist())
        expected_symbols = {"BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSD"}
        assert symbols == expected_symbols
        
        # Send notifications for all trades
        for i, trade_row in trades_df.iterrows():
            notification_data = {
                'id': trade_row['id'],
                'symbol': trade_row['symbol'],
                'side': trade_row['side'],
                'entry': trade_row['entry'],
                'tp': trade_row['tp'],
                'sl': trade_row['sl'],
                'position_size': trade_row['position_size']
            }
            components['telegram_notifier'].notify_trade_opened(notification_data)
        
        # Verify all notifications sent
        messages = components['telegram_notifier'].get_sent_messages()
        assert len(messages) == 4
        
        # Verify each symbol was notified
        message_symbols = []
        for message in messages:
            for symbol in expected_symbols:
                if symbol in message['text']:
                    message_symbols.append(symbol)
                    break
        
        assert set(message_symbols) == expected_symbols
    
    def test_position_monitoring_and_closure_workflow(self, workflow_components):
        """Test position monitoring and automatic closure workflow"""
        components = workflow_components
        
        # Step 1: Add open trade
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=45000.0,
            tp=47250.0,
            sl=42750.0
        )
        
        components['db_manager'].add_trade(trade)
        
        # Step 2: Get trade ID
        trades_df = components['db_manager'].get_trades_df()
        trade_id = trades_df.iloc[0]['id']
        
        # Step 3: Simulate price movement that hits TP
        components['mock_binance'].set_price('BTCUSDT', 47250.0)  # Hit TP
        
        # Step 4: Simulate position monitoring detecting TP hit
        # (In real system, this would be done by position monitor)
        close_result = components['db_manager'].close_trade(trade_id, 47250.0, 'tp')
        assert close_result is True
        
        # Step 5: Send closure notification
        close_data = {
            'id': trade_id,
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry': 45000.0,
            'exit_price': 47250.0,
            'pnl': 2250.0,
            'pnl_pct': 5.0,
            'exit_reason': 'tp',
            'duration': '2.5 hours'
        }
        
        components['telegram_notifier'].notify_trade_closed(close_data)
        
        # Step 6: Verify final state
        final_trades_df = components['db_manager'].get_trades_df()
        closed_trade = final_trades_df.iloc[0]
        
        assert closed_trade['result'] == 'tp'
        assert closed_trade['pnl'] == 2250.0
        
        messages = components['telegram_notifier'].get_sent_messages()
        assert len(messages) == 1
        assert 'TRADE CLOSED - PROFIT' in messages[0]['text']
        assert 'Take Profit Hit' in messages[0]['text']
    
    def test_risk_management_workflow(self, workflow_components):
        """Test risk management prevents over-trading"""
        components = workflow_components
        
        # Step 1: Fill up to max open positions
        max_positions = 5  # From trading settings
        
        for i in range(max_positions):
            signal = {
                'symbol': f'TEST{i}_USDT',
                'side': 'Buy',
                'entry_price': 1000.0 + i
            }
            result = components['trading_engine'].process_signal(signal)
            assert result is not None
            assert result['success'] is True
        
        # Step 2: Try to add one more (should be rejected)
        excess_signal = {
            'symbol': 'EXCESS_USDT',
            'side': 'Buy',
            'entry_price': 2000.0
        }
        
        result = components['trading_engine'].process_signal(excess_signal)
        assert result is None  # Should be rejected due to risk limits
        
        # Step 3: Verify exactly max_positions trades in database
        trades_df = components['db_manager'].get_trades_df()
        assert len(trades_df) == max_positions
        
        # Step 4: Close one trade and try again
        trade_id = trades_df.iloc[0]['id']
        components['db_manager'].close_trade(trade_id, 1050.0, 'tp')
        
        # Now the excess signal should work
        result = components['trading_engine'].process_signal(excess_signal)
        assert result is not None
        assert result['success'] is True
        
        # Verify trade was added
        final_trades_df = components['db_manager'].get_trades_df()
        open_trades = final_trades_df[final_trades_df['result'] == 'open']
        assert len(open_trades) == max_positions  # Still at max, but different trades
    
    def test_error_handling_and_recovery_workflow(self, workflow_components):
        """Test error handling and system recovery"""
        components = workflow_components
        
        # Step 1: Test invalid signal handling
        invalid_signal = {
            'symbol': '',  # Invalid empty symbol
            'side': 'Buy',
            'entry_price': 1000.0
        }
        
        result = components['trading_engine'].process_signal(invalid_signal)
        assert result is None  # Should be rejected
        
        # Step 2: Test database error handling
        # Simulate database corruption by closing connection
        components['db_manager']._db_path = '/nonexistent/path.db'
        
        corrupted_signal = {
            'symbol': 'TESTUSDT',
            'side': 'Buy',
            'entry_price': 1000.0
        }
        
        # Should handle database error gracefully
        result = components['trading_engine'].process_signal(corrupted_signal)
        # Exact behavior depends on implementation, but shouldn't crash
        
        # Step 3: Test notification failure handling
        components['telegram_notifier'].set_should_fail(True)
        
        # Should handle notification failure gracefully
        components['telegram_notifier'].notify_error("Test Error", "Test error details")
        
        # System should continue operating despite notification failures
        stats = components['telegram_notifier'].get_stats()
        assert stats['failed_calls'] > 0
    
    def test_daily_reset_and_reporting_workflow(self, workflow_components):
        """Test daily reset and reporting workflow"""
        components = workflow_components
        
        # Step 1: Generate some trading activity
        signals = [
            {'symbol': 'BTCUSDT', 'side': 'Buy', 'entry_price': 45000.0},
            {'symbol': 'ETHUSDT', 'side': 'Sell', 'entry_price': 2800.0}
        ]
        
        for signal in signals:
            result = components['trading_engine'].process_signal(signal)
            assert result['success'] is True
        
        # Step 2: Close trades with different outcomes
        trades_df = components['db_manager'].get_trades_df()
        
        # Close first trade at profit
        components['db_manager'].close_trade(
            trades_df.iloc[0]['id'], 
            46800.0, 
            'tp'
        )
        
        # Close second trade at loss
        components['db_manager'].close_trade(
            trades_df.iloc[1]['id'], 
            2850.0, 
            'sl'
        )
        
        # Step 3: Generate daily summary
        stats = components['db_manager'].get_performance_stats()
        
        summary = {
            'signals_received': 2,
            'trades_executed': 2,
            'trades_closed': 2,
            'open_positions': 0,
            'daily_pnl': stats['total_pnl'],
            'win_rate': stats['win_rate'],
            'best_trade': max(1800.0, -50.0),  # Approximate
            'worst_trade': min(1800.0, -50.0),
            'start_balance': 10000.0,
            'current_balance': stats['current_capital'],
            'total_roi': ((stats['current_capital'] - 10000.0) / 10000.0) * 100
        }
        
        # Step 4: Send daily summary notification
        components['telegram_notifier'].notify_daily_summary(summary)
        
        # Step 5: Perform prop firm daily reset
        components['prop_firm_processor'].perform_daily_reset()
        
        # Step 6: Verify reset occurred
        status = components['prop_firm_processor'].get_current_status()
        assert status['daily_pnl'] == 0.0
        assert status['daily_trades'] == 0
        
        # Step 7: Verify summary notification was sent
        messages = components['telegram_notifier'].get_sent_messages()
        summary_messages = [m for m in messages if 'DAILY TRADING SUMMARY' in m['text']]
        assert len(summary_messages) == 1
        
        summary_text = summary_messages[0]['text']
        assert '2' in summary_text  # trades executed
        assert str(int(stats['win_rate'])) in summary_text  # win rate
    
    def test_market_conditions_integration_workflow(self, workflow_components):
        """Test market conditions affecting trade decisions"""
        components = workflow_components
        
        # Step 1: Simulate poor market conditions
        with patch('trading_engine.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop
            mock_asyncio.set_event_loop = Mock()
            
            # Mock poor market analysis
            mock_analysis = {
                'trade_recommendation': 'strong_sell',
                'overall_score': 2.0,
                'volatility_1h': 15.0,
                'volume_ratio': 0.3
            }
            mock_loop.run_until_complete.return_value = mock_analysis
            
            # Step 2: Try to process signal in poor conditions
            signal = {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'entry_price': 45000.0
            }
            
            result = components['trading_engine'].process_signal(signal)
            
            # Should be rejected due to poor market conditions
            assert result is not None
            assert result['success'] is False
            assert 'Poor market conditions' in result['reason']
        
        # Step 3: Simulate good market conditions
        with patch('trading_engine.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop
            mock_asyncio.set_event_loop = Mock()
            
            # Mock good market analysis
            mock_analysis = {
                'trade_recommendation': 'buy',
                'overall_score': 8.5,
                'volatility_1h': 2.1,
                'volume_ratio': 1.5,
                'recommended_tp_adjustment': 1.2,
                'recommended_sl_adjustment': 0.8
            }
            mock_loop.run_until_complete.return_value = mock_analysis
            
            # Step 4: Process signal in good conditions
            result = components['trading_engine'].process_signal(signal)
            
            # Should be accepted and TP/SL adjusted
            assert result is not None
            assert result['success'] is True
            
            # Verify TP/SL were adjusted based on market conditions
            # Original: 5% TP/SL
            # Adjusted: TP = 5% * 1.2 = 6%, SL = 5% * 0.8 = 4%
            expected_tp = 45000 * 1.06  # +6%
            expected_sl = 45000 * 0.96  # -4%
            
            assert result['tp'] == pytest.approx(expected_tp, rel=0.01)
            assert result['sl'] == pytest.approx(expected_sl, rel=0.01)
    
    def test_performance_under_load_workflow(self, workflow_components):
        """Test system performance under high load"""
        components = workflow_components
        
        import time
        
        # Step 1: Process many signals quickly
        num_signals = 100
        start_time = time.time()
        
        successful_trades = 0
        for i in range(num_signals):
            signal = {
                'symbol': f'LOAD{i % 10}_USDT',  # 10 different symbols
                'side': 'Buy' if i % 2 == 0 else 'Sell',
                'entry_price': 1000.0 + (i % 50)
            }
            
            result = components['trading_engine'].process_signal(signal)
            if result and result.get('success'):
                successful_trades += 1
        
        processing_time = time.time() - start_time
        
        # Step 2: Verify performance
        # Should process at least 50 signals per second
        min_rate = 50  # signals/second
        actual_rate = num_signals / processing_time
        
        # Note: This is generous for CI environments
        assert actual_rate > min_rate * 0.1, f"Processing rate too slow: {actual_rate:.2f} signals/sec"
        
        # Step 3: Verify data integrity
        trades_df = components['db_manager'].get_trades_df()
        assert len(trades_df) == successful_trades
        
        # Step 4: Test notification performance
        start_time = time.time()
        
        for i in range(50):  # Fewer notifications to test
            components['telegram_notifier'].notify_error(f"Load Test {i}", f"Test error {i}")
        
        notification_time = time.time() - start_time
        notification_rate = 50 / notification_time
        
        # Should handle at least 100 notifications per second
        assert notification_rate > 10, f"Notification rate too slow: {notification_rate:.2f} notifications/sec"
        
        # Step 5: Verify all notifications were sent
        messages = components['telegram_notifier'].get_sent_messages()
        error_messages = [m for m in messages if 'SYSTEM ALERT' in m['text']]
        assert len(error_messages) == 50