import sqlite3
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from config import Config
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Trade data model"""
    symbol: str
    side: str  # 'Buy' or 'Sell'
    entry: float
    tp: float  # Take Profit
    sl: float  # Stop Loss
    result: str = 'open'  # 'open', 'tp', 'sl', 'manual'
    pnl: float = 0.0
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def calculate_pnl(self, exit_price: float) -> float:
        """Calculate PnL based on exit price"""
        multiplier = 1 if self.side.lower() == 'buy' else -1
        return (exit_price - self.entry) * multiplier
    
    def validate(self) -> List[str]:
        """Validate trade data"""
        errors = []
        
        if not self.symbol or not isinstance(self.symbol, str):
            errors.append("Symbol must be a non-empty string")
        
        if self.side not in ['Buy', 'Sell']:
            errors.append("Side must be 'Buy' or 'Sell'")
        
        if self.entry <= 0:
            errors.append("Entry price must be positive")
        
        if self.tp <= 0:
            errors.append("Take profit must be positive")
        
        if self.sl <= 0:
            errors.append("Stop loss must be positive")
        
        # Validate TP/SL logic
        if self.side == 'Buy' and (self.tp <= self.entry or self.sl >= self.entry):
            errors.append("For Buy: TP must be > entry and SL must be < entry")
        
        if self.side == 'Sell' and (self.tp >= self.entry or self.sl <= self.entry):
            errors.append("For Sell: TP must be < entry and SL must be > entry")
        
        return errors

class DatabaseManager:
    """Enhanced database manager with proper error handling and validation"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.get_absolute_db_path()
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialize database with proper schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL CHECK(side IN ('Buy', 'Sell')),
                        entry REAL NOT NULL CHECK(entry > 0),
                        tp REAL NOT NULL CHECK(tp > 0),
                        sl REAL NOT NULL CHECK(sl > 0),
                        result TEXT NOT NULL DEFAULT 'open' CHECK(result IN ('open', 'tp', 'sl', 'manual')),
                        pnl REAL NOT NULL DEFAULT 0.0,
                        timestamp TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create capital table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS capital (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        value REAL NOT NULL CHECK(value >= 0),
                        timestamp TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create capital_by_symbol table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS capital_by_symbol (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol) ON CONFLICT REPLACE
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_capital_timestamp ON capital(timestamp)')
                
                # Initialize capital if empty
                cursor.execute('SELECT COUNT(*) FROM capital')
                if cursor.fetchone()[0] == 0:
                    self._initialize_capital(cursor, Config.INITIAL_CAPITAL)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _initialize_capital(self, cursor, initial_amount: float):
        """Initialize capital with starting amount"""
        timestamp = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO capital (value, timestamp) VALUES (?, ?)',
            (initial_amount, timestamp)
        )
    
    def add_trade(self, trade: Trade) -> bool:
        """Add a new trade with validation"""
        try:
            # Validate trade
            errors = trade.validate()
            if errors:
                logger.error(f"Trade validation failed: {errors}")
                return False
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for maximum open trades
                cursor.execute(
                    "SELECT COUNT(*) FROM trades WHERE result = 'open'"
                )
                open_trades = cursor.fetchone()[0]
                
                if open_trades >= Config.MAX_OPEN_TRADES:
                    logger.warning(f"Maximum open trades ({Config.MAX_OPEN_TRADES}) reached")
                    return False
                
                # Insert trade
                cursor.execute('''
                    INSERT INTO trades (symbol, side, entry, tp, sl, result, pnl, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade.symbol, trade.side, trade.entry, trade.tp, trade.sl,
                    trade.result, trade.pnl, trade.timestamp
                ))
                
                conn.commit()
                logger.info(f"Trade added: {trade.symbol} {trade.side} @ {trade.entry}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add trade: {e}")
            return False
    
    def close_trade(self, trade_id: int, exit_price: float, result: str) -> bool:
        """Close a trade and update capital"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get trade details
                cursor.execute('SELECT * FROM trades WHERE id = ? AND result = "open"', (trade_id,))
                trade_row = cursor.fetchone()
                
                if not trade_row:
                    logger.error(f"Open trade with id {trade_id} not found")
                    return False
                
                # Create trade object for PnL calculation
                trade = Trade(
                    symbol=trade_row['symbol'],
                    side=trade_row['side'],
                    entry=trade_row['entry'],
                    tp=trade_row['tp'],
                    sl=trade_row['sl']
                )
                
                # Calculate PnL
                pnl = trade.calculate_pnl(exit_price)
                
                # Update trade
                cursor.execute('''
                    UPDATE trades 
                    SET result = ?, pnl = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (result, pnl, trade_id))
                
                # Update capital
                self._update_capital(cursor, pnl)
                self._update_capital_by_symbol(cursor, trade.symbol, pnl)
                
                conn.commit()
                logger.info(f"Trade {trade_id} closed with PnL: {pnl:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            return False
    
    def _update_capital(self, cursor, pnl: float):
        """Update total capital"""
        cursor.execute('SELECT value FROM capital ORDER BY timestamp DESC LIMIT 1')
        current_capital = cursor.fetchone()[0]
        new_capital = current_capital + pnl
        timestamp = datetime.now().isoformat()
        
        cursor.execute(
            'INSERT INTO capital (value, timestamp) VALUES (?, ?)',
            (new_capital, timestamp)
        )
    
    def _update_capital_by_symbol(self, cursor, symbol: str, pnl: float):
        """Update capital by symbol"""
        cursor.execute('SELECT value FROM capital_by_symbol WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        
        if row:
            current_value = row[0]
        else:
            current_value = Config.INITIAL_CAPITAL / 10  # Default allocation
        
        new_value = current_value + pnl
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO capital_by_symbol (symbol, value, timestamp)
            VALUES (?, ?, ?)
        ''', (symbol, new_value, timestamp))
    
    def get_current_capital(self) -> float:
        """Get current total capital"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM capital ORDER BY timestamp DESC LIMIT 1')
                result = cursor.fetchone()
                return result[0] if result else Config.INITIAL_CAPITAL
        except Exception as e:
            logger.error(f"Failed to get current capital: {e}")
            return Config.INITIAL_CAPITAL
    
    def get_trades_df(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Get trades as pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM trades ORDER BY timestamp DESC"
                if limit:
                    query += f" LIMIT {limit}"
                return pd.read_sql_query(query, conn)
        except Exception as e:
            logger.error(f"Failed to get trades DataFrame: {e}")
            return pd.DataFrame()
    
    def get_capital_df(self) -> pd.DataFrame:
        """Get capital history as pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(
                    "SELECT * FROM capital ORDER BY timestamp DESC",
                    conn
                )
        except Exception as e:
            logger.error(f"Failed to get capital DataFrame: {e}")
            return pd.DataFrame()
    
    def get_capital_by_symbol_df(self) -> pd.DataFrame:
        """Get capital by symbol as pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(
                    "SELECT * FROM capital_by_symbol ORDER BY symbol",
                    conn
                )
        except Exception as e:
            logger.error(f"Failed to get capital by symbol DataFrame: {e}")
            return pd.DataFrame()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get trading performance statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total trades
                cursor.execute("SELECT COUNT(*) FROM trades")
                total_trades = cursor.fetchone()[0]
                
                # Winning/losing trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
                winning_trades = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl < 0")
                losing_trades = cursor.fetchone()[0]
                
                # Total PnL
                cursor.execute("SELECT SUM(pnl) FROM trades")
                total_pnl = cursor.fetchone()[0] or 0
                
                # Average PnL
                cursor.execute("SELECT AVG(pnl) FROM trades WHERE pnl != 0")
                avg_pnl = cursor.fetchone()[0] or 0
                
                # Win rate
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                return {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'avg_pnl': avg_pnl,
                    'current_capital': self.get_current_capital()
                }
                
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {}