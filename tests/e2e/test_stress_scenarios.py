"""
Stress tests and failure scenario tests
"""

import pytest
import asyncio
import sqlite3
import tempfile
import os
import threading
import time
import random
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from signal_processor import SignalProcessor
from prop_firm_signal_processor import PropFirmSignalProcessor
from trading_engine import TradingEngine
from database import DatabaseManager, Trade
from tests.mocks.mock_mt5 import MockMT5Terminal
from tests.mocks.mock_telegram import MockTelegramNotifier
from tests.mocks.mock_binance import MockBinanceWebSocket


@pytest.mark.stress
class TestStressScenarios:
    """Test system under stress and failure scenarios"""
    
    @pytest.fixture
    def stress_db_path(self):
        """Create temporary database optimized for stress testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create tables with indexes for performance
        cursor.execute('''
            CREATE TABLE trades (
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE capital (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE signal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                raw_message TEXT,
                prop_firm_processed INTEGER DEFAULT 0
            )
        ''')
        
        # Create performance indexes
        cursor.execute('CREATE INDEX idx_trades_symbol_result ON trades(symbol, result)')
        cursor.execute('CREATE INDEX idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX idx_capital_timestamp ON capital(timestamp)')
        cursor.execute('CREATE INDEX idx_signal_processed ON signal_log(prop_firm_processed)')
        
        # Insert initial capital
        cursor.execute("INSERT INTO capital (value, timestamp) VALUES (10000, ?)", 
                      (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def stress_components(self, stress_db_path):
        """Setup components for stress testing"""
        db_manager = DatabaseManager(stress_db_path)
        mock_telegram = MockTelegramNotifier()
        
        with patch('signal_processor.DatabaseManager') as mock_db_signal, \
             patch('trading_engine.TrailingTakeProfitManager'), \
             patch('trading_engine.MarketAnalyzer'), \
             patch('trading_engine.position_sizer') as mock_sizer:
            
            mock_db_signal.return_value = db_manager
            mock_sizer.calculate_position_size.return_value = (1000.0, {'actual_risk_usd': 50.0})
            
            signal_processor = SignalProcessor()
            
            return {
                'db_manager': db_manager,
                'signal_processor': signal_processor,
                'telegram_notifier': mock_telegram,
                'db_path': stress_db_path
            }
    
    def test_high_volume_signal_processing(self, stress_components):
        """Test processing thousands of signals rapidly"""
        components = stress_components
        
        num_signals = 5000
        batch_size = 100
        start_time = time.time()
        
        successful_signals = 0
        failed_signals = 0
        
        # Generate signal messages
        signal_templates = [
            "BTCUSDT Buy\nEntry: {entry}\nTP: {tp}\nSL: {sl}",
            "ETHUSDT Sell\nEntry: {entry}\nTP: {tp}\nSL: {sl}",
            "ADAUSDT Buy\nEntry: {entry}\nTP: {tp}\nSL: {sl}",
            "SOLUSD Sell\nEntry: {entry}\nTP: {tp}\nSL: {sl}"
        ]
        
        # Process signals in batches
        for batch_start in range(0, num_signals, batch_size):
            batch_end = min(batch_start + batch_size, num_signals)
            batch_results = []
            
            for i in range(batch_start, batch_end):
                template = signal_templates[i % len(signal_templates)]
                entry = random.uniform(100, 50000)
                tp = entry * random.uniform(1.02, 1.08)  # 2-8% profit
                sl = entry * random.uniform(0.92, 0.98)  # 2-8% loss
                
                if 'Sell' in template:
                    tp, sl = sl, tp  # Swap for sell orders
                
                signal_message = template.format(
                    entry=f"{entry:.2f}",
                    tp=f"{tp:.2f}",
                    sl=f"{sl:.2f}"
                )
                
                try:
                    result = components['signal_processor'].process_signal(signal_message)
                    if result and result.get('success'):
                        successful_signals += 1
                    else:
                        failed_signals += 1
                except Exception as e:
                    failed_signals += 1
                    print(f"Error processing signal {i}: {e}")
        
        processing_time = time.time() - start_time
        signals_per_second = num_signals / processing_time
        
        print(f"Processed {num_signals} signals in {processing_time:.2f}s")
        print(f"Rate: {signals_per_second:.2f} signals/second")
        print(f"Success: {successful_signals}, Failed: {failed_signals}")
        
        # Verify performance
        assert signals_per_second > 100, f"Signal processing too slow: {signals_per_second:.2f}/s"
        assert successful_signals > num_signals * 0.95, f"Too many failed signals: {failed_signals}"
        
        # Verify database consistency
        trades_df = components['db_manager'].get_trades_df()
        print(f"Total trades in database: {len(trades_df)}")
        
        # Should have created many trades (limited by max open trades setting)
        assert len(trades_df) > 0
    
    def test_concurrent_signal_processing(self, stress_components):
        """Test concurrent signal processing from multiple threads"""
        components = stress_components
        
        num_threads = 10
        signals_per_thread = 200
        
        def process_signals_thread(thread_id):
            """Process signals in a separate thread"""
            results = {'success': 0, 'failure': 0, 'errors': []}
            
            for i in range(signals_per_thread):
                try:
                    signal_message = f"""TEST{thread_id}_{i}_USDT Buy
