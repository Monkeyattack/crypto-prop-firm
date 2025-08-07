"""
Prop Firm Manager for $10,000 One-Step Evaluation
Based on Breakout Prop requirements
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PropFirmConfig:
    """Configuration for prop firm evaluation"""
    # Account settings
    account_size: float = 10000.00
    evaluation_type: str = "one_step"
    
    # Targets and limits
    profit_target: float = 1000.00  # 10% of account
    max_drawdown: float = 600.00    # 6% of account
    max_daily_loss: float = 500.00  # 5% of account
    
    # Leverage limits
    max_leverage_btc_eth: float = 5.0
    max_leverage_altcoins: float = 2.0
    
    # Risk parameters
    risk_per_trade_percent: float = 1.5  # 1.5% per trade
    max_concurrent_trades: int = 3
    warning_threshold_percent: float = 75.0  # Warn at 75% of limits
    
    # Reset time (UTC)
    daily_reset_hour: int = 0
    daily_reset_minute: int = 30
    
    # Safety features
    auto_stop_at_daily_limit: bool = True
    auto_stop_at_drawdown: bool = True
    reduce_size_near_limits: bool = True

@dataclass
class AccountStatus:
    """Current account status and metrics"""
    current_balance: float
    starting_balance: float
    peak_balance: float
    
    # Daily metrics (reset at 0030 UTC)
    daily_starting_balance: float
    daily_pnl: float
    daily_peak: float
    daily_trough: float
    daily_trades: int
    
    # Overall metrics
    total_pnl: float
    total_pnl_percent: float
    current_drawdown: float
    max_drawdown_seen: float
    
    # Progress
    profit_achieved: float
    profit_remaining: float
    progress_percent: float
    
    # Status flags
    is_trading_allowed: bool
    daily_limit_reached: bool
    drawdown_limit_reached: bool
    evaluation_passed: bool
    evaluation_failed: bool
    
    # Timestamps
    last_update: str
    daily_reset_time: str
    evaluation_start: str

class PropFirmManager:
    """Manages prop firm evaluation rules and risk management"""
    
    def __init__(self, config: PropFirmConfig = None, db_path: str = "prop_firm.db"):
        self.config = config or PropFirmConfig()
        self.db_path = db_path
        self.status = self._initialize_status()
        self._setup_database()
        self._load_or_create_account()
        
    def _initialize_status(self) -> AccountStatus:
        """Initialize account status"""
        now = datetime.now(timezone.utc)
        reset_time = self._get_next_reset_time()
        
        return AccountStatus(
            current_balance=self.config.account_size,
            starting_balance=self.config.account_size,
            peak_balance=self.config.account_size,
            daily_starting_balance=self.config.account_size,
            daily_pnl=0.0,
            daily_peak=self.config.account_size,
            daily_trough=self.config.account_size,
            daily_trades=0,
            total_pnl=0.0,
            total_pnl_percent=0.0,
            current_drawdown=0.0,
            max_drawdown_seen=0.0,
            profit_achieved=0.0,
            profit_remaining=self.config.profit_target,
            progress_percent=0.0,
            is_trading_allowed=True,
            daily_limit_reached=False,
            drawdown_limit_reached=False,
            evaluation_passed=False,
            evaluation_failed=False,
            last_update=now.isoformat(),
            daily_reset_time=reset_time.isoformat(),
            evaluation_start=now.isoformat()
        )
    
    def _setup_database(self):
        """Setup database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Account status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                balance REAL NOT NULL,
                daily_pnl REAL NOT NULL,
                total_pnl REAL NOT NULL,
                drawdown REAL NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        
        # Trade history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prop_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                position_size REAL NOT NULL,
                leverage REAL NOT NULL,
                pnl REAL,
                status TEXT NOT NULL,
                notes TEXT
            )
        ''')
        
        # Daily performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_performance (
                date TEXT PRIMARY KEY,
                starting_balance REAL NOT NULL,
                ending_balance REAL NOT NULL,
                daily_pnl REAL NOT NULL,
                daily_pnl_percent REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                max_drawdown REAL NOT NULL,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_or_create_account(self):
        """Load existing account or create new one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for existing evaluation
        cursor.execute('''
            SELECT balance, total_pnl, drawdown, status 
            FROM account_status 
            ORDER BY id DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        if result:
            balance, total_pnl, drawdown, status_json = result
            status_data = json.loads(status_json)
            
            # Update current status
            self.status.current_balance = balance
            self.status.total_pnl = total_pnl
            self.status.current_drawdown = drawdown
            
            # Check if evaluation is complete
            if status_data.get('evaluation_passed'):
                self.status.evaluation_passed = True
            elif status_data.get('evaluation_failed'):
                self.status.evaluation_failed = True
        
        conn.close()
    
    def _get_next_reset_time(self) -> datetime:
        """Get next daily reset time (0030 UTC)"""
        now = datetime.now(timezone.utc)
        reset_time = now.replace(
            hour=self.config.daily_reset_hour,
            minute=self.config.daily_reset_minute,
            second=0,
            microsecond=0
        )
        
        if now >= reset_time:
            reset_time += timedelta(days=1)
        
        return reset_time
    
    def check_daily_reset(self) -> bool:
        """Check if daily reset is needed"""
        now = datetime.now(timezone.utc)
        reset_time = datetime.fromisoformat(self.status.daily_reset_time)
        
        if now >= reset_time:
            self.perform_daily_reset()
            return True
        return False
    
    def perform_daily_reset(self):
        """Perform daily reset at 0030 UTC"""
        logger.info("Performing daily reset")
        
        # Save daily performance
        self._save_daily_performance()
        
        # Reset daily metrics
        self.status.daily_starting_balance = self.status.current_balance
        self.status.daily_pnl = 0.0
        self.status.daily_peak = self.status.current_balance
        self.status.daily_trough = self.status.current_balance
        self.status.daily_trades = 0
        self.status.daily_limit_reached = False
        
        # Update reset time
        self.status.daily_reset_time = self._get_next_reset_time().isoformat()
        
        # Re-enable trading if only daily limit was reached
        if not self.status.drawdown_limit_reached and not self.status.evaluation_failed:
            self.status.is_trading_allowed = True
        
        self._save_status()
        logger.info(f"Daily reset complete. New balance: ${self.status.current_balance:.2f}")
    
    def can_open_trade(self, symbol: str, position_size: float, 
                      stop_loss_amount: float) -> Tuple[bool, str]:
        """Check if a new trade can be opened"""
        
        # Check if trading is allowed
        if not self.status.is_trading_allowed:
            return False, "Trading is currently disabled"
        
        # Check evaluation status
        if self.status.evaluation_passed:
            return False, "Evaluation already passed"
        
        if self.status.evaluation_failed:
            return False, "Evaluation failed"
        
        # Check daily reset
        self.check_daily_reset()
        
        # Check daily loss limit
        potential_daily_loss = self.status.daily_pnl - stop_loss_amount
        if abs(potential_daily_loss) > self.config.max_daily_loss:
            return False, f"Trade would exceed daily loss limit (${self.config.max_daily_loss:.2f})"
        
        # Check drawdown limit
        potential_drawdown = self.status.current_drawdown + stop_loss_amount
        if potential_drawdown > self.config.max_drawdown:
            return False, f"Trade would exceed maximum drawdown (${self.config.max_drawdown:.2f})"
        
        # Check leverage limits
        leverage = position_size / self.status.current_balance
        is_major = symbol.upper() in ['BTC', 'ETH', 'BTCUSDT', 'ETHUSDT']
        max_leverage = self.config.max_leverage_btc_eth if is_major else self.config.max_leverage_altcoins
        
        if leverage > max_leverage:
            return False, f"Leverage {leverage:.1f}x exceeds limit ({max_leverage}x)"
        
        # Check position sizing
        risk_amount = stop_loss_amount
        risk_percent = (risk_amount / self.status.current_balance) * 100
        
        if risk_percent > self.config.risk_per_trade_percent:
            return False, f"Risk {risk_percent:.1f}% exceeds limit ({self.config.risk_per_trade_percent}%)"
        
        # Warning for high risk
        if self._should_reduce_size():
            return True, "WARNING: Near risk limits - consider reducing position size"
        
        return True, "Trade approved"
    
    def _should_reduce_size(self) -> bool:
        """Check if position size should be reduced due to risk"""
        daily_loss_percent = abs(self.status.daily_pnl / self.config.max_daily_loss) * 100
        drawdown_percent = (self.status.current_drawdown / self.config.max_drawdown) * 100
        
        return (daily_loss_percent >= self.config.warning_threshold_percent or 
                drawdown_percent >= self.config.warning_threshold_percent)
    
    def update_balance(self, new_balance: float):
        """Update account balance after trade"""
        old_balance = self.status.current_balance
        self.status.current_balance = new_balance
        
        # Update P&L
        trade_pnl = new_balance - old_balance
        self.status.daily_pnl += trade_pnl
        self.status.total_pnl = new_balance - self.status.starting_balance
        self.status.total_pnl_percent = (self.status.total_pnl / self.status.starting_balance) * 100
        
        # Update peak balance
        if new_balance > self.status.peak_balance:
            self.status.peak_balance = new_balance
        
        # Update daily peak/trough
        if new_balance > self.status.daily_peak:
            self.status.daily_peak = new_balance
        if new_balance < self.status.daily_trough:
            self.status.daily_trough = new_balance
        
        # Update drawdown
        self.status.current_drawdown = self.status.peak_balance - new_balance
        if self.status.current_drawdown > self.status.max_drawdown_seen:
            self.status.max_drawdown_seen = self.status.current_drawdown
        
        # Update progress
        self.status.profit_achieved = max(0, self.status.total_pnl)
        self.status.profit_remaining = max(0, self.config.profit_target - self.status.profit_achieved)
        self.status.progress_percent = (self.status.profit_achieved / self.config.profit_target) * 100
        
        # Check limits
        self._check_limits()
        
        # Update timestamp
        self.status.last_update = datetime.now(timezone.utc).isoformat()
        
        # Save to database
        self._save_status()
        
        logger.info(f"Balance updated: ${old_balance:.2f} -> ${new_balance:.2f} (PnL: ${trade_pnl:.2f})")
    
    def _check_limits(self):
        """Check if any limits have been breached"""
        # Check daily loss limit
        if abs(self.status.daily_pnl) >= self.config.max_daily_loss:
            self.status.daily_limit_reached = True
            if self.config.auto_stop_at_daily_limit:
                self.status.is_trading_allowed = False
                logger.warning(f"Daily loss limit reached: ${self.status.daily_pnl:.2f}")
        
        # Check drawdown limit
        if self.status.current_drawdown >= self.config.max_drawdown:
            self.status.drawdown_limit_reached = True
            self.status.evaluation_failed = True
            if self.config.auto_stop_at_drawdown:
                self.status.is_trading_allowed = False
                logger.error(f"Maximum drawdown reached: ${self.status.current_drawdown:.2f}")
        
        # Check if evaluation passed
        if self.status.profit_achieved >= self.config.profit_target:
            self.status.evaluation_passed = True
            self.status.is_trading_allowed = False
            logger.info(f"EVALUATION PASSED! Profit target reached: ${self.status.profit_achieved:.2f}")
    
    def record_trade(self, symbol: str, side: str, entry_price: float,
                    position_size: float, leverage: float, notes: str = ""):
        """Record a new trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO prop_trades (
                timestamp, symbol, side, entry_price, position_size, 
                leverage, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).isoformat(),
            symbol, side, entry_price, position_size,
            leverage, 'OPEN', notes
        ))
        
        self.status.daily_trades += 1
        
        conn.commit()
        conn.close()
    
    def close_trade(self, trade_id: int, exit_price: float, pnl: float):
        """Close an existing trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE prop_trades 
            SET exit_price = ?, pnl = ?, status = ? 
            WHERE id = ?
        ''', (exit_price, pnl, 'CLOSED', trade_id))
        
        conn.commit()
        conn.close()
        
        # Update balance
        self.update_balance(self.status.current_balance + pnl)
    
    def _save_status(self):
        """Save current status to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        status_dict = asdict(self.status)
        
        cursor.execute('''
            INSERT INTO account_status (
                timestamp, balance, daily_pnl, total_pnl, drawdown, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.status.last_update,
            self.status.current_balance,
            self.status.daily_pnl,
            self.status.total_pnl,
            self.status.current_drawdown,
            json.dumps(status_dict)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_daily_performance(self):
        """Save daily performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date = datetime.now(timezone.utc).date().isoformat()
        
        # Calculate daily metrics
        daily_pnl_percent = (self.status.daily_pnl / self.status.daily_starting_balance) * 100
        max_daily_dd = self.status.daily_peak - self.status.daily_trough
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_performance (
                date, starting_balance, ending_balance, daily_pnl,
                daily_pnl_percent, trades_count, winning_trades,
                losing_trades, max_drawdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date,
            self.status.daily_starting_balance,
            self.status.current_balance,
            self.status.daily_pnl,
            daily_pnl_percent,
            self.status.daily_trades,
            0,  # To be calculated from trades
            0,  # To be calculated from trades
            max_daily_dd
        ))
        
        conn.commit()
        conn.close()
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        return {
            'account': {
                'current_balance': f"${self.status.current_balance:,.2f}",
                'starting_balance': f"${self.status.starting_balance:,.2f}",
                'peak_balance': f"${self.status.peak_balance:,.2f}",
            },
            'performance': {
                'total_pnl': f"${self.status.total_pnl:,.2f}",
                'total_pnl_percent': f"{self.status.total_pnl_percent:.2f}%",
                'daily_pnl': f"${self.status.daily_pnl:,.2f}",
                'current_drawdown': f"${self.status.current_drawdown:,.2f}",
                'max_drawdown_seen': f"${self.status.max_drawdown_seen:,.2f}",
            },
            'progress': {
                'profit_achieved': f"${self.status.profit_achieved:,.2f}",
                'profit_remaining': f"${self.status.profit_remaining:,.2f}",
                'progress_percent': f"{self.status.progress_percent:.1f}%",
                'target': f"${self.config.profit_target:,.2f}",
            },
            'limits': {
                'daily_loss_limit': f"${self.config.max_daily_loss:,.2f}",
                'daily_loss_used': f"{abs(self.status.daily_pnl / self.config.max_daily_loss * 100):.1f}%",
                'max_drawdown_limit': f"${self.config.max_drawdown:,.2f}",
                'drawdown_used': f"{(self.status.current_drawdown / self.config.max_drawdown * 100):.1f}%",
            },
            'status': {
                'is_trading_allowed': self.status.is_trading_allowed,
                'daily_limit_reached': self.status.daily_limit_reached,
                'drawdown_limit_reached': self.status.drawdown_limit_reached,
                'evaluation_passed': self.status.evaluation_passed,
                'evaluation_failed': self.status.evaluation_failed,
                'next_reset': self.status.daily_reset_time,
            }
        }
    
    def calculate_position_size(self, account_balance: float, stop_loss_percent: float) -> float:
        """Calculate position size based on risk management rules"""
        # Check if we should reduce size
        size_multiplier = 0.5 if self._should_reduce_size() else 1.0
        
        # Calculate based on risk per trade
        risk_amount = account_balance * (self.config.risk_per_trade_percent / 100) * size_multiplier
        position_size = risk_amount / (stop_loss_percent / 100)
        
        return min(position_size, account_balance * self.config.max_leverage_btc_eth)


def main():
    """Test the prop firm manager"""
    manager = PropFirmManager()
    
    # Get initial status
    print("Initial Status:")
    print(json.dumps(manager.get_status_report(), indent=2))
    
    # Test trade validation
    can_trade, message = manager.can_open_trade(
        symbol="BTC",
        position_size=30000,  # 3x leverage on 10k
        stop_loss_amount=150   # 1.5% risk
    )
    print(f"\nCan open trade: {can_trade}")
    print(f"Message: {message}")
    
    # Simulate a winning trade
    manager.update_balance(10150)  # +$150 profit
    print("\nAfter winning trade:")
    print(json.dumps(manager.get_status_report(), indent=2))
    
    # Simulate a losing trade
    manager.update_balance(10050)  # -$100 loss
    print("\nAfter losing trade:")
    print(json.dumps(manager.get_status_report(), indent=2))


if __name__ == "__main__":
    main()