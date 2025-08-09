"""
Unit tests for Database components
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
import pandas as pd

from database import DatabaseManager, Trade


@pytest.mark.unit
class TestTrade:
    """Test Trade data model"""
    
    def test_trade_creation(self):
        """Test basic trade creation"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        assert trade.symbol == "BTCUSDT"
        assert trade.side == "Buy"
        assert trade.entry == 50000.0
        assert trade.tp == 52500.0
        assert trade.sl == 47500.0
        assert trade.result == "open"
        assert trade.pnl == 0.0
        assert trade.timestamp is not None
    
    def test_trade_with_timestamp(self):
        """Test trade creation with explicit timestamp"""
        timestamp = "2023-01-01T12:00:00"
        trade = Trade(
            symbol="ETHUSDT",
            side="Sell",
            entry=2000.0,
            tp=1900.0,
            sl=2100.0,
            timestamp=timestamp
        )
        
        assert trade.timestamp == timestamp
    
    def test_calculate_pnl_buy_profit(self):
        """Test PnL calculation for profitable buy trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        # Exit at higher price (profit)
        pnl = trade.calculate_pnl(51000.0)
        assert pnl == 1000.0  # 51000 - 50000
    
    def test_calculate_pnl_buy_loss(self):
        """Test PnL calculation for losing buy trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        # Exit at lower price (loss)
        pnl = trade.calculate_pnl(49000.0)
        assert pnl == -1000.0  # 49000 - 50000
    
    def test_calculate_pnl_sell_profit(self):
        """Test PnL calculation for profitable sell trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Sell",
            entry=50000.0,
            tp=47500.0,
            sl=52500.0
        )
        
        # Exit at lower price (profit for sell)
        pnl = trade.calculate_pnl(49000.0)
        assert pnl == 1000.0  # (50000 - 49000) * -1 for sell = 1000
    
    def test_calculate_pnl_sell_loss(self):
        """Test PnL calculation for losing sell trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Sell",
            entry=50000.0,
            tp=47500.0,
            sl=52500.0
        )
        
        # Exit at higher price (loss for sell)
        pnl = trade.calculate_pnl(51000.0)
        assert pnl == -1000.0  # (50000 - 51000) * -1 for sell = -1000
    
    def test_validate_valid_buy_trade(self):
        """Test validation of valid buy trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,  # Above entry
            sl=47500.0   # Below entry
        )
        
        errors = trade.validate()
        assert len(errors) == 0
    
    def test_validate_valid_sell_trade(self):
        """Test validation of valid sell trade"""
        trade = Trade(
            symbol="ETHUSDT",
            side="Sell",
            entry=2000.0,
            tp=1900.0,  # Below entry
            sl=2100.0   # Above entry
        )
        
        errors = trade.validate()
        assert len(errors) == 0
    
    def test_validate_empty_symbol(self):
        """Test validation with empty symbol"""
        trade = Trade(
            symbol="",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        errors = trade.validate()
        assert len(errors) > 0
        assert any("Symbol must be" in error for error in errors)
    
    def test_validate_invalid_side(self):
        """Test validation with invalid side"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Long",  # Should be Buy or Sell
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        errors = trade.validate()
        assert len(errors) > 0
        assert any("Side must be" in error for error in errors)
    
    def test_validate_negative_prices(self):
        """Test validation with negative prices"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=-1000.0,
            tp=-500.0,
            sl=-1500.0
        )
        
        errors = trade.validate()
        assert len(errors) >= 3  # All prices should be positive
    
    def test_validate_buy_wrong_tp_sl(self):
        """Test validation of buy trade with wrong TP/SL positions"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=45000.0,  # TP below entry (wrong for buy)
            sl=55000.0   # SL above entry (wrong for buy)
        )
        
        errors = trade.validate()
        assert len(errors) > 0
        assert any("TP must be > entry and SL must be < entry" in error for error in errors)
    
    def test_validate_sell_wrong_tp_sl(self):
        """Test validation of sell trade with wrong TP/SL positions"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Sell",
            entry=50000.0,
            tp=55000.0,  # TP above entry (wrong for sell)
            sl=45000.0   # SL below entry (wrong for sell)
        )
        
        errors = trade.validate()
        assert len(errors) > 0
        assert any("TP must be < entry and SL must be > entry" in error for error in errors)


@pytest.mark.unit
class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DatabaseManager with temporary database"""
        with patch('database.Config') as mock_config:
            mock_config.get_absolute_db_path.return_value = temp_db_path
            mock_config.INITIAL_CAPITAL = 10000.0
            mock_config.MAX_OPEN_TRADES = 5
            return DatabaseManager(temp_db_path)
    
    def test_init_database(self, db_manager):
        """Test database initialization"""
        # Check that tables exist
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Check trades table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        assert cursor.fetchone() is not None
        
        # Check capital table  
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capital'")
        assert cursor.fetchone() is not None
        
        # Check capital_by_symbol table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capital_by_symbol'")
        assert cursor.fetchone() is not None
        
        # Check initial capital was inserted
        cursor.execute("SELECT COUNT(*) FROM capital")
        assert cursor.fetchone()[0] > 0
        
        conn.close()
    
    def test_add_valid_trade(self, db_manager):
        """Test adding a valid trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        result = db_manager.add_trade(trade)
        assert result is True
        
        # Verify trade was added
        df = db_manager.get_trades_df()
        assert len(df) == 1
        assert df.iloc[0]['symbol'] == "BTCUSDT"
        assert df.iloc[0]['side'] == "Buy"
        assert df.iloc[0]['entry'] == 50000.0
    
    def test_add_invalid_trade(self, db_manager):
        """Test adding an invalid trade"""
        trade = Trade(
            symbol="",  # Invalid empty symbol
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        
        result = db_manager.add_trade(trade)
        assert result is False
        
        # Verify no trade was added
        df = db_manager.get_trades_df()
        assert len(df) == 0
    
    @patch('database.Config')
    def test_add_trade_max_limit(self, mock_config, db_manager):
        """Test that max open trades limit is enforced"""
        mock_config.MAX_OPEN_TRADES = 2
        
        # Add max number of trades
        for i in range(2):
            trade = Trade(
                symbol=f"TEST{i}USDT",
                side="Buy",
                entry=1000.0,
                tp=1100.0,
                sl=900.0
            )
            result = db_manager.add_trade(trade)
            assert result is True
        
        # Try to add one more (should fail)
        trade = Trade(
            symbol="EXTRAUSDT",
            side="Buy", 
            entry=1000.0,
            tp=1100.0,
            sl=900.0
        )
        result = db_manager.add_trade(trade)
        assert result is False
    
    def test_close_trade_profit(self, db_manager):
        """Test closing a trade with profit"""
        # Add a trade first
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        db_manager.add_trade(trade)
        
        # Get trade ID
        df = db_manager.get_trades_df()
        trade_id = df.iloc[0]['id']
        
        # Close trade at profit
        result = db_manager.close_trade(trade_id, 51000.0, "tp")
        assert result is True
        
        # Verify trade was closed
        df = db_manager.get_trades_df()
        closed_trade = df.iloc[0]
        assert closed_trade['result'] == "tp"
        assert closed_trade['pnl'] == 1000.0  # 51000 - 50000
        
        # Verify capital was updated
        current_capital = db_manager.get_current_capital()
        assert current_capital == 11000.0  # 10000 + 1000 profit
    
    def test_close_trade_loss(self, db_manager):
        """Test closing a trade with loss"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        db_manager.add_trade(trade)
        
        df = db_manager.get_trades_df()
        trade_id = df.iloc[0]['id']
        
        # Close trade at loss
        result = db_manager.close_trade(trade_id, 49000.0, "sl")
        assert result is True
        
        # Verify trade was closed
        df = db_manager.get_trades_df()
        closed_trade = df.iloc[0]
        assert closed_trade['result'] == "sl"
        assert closed_trade['pnl'] == -1000.0  # 49000 - 50000
        
        # Verify capital was updated
        current_capital = db_manager.get_current_capital()
        assert current_capital == 9000.0  # 10000 - 1000 loss
    
    def test_close_nonexistent_trade(self, db_manager):
        """Test closing a non-existent trade"""
        result = db_manager.close_trade(999, 50000.0, "manual")
        assert result is False
    
    def test_close_already_closed_trade(self, db_manager):
        """Test closing an already closed trade"""
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        db_manager.add_trade(trade)
        
        df = db_manager.get_trades_df()
        trade_id = df.iloc[0]['id']
        
        # Close trade first time
        db_manager.close_trade(trade_id, 51000.0, "tp")
        
        # Try to close again
        result = db_manager.close_trade(trade_id, 52000.0, "manual")
        assert result is False
    
    def test_get_current_capital_initial(self, db_manager):
        """Test getting initial capital"""
        capital = db_manager.get_current_capital()
        assert capital == 10000.0
    
    def test_get_trades_df_empty(self, db_manager):
        """Test getting trades DataFrame when empty"""
        df = db_manager.get_trades_df()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_get_trades_df_with_limit(self, db_manager):
        """Test getting trades DataFrame with limit"""
        # Add multiple trades
        for i in range(5):
            trade = Trade(
                symbol=f"TEST{i}USDT",
                side="Buy",
                entry=1000.0 + i,
                tp=1100.0 + i,
                sl=900.0 + i
            )
            db_manager.add_trade(trade)
        
        # Get limited results
        df = db_manager.get_trades_df(limit=3)
        assert len(df) == 3
        
        # Should be ordered by timestamp DESC (most recent first)
        assert df.iloc[0]['symbol'] == "TEST4USDT"
        assert df.iloc[1]['symbol'] == "TEST3USDT"
        assert df.iloc[2]['symbol'] == "TEST2USDT"
    
    def test_get_capital_df(self, db_manager):
        """Test getting capital history DataFrame"""
        df = db_manager.get_capital_df()
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1  # At least initial capital entry
        assert 'value' in df.columns
        assert 'timestamp' in df.columns
    
    def test_get_capital_by_symbol_df(self, db_manager):
        """Test getting capital by symbol DataFrame"""
        # Add and close a trade to create symbol-specific capital
        trade = Trade(
            symbol="BTCUSDT",
            side="Buy",
            entry=50000.0,
            tp=52500.0,
            sl=47500.0
        )
        db_manager.add_trade(trade)
        
        df = db_manager.get_trades_df()
        trade_id = df.iloc[0]['id']
        db_manager.close_trade(trade_id, 51000.0, "tp")
        
        # Get capital by symbol
        df = db_manager.get_capital_by_symbol_df()
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1
        assert 'symbol' in df.columns
        assert 'value' in df.columns
    
    def test_get_performance_stats_empty(self, db_manager):
        """Test performance stats with no trades"""
        stats = db_manager.get_performance_stats()
        
        assert stats['total_trades'] == 0
        assert stats['winning_trades'] == 0
        assert stats['losing_trades'] == 0
        assert stats['win_rate'] == 0
        assert stats['total_pnl'] == 0
        assert stats['avg_pnl'] == 0
        assert stats['current_capital'] == 10000.0
    
    def test_get_performance_stats_with_trades(self, db_manager):
        """Test performance stats with completed trades"""
        # Add winning trade
        trade1 = Trade(symbol="BTCUSDT", side="Buy", entry=50000.0, tp=52500.0, sl=47500.0)
        db_manager.add_trade(trade1)
        df = db_manager.get_trades_df()
        trade1_id = df.iloc[0]['id']
        db_manager.close_trade(trade1_id, 51000.0, "tp")  # +1000 profit
        
        # Add losing trade
        trade2 = Trade(symbol="ETHUSDT", side="Buy", entry=2000.0, tp=2200.0, sl=1800.0)
        db_manager.add_trade(trade2)
        df = db_manager.get_trades_df()
        trade2_id = df[df['symbol'] == 'ETHUSDT'].iloc[0]['id']
        db_manager.close_trade(trade2_id, 1900.0, "sl")  # -100 loss
        
        stats = db_manager.get_performance_stats()
        
        assert stats['total_trades'] == 2
        assert stats['winning_trades'] == 1
        assert stats['losing_trades'] == 1
        assert stats['win_rate'] == 50.0
        assert stats['total_pnl'] == 900.0  # 1000 - 100
        assert stats['avg_pnl'] == 450.0   # 900 / 2
        assert stats['current_capital'] == 10900.0  # 10000 + 900
    
    def test_context_manager_success(self, db_manager):
        """Test context manager with successful operation"""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades")
            result = cursor.fetchone()
            assert result is not None
    
    def test_context_manager_exception(self, db_manager):
        """Test context manager with exception (should rollback)"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO trades (symbol, side, entry, tp, sl) VALUES (?, ?, ?, ?, ?)", 
                              ("TEST", "Buy", 1000, 1100, 900))
                # Cause an exception
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Verify rollback occurred (no trade should be added)
        df = db_manager.get_trades_df()
        assert len(df) == 0