Entry: {1000 + i}
TP: {1050 + i}
SL: {950 + i}"""
                    
                    result = components['signal_processor'].process_signal(signal_message)
                    if result and result.get('success'):
                        results['success'] += 1
                    else:
                        results['failure'] += 1
                    
                    # Small delay to simulate real-world timing
                    time.sleep(0.001)
                    
                except Exception as e:
                    results['errors'].append(str(e))
                    results['failure'] += 1
            
            return thread_id, results
        
        # Start concurrent processing
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(process_signals_thread, thread_id)
                for thread_id in range(num_threads)
            ]
            
            thread_results = {}
            for future in as_completed(futures):
                thread_id, results = future.result()
                thread_results[thread_id] = results
        
        processing_time = time.time() - start_time
        
        # Aggregate results
        total_success = sum(r['success'] for r in thread_results.values())
        total_failure = sum(r['failure'] for r in thread_results.values())
        total_errors = sum(len(r['errors']) for r in thread_results.values())
        
        total_signals = num_threads * signals_per_thread
        success_rate = (total_success / total_signals) * 100
        
        print(f"Concurrent processing results:")
        print(f"  Threads: {num_threads}, Signals per thread: {signals_per_thread}")
        print(f"  Total time: {processing_time:.2f}s")
        print(f"  Success: {total_success}, Failure: {total_failure}")
        print(f"  Success rate: {success_rate:.2f}%")
        print(f"  Errors: {total_errors}")
        
        # Verify performance and reliability
        assert success_rate > 80, f"Success rate too low: {success_rate:.2f}%"
        assert total_errors < total_signals * 0.1, f"Too many errors: {total_errors}"
        
        # Verify database integrity
        trades_df = components['db_manager'].get_trades_df()
        print(f"Total trades created: {len(trades_df)}")
        
        # Should have some trades (limited by risk management)
        assert len(trades_df) > 0
    
    def test_database_connection_failures(self, stress_components):
        """Test system behavior with database connection issues"""
        components = stress_components
        
        # Test 1: Database file locked
        def lock_database():
            """Lock database from another connection"""
            conn = sqlite3.connect(components['db_path'])
            conn.execute("BEGIN EXCLUSIVE")
            time.sleep(0.5)  # Hold lock briefly
            conn.close()
        
        # Start database lock in background
        lock_thread = threading.Thread(target=lock_database)
        lock_thread.start()
        
        time.sleep(0.1)  # Let lock establish
        
        # Try to process signal during lock
        signal_message = """LOCKTEST_USDT Buy
