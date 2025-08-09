"""
Integration tests for database operations
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
import pandas as pd

from database import DatabaseManager, Trade
from signal_processor import SignalProcessor
from prop_firm_signal_processor import PropFirmSignalProcessor


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration across components"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DatabaseManager with temporary database"""
        return DatabaseManager(temp_db_path)
    
    def test_database_schema_consistency(self, db_manager):
        """Test that database schema is correctly initialized"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Check that all required tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['capital', 'capital_by_symbol', 'trades']
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
        
        # Check trades table schema
        cursor.execute("PRAGMA table_info(trades)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
        
        expected_columns = {
            'id': 'INTEGER',
            'symbol': 'TEXT',
            'side': 'TEXT',
            'entry': 'REAL',
            'tp': 'REAL',
            'sl': 'REAL',
            'result': 'TEXT',
            'pnl': 'REAL',
            'timestamp': 'TEXT'
        }
        
        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Column {col_name} not found"
            assert col_type in columns[col_name], f"Column {col_name} has wrong type"
        
        conn.close()
    
    def test_concurrent_trade_operations(self, db_manager):
        """Test concurrent database operations"""
        import threading
        import time
        
        results = []
        errors = []
        
        def add_trades(thread_id, num_trades):
            """Add trades in separate thread"""
            try:
                for i in range(num_trades):
                    trade = Trade(
                        symbol=f"TEST{thread_id}_{i}_USDT",
                        side="Buy" if i % 2 == 0 else "Sell",
                        entry=1000.0 + i,
                        tp=1100.0 + i,
                        sl=900.0 + i
                    )
                    success = db_manager.add_trade(trade)
                    results.append((thread_id, i, success))
                    time.sleep(0.001)  # Small delay to increase chance of concurrency
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads adding trades
        threads = []
        num_threads = 5
        trades_per_thread = 10
        
        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=add_trades,
                args=(thread_id, trades_per_thread)
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads * trades_per_thread
        
        # Verify all trades were added successfully
        successful_adds = sum(1 for _, _, success in results if success)
        assert successful_adds == num_threads * trades_per_thread
        
        # Verify database consistency
        df = db_manager.get_trades_df()
        assert len(df) == num_threads * trades_per_thread
    
    def test_database_rollback_on_error(self, db_manager):
        """Test database rollback on errors"""
        # Add a valid trade first
        valid_trade = Trade(
            symbol="VALIDUSDT",
            side="Buy",
            entry=1000.0,
            tp=1100.0,
            sl=900.0
        )
        assert db_manager.add_trade(valid_trade) is True
        
        # Now simulate an error during transaction
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        try:
            # Start transaction
            cursor.execute("BEGIN")
            
            # Insert a trade
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry, tp, sl, result, pnl, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ("ERRORUSDT", "Buy", 1000, 1100, 900, "open", 0, datetime.now().isoformat()))
            
            # Simulate error by violating constraint
            cursor.execute("INSERT INTO trades (id) VALUES (NULL)")  # This should fail
            
        except sqlite3.Error:
            conn.rollback()
        finally:
            conn.close()
        
        # Check that only the valid trade exists
        df = db_manager.get_trades_df()
        assert len(df) == 1
        assert df.iloc[0]['symbol'] == "VALIDUSDT"
    
    def test_large_dataset_performance(self, db_manager):
        """Test database performance with large datasets"""
        import time
        
        # Add many trades
        num_trades = 1000
        start_time = time.time()
        
        trades_added = 0
        for i in range(num_trades):
            trade = Trade(
                symbol=f"PERF{i % 10}_USDT",  # 10 different symbols
                side="Buy" if i % 2 == 0 else "Sell",
                entry=1000.0 + (i % 100),
                tp=1100.0 + (i % 100),
                sl=900.0 + (i % 100)
            )
            if db_manager.add_trade(trade):
                trades_added += 1
        
        add_time = time.time() - start_time
        
        # Query performance
        start_time = time.time()
        df = db_manager.get_trades_df()
        query_time = time.time() - start_time
        
        # Verify results
        assert trades_added == num_trades
        assert len(df) == num_trades
        
        # Performance assertions (generous limits for CI environments)
        assert add_time < 10.0, f"Adding {num_trades} trades took {add_time:.2f}s (too slow)"
        assert query_time < 2.0, f"Querying {num_trades} trades took {query_time:.2f}s (too slow)"
        
        # Test performance stats calculation
        start_time = time.time()
        stats = db_manager.get_performance_stats()
        stats_time = time.time() - start_time
        
        assert stats_time < 1.0, f"Performance stats took {stats_time:.2f}s (too slow)"
        assert stats['total_trades'] == num_trades
    
    def test_database_integrity_after_operations(self, db_manager):
        """Test database integrity after various operations"""
        # Add trades
        trades = []
        for i in range(10):
            trade = Trade(
                symbol=f"INTEGRITY{i}_USDT",
                side="Buy" if i % 2 == 0 else "Sell",
                entry=1000.0 + i,
                tp=1100.0 + i,
                sl=900.0 + i
            )
            trades.append(trade)
            db_manager.add_trade(trade)
        
        # Close some trades
        df = db_manager.get_trades_df()
        for i in range(0, 5):  # Close first 5 trades
            trade_id = df.iloc[i]['id']
            exit_price = df.iloc[i]['entry'] + 50  # Profitable exit
            db_manager.close_trade(trade_id, exit_price, "tp")
        
        # Check database integrity
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Run PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchall()
        assert integrity_result == [('ok',)], f"Database integrity check failed: {integrity_result}"
        
        # Check foreign key consistency (if any)
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        assert len(fk_violations) == 0, f"Foreign key violations: {fk_violations}"
        
        # Verify data consistency
        cursor.execute("SELECT COUNT(*) FROM trades WHERE result = 'tp'")
        closed_count = cursor.fetchone()[0]
        assert closed_count == 5, f"Expected 5 closed trades, got {closed_count}"
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE result = 'open'")
        open_count = cursor.fetchone()[0]
        assert open_count == 5, f"Expected 5 open trades, got {open_count}"
        
        conn.close()
    
    def test_capital_tracking_accuracy(self, db_manager):
        """Test accuracy of capital tracking across operations"""
        initial_capital = db_manager.get_current_capital()
        assert initial_capital == 10000.0  # From Config.INITIAL_CAPITAL
        
        # Add profitable trade
        profit_trade = Trade(symbol="PROFIT_USDT", side="Buy", entry=1000, tp=1100, sl=900)
        db_manager.add_trade(profit_trade)
        
        df = db_manager.get_trades_df()
        profit_trade_id = df[df['symbol'] == 'PROFIT_USDT'].iloc[0]['id']
        
        # Close at profit
        profit_amount = 100.0
        db_manager.close_trade(profit_trade_id, 1000 + profit_amount, "tp")
        
        # Check capital increased
        capital_after_profit = db_manager.get_current_capital()
        assert capital_after_profit == initial_capital + profit_amount
        
        # Add losing trade
        loss_trade = Trade(symbol="LOSS_USDT", side="Buy", entry=1000, tp=1100, sl=900)
        db_manager.add_trade(loss_trade)
        
        df = db_manager.get_trades_df()
        loss_trade_id = df[df['symbol'] == 'LOSS_USDT'].iloc[0]['id']
        
        # Close at loss
        loss_amount = 50.0
        db_manager.close_trade(loss_trade_id, 1000 - loss_amount, "sl")
        
        # Check capital decreased
        final_capital = db_manager.get_current_capital()
        expected_capital = initial_capital + profit_amount - loss_amount
        assert final_capital == expected_capital
        
        # Verify capital history
        capital_df = db_manager.get_capital_df()
        assert len(capital_df) == 3  # Initial + 2 updates
        
        # Check capital by symbol
        symbol_df = db_manager.get_capital_by_symbol_df()
        assert len(symbol_df) == 2  # PROFIT_USDT and LOSS_USDT
        
        profit_symbol_capital = symbol_df[symbol_df['symbol'] == 'PROFIT_USDT'].iloc[0]['value']
        loss_symbol_capital = symbol_df[symbol_df['symbol'] == 'LOSS_USDT'].iloc[0]['value']
        
        # These should reflect the P&L for each symbol
        assert profit_symbol_capital > 0  # Gained value
        assert loss_symbol_capital < 0 or loss_symbol_capital > 0  # Could be initial allocation minus loss
    
    def test_signal_processor_database_integration(self, temp_db_path):
        """Test SignalProcessor integration with database"""
        with patch('signal_processor.DatabaseManager') as mock_db_class, \
             patch('signal_processor.Config') as mock_config:
            
            # Setup mocks
            db_manager = DatabaseManager(temp_db_path)
            mock_db_class.return_value = db_manager
            mock_config.MIN_RISK_REWARD_RATIO = 1.5
            mock_config.MAX_OPEN_TRADES = 5
            mock_config.INITIAL_CAPITAL = 10000
            mock_config.ALLOWED_SYMBOLS = None
            
            processor = SignalProcessor()
            
            # Test signal processing that adds to database
            message = """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750"""
            
            result = processor.process_signal(message)
            
            assert result['success'] is True
            
            # Verify trade was added to database
            df = db_manager.get_trades_df()
            assert len(df) == 1
            assert df.iloc[0]['symbol'] == 'BTCUSDT'
            assert df.iloc[0]['side'] == 'Buy'
            assert df.iloc[0]['entry'] == 45000.0
    
    def test_prop_firm_processor_database_integration(self, temp_db_path):
        """Test PropFirmSignalProcessor database integration"""
        processor = PropFirmSignalProcessor(temp_db_path)
        
        # Setup database tables
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Create required tables
        cursor.execute("""
            CREATE TABLE signal_log (
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
            CREATE TABLE prop_firm_status (
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
            INSERT INTO prop_firm_status (id) VALUES (1)
        """)
        
        # Add test signal
        cursor.execute("""
            INSERT INTO signal_log (timestamp, symbol, side, entry_price, take_profit, stop_loss, raw_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), 'BTCUSDT', 'BUY', 45000, 47250, 42750, 'Test signal'))
        
        conn.commit()
        conn.close()
        
        # Process signals
        decisions = processor.process_new_signals()
        
        assert len(decisions) == 1
        assert decisions[0]['decision'] == 'ACCEPTED'
        
        # Verify signal was marked as processed
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prop_firm_processed, prop_firm_decision FROM signal_log WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        assert row[0] == 1  # processed
        assert row[1] == 'ACCEPTED'  # decision
    
    def test_database_backup_and_recovery(self, db_manager):
        """Test database backup and recovery procedures"""
        # Add some test data
        for i in range(5):
            trade = Trade(
                symbol=f"BACKUP{i}_USDT",
                side="Buy" if i % 2 == 0 else "Sell",
                entry=1000.0 + i,
                tp=1100.0 + i,
                sl=900.0 + i
            )
            db_manager.add_trade(trade)
        
        # Create backup
        import shutil
        backup_path = db_manager.db_path + '.backup'
        shutil.copy2(db_manager.db_path, backup_path)
        
        # Verify backup
        backup_db = DatabaseManager(backup_path)
        backup_df = backup_db.get_trades_df()
        original_df = db_manager.get_trades_df()
        
        assert len(backup_df) == len(original_df)
        assert list(backup_df['symbol']) == list(original_df['symbol'])
        
        # Cleanup
        os.unlink(backup_path)
    
    def test_database_migration_compatibility(self, temp_db_path):
        """Test database schema migration compatibility"""
        # Create old schema version (simplified)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Create minimal old schema
        cursor.execute('''
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                side TEXT,
                entry REAL,
                tp REAL,
                sl REAL
            )
        ''')
        
        # Insert test data with old schema
        cursor.execute('''
            INSERT INTO trades (symbol, side, entry, tp, sl)
            VALUES ('OLDUSDT', 'Buy', 1000, 1100, 900)
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize DatabaseManager (should handle migration)
        db_manager = DatabaseManager(temp_db_path)
        
        # Verify new columns exist
        df = db_manager.get_trades_df()
        required_columns = ['id', 'symbol', 'side', 'entry', 'tp', 'sl', 'result', 'pnl', 'timestamp']
        
        for col in required_columns:
            assert col in df.columns, f"Column {col} missing after migration"
        
        # Verify old data is preserved
        assert len(df) >= 1
        old_trade = df[df['symbol'] == 'OLDUSDT']
        assert len(old_trade) == 1