Entry: 1000
TP: 1100
SL: 900"""
        
        result = components['signal_processor'].process_signal(signal_message)
        # Should handle gracefully (might succeed or fail, but shouldn't crash)
        
        lock_thread.join()
        
        # Test 2: Database file deleted
        original_path = components['db_manager'].db_path
        backup_path = original_path + '.backup'
        
        # Create backup and delete original
        import shutil
        shutil.copy2(original_path, backup_path)
        os.unlink(original_path)
        
        # Try to process signal with missing database
        result = components['signal_processor'].process_signal(signal_message)
        # Should handle gracefully without crashing
        
        # Restore database
        shutil.move(backup_path, original_path)
        
        # Test 3: Corrupted database
        with open(original_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        # Try to process signal with corrupted database
        result = components['signal_processor'].process_signal(signal_message)
        # Should handle gracefully
        
        # Cleanup - restore working database
        components['db_manager'] = DatabaseManager(components['db_path'])
    
    def test_memory_usage_under_load(self, stress_components):
        """Test memory usage with large datasets"""
        components = stress_components
        
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available for memory testing")
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large number of trades
        large_trade_count = 10000
        
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Add many trades to database
        for i in range(0, large_trade_count, 100):  # Process in batches
            batch_trades = []
            for j in range(100):
                if i + j >= large_trade_count:
                    break
                
                trade = Trade(
                    symbol=f"MEM{(i+j) % 50}_USDT",  # 50 different symbols
                    side="Buy" if (i+j) % 2 == 0 else "Sell",
                    entry=random.uniform(100, 1000),
                    tp=random.uniform(110, 1100),
                    sl=random.uniform(90, 900)
                )
                batch_trades.append(trade)
            
            # Add trades
            for trade in batch_trades:
                components['db_manager'].add_trade(trade)
            
            # Check memory periodically
            if i % 1000 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"Memory at {i} trades: {current_memory:.2f} MB")
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"Final memory usage: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable (less than 500MB for 10k trades)
        assert memory_increase < 500, f"Excessive memory usage: {memory_increase:.2f} MB"
        
        # Test querying large dataset
        start_time = time.time()
        trades_df = components['db_manager'].get_trades_df()
        query_time = time.time() - start_time
        
        print(f"Query time for {len(trades_df)} trades: {query_time:.2f}s")
        
        # Query should complete in reasonable time
        assert query_time < 5.0, f"Query too slow: {query_time:.2f}s"
        assert len(trades_df) > 5000  # Should have created many trades
    
    def test_network_failure_simulation(self, stress_components):
        """Test behavior during simulated network failures"""
        components = stress_components
        
        # Test Telegram notification failures
        failure_scenarios = [
            "Connection timeout",
            "Rate limit exceeded", 
            "Invalid bot token",
            "Chat not found",
            "Network unreachable"
        ]
        
        for scenario in failure_scenarios:
            print(f"Testing scenario: {scenario}")
            
            # Enable failure mode
            components['telegram_notifier'].set_should_fail(True)
            
            # Try to send various notifications
            test_notifications = [
                lambda: components['telegram_notifier'].notify_new_signal({
                    'symbol': 'BTCUSDT', 'side': 'BUY', 'entry_price': 45000
                }),
                lambda: components['telegram_notifier'].notify_error("Test", scenario),
                lambda: components['telegram_notifier'].notify_trade_opened({
                    'symbol': 'ETHUSDT', 'side': 'SELL', 'entry': 2800, 'id': 'TEST'
                })
            ]
            
            for notification_func in test_notifications:
                result = notification_func()
                # Should fail gracefully without crashing
                assert result is False
            
            # Reset for next scenario
            components['telegram_notifier'].set_should_fail(False)
        
        # Verify system continues to work after failures
        signal_message = """RECOVERY_USDT Buy
Entry: 1000
TP: 1100
SL: 900"""
        
        result = components['signal_processor'].process_signal(signal_message)
        # Should work normally after network recovery
        assert result is not None
    
    def test_extreme_market_volatility(self, stress_components):
        """Test system under extreme market volatility scenarios"""
        components = stress_components
        
        # Simulate extreme price movements
        volatile_scenarios = [
            {"name": "Flash crash", "price_changes": [-0.30, -0.20, -0.15, 0.25, 0.35]},
            {"name": "Pump and dump", "price_changes": [0.50, 0.80, 1.20, -0.60, -0.40]},
            {"name": "High frequency oscillation", "price_changes": [0.05, -0.05, 0.05, -0.05, 0.05, -0.05] * 10}
        ]
        
        for scenario in volatile_scenarios:
            print(f"Testing scenario: {scenario['name']}")
            
            # Add initial trades
            base_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
            initial_trades = []
            
            for symbol in base_symbols:
                trade = Trade(
                    symbol=symbol,
                    side="Buy",
                    entry=10000.0,  # Normalized price
                    tp=11000.0,     # +10%
                    sl=9000.0       # -10%
                )
                components['db_manager'].add_trade(trade)
                initial_trades.append(trade)
            
            # Simulate extreme price movements
            current_price = 10000.0
            
            for i, price_change in enumerate(scenario['price_changes']):
                current_price *= (1 + price_change)
                
                print(f"  Step {i+1}: Price = {current_price:.2f} ({price_change*100:+.1f}%)")
                
                # Check if any trades should be closed
                trades_df = components['db_manager'].get_trades_df()
                open_trades = trades_df[trades_df['result'] == 'open']
                
                for _, trade_row in open_trades.iterrows():
                    # Check TP/SL hits
                    if trade_row['side'] == 'Buy':
                        if current_price >= trade_row['tp']:
                            components['db_manager'].close_trade(trade_row['id'], current_price, 'tp')
                        elif current_price <= trade_row['sl']:
                            components['db_manager'].close_trade(trade_row['id'], current_price, 'sl')
                    else:  # Sell
                        if current_price <= trade_row['tp']:
                            components['db_manager'].close_trade(trade_row['id'], current_price, 'tp')
                        elif current_price >= trade_row['sl']:
                            components['db_manager'].close_trade(trade_row['id'], current_price, 'sl')
                
                # Add some new trades during volatility
                if i % 2 == 0:
                    volatile_signal = f"""VOL{i}_USDT Buy
Entry: {current_price}
TP: {current_price * 1.05}
SL: {current_price * 0.95}"""
                    
                    result = components['signal_processor'].process_signal(volatile_signal)
                    # May succeed or fail due to risk management
            
            # Verify system stability after extreme volatility
            final_trades_df = components['db_manager'].get_trades_df()
            print(f"  Final trade count: {len(final_trades_df)}")
            
            # System should still be operational
            test_signal = f"""POST_VOLATILITY_USDT Buy
Entry: {current_price}
TP: {current_price * 1.02}
SL: {current_price * 0.98}"""
            
            result = components['signal_processor'].process_signal(test_signal)
            # Should handle normally (success depends on risk management)
    
    def test_resource_cleanup_after_failures(self, stress_components):
        """Test that resources are properly cleaned up after failures"""
        components = stress_components
        
        # Test database connection cleanup
        initial_connections = []
        
        # Create many database operations
        for i in range(100):
            try:
                # This should create and cleanup connections properly
                trade = Trade(
                    symbol=f"CLEANUP{i}_USDT",
                    side="Buy",
                    entry=1000,
                    tp=1100,
                    sl=900
                )
                components['db_manager'].add_trade(trade)
                
                # Occasionally cause errors
                if i % 10 == 0:
                    try:
                        # Cause database error
                        conn = sqlite3.connect(components['db_path'])
                        conn.execute("INVALID SQL STATEMENT")
                        conn.close()
                    except:
                        pass  # Expected to fail
                
            except Exception:
                pass  # Some operations may fail, that's expected
        
        # Verify system is still operational
        final_trade = Trade(
            symbol="FINAL_USDT",
            side="Buy",
            entry=1000,
            tp=1100,
            sl=900
        )
        result = components['db_manager'].add_trade(final_trade)
        
        # Should still work after all the errors
        assert result is True
        
        # Check final database state
        trades_df = components['db_manager'].get_trades_df()
        print(f"Trades created during cleanup test: {len(trades_df)}")
        assert len(trades_df) > 0
    
    def test_performance_degradation_detection(self, stress_components):
        """Test detection of performance degradation"""
        components = stress_components
        
        # Measure baseline performance
        baseline_signals = 100
        start_time = time.time()
        
        for i in range(baseline_signals):
            signal_message = f"""BASELINE{i}_USDT Buy
Entry: {1000 + i}
TP: {1100 + i}
SL: {900 + i}"""
            components['signal_processor'].process_signal(signal_message)
        
        baseline_time = time.time() - start_time
        baseline_rate = baseline_signals / baseline_time
        
        print(f"Baseline performance: {baseline_rate:.2f} signals/second")
        
        # Add load and measure degradation
        # Fill database with many trades
        for i in range(1000):
            trade = Trade(
                symbol=f"LOAD{i % 20}_USDT",
                side="Buy" if i % 2 == 0 else "Sell",
                entry=random.uniform(100, 1000),
                tp=random.uniform(110, 1100),
                sl=random.uniform(90, 900)
            )
            components['db_manager'].add_trade(trade)
        
        # Measure performance under load
        load_signals = 100
        start_time = time.time()
        
        for i in range(load_signals):
            signal_message = f"""LOAD{i}_USDT Buy
Entry: {2000 + i}
TP: {2200 + i}
SL: {1800 + i}"""
            components['signal_processor'].process_signal(signal_message)
        
        load_time = time.time() - start_time
        load_rate = load_signals / load_time
        
        print(f"Under-load performance: {load_rate:.2f} signals/second")
        
        # Calculate performance degradation
        degradation = ((baseline_rate - load_rate) / baseline_rate) * 100
        print(f"Performance degradation: {degradation:.2f}%")
        
        # Performance should not degrade more than 50%
        assert degradation < 50, f"Excessive performance degradation: {degradation:.2f}%"
        
        # Verify system is still functional
        trades_df = components['db_manager'].get_trades_df()
        print(f"Total trades after load test: {len(trades_df)}")
        
        assert len(trades_df) > 1000  # Should have many trades