"""
Prop Firm Demo Account Tracker
Simulates trading the accepted signals to track challenge progress
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import asyncio
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropFirmDemoTracker:
    """Tracks demo account performance for prop firm challenge"""
    
    def __init__(self, db_path: str = "trade_log.db"):
        self.db_path = db_path
        self.initial_balance = 10000
        self.profit_target = 1000  # 10% of $10k
        self.max_daily_loss = 500  # 5% of $10k  
        self.max_drawdown = 600  # 6% of $10k
        
        # Telegram settings
        self.telegram_token = '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0'
        self.telegram_chat_id = '6585156851'
        
        self._ensure_demo_tables()
        
    def _ensure_demo_tables(self):
        """Create demo account tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Demo trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_demo_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    entry_time DATETIME,
                    exit_time DATETIME,
                    status TEXT,  -- 'OPEN', 'WIN', 'LOSS', 'BREAKEVEN'
                    pnl REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    running_balance REAL,
                    FOREIGN KEY (signal_id) REFERENCES signal_log (id)
                )
            """)
            
            # Demo account status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_demo_status (
                    id INTEGER PRIMARY KEY,
                    current_balance REAL DEFAULT 10000,
                    starting_balance REAL DEFAULT 10000,
                    peak_balance REAL DEFAULT 10000,
                    lowest_balance REAL DEFAULT 10000,
                    daily_starting_balance REAL DEFAULT 10000,
                    daily_pnl REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    max_drawdown_amount REAL DEFAULT 0,
                    max_drawdown_pct REAL DEFAULT 0,
                    daily_loss_amount REAL DEFAULT 0,
                    daily_loss_pct REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    challenge_status TEXT DEFAULT 'ACTIVE',  -- 'ACTIVE', 'PASSED', 'FAILED'
                    challenge_start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    challenge_end_date DATETIME,
                    last_trade_date DATETIME,
                    last_reset_date DATE DEFAULT CURRENT_DATE
                )
            """)
            
            # Insert initial status if doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO prop_demo_status (id, current_balance)
                VALUES (1, 10000)
            """)
            
            # Trade history for analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_demo_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    starting_balance REAL,
                    ending_balance REAL,
                    daily_pnl REAL,
                    daily_pnl_pct REAL,
                    trades_taken INTEGER,
                    winning_trades INTEGER,
                    max_drawdown REAL,
                    notes TEXT
                )
            """)
            
            conn.commit()
    
    def simulate_trade_execution(self, signal_data: Dict) -> Tuple[bool, str, Dict]:
        """Simulate executing an accepted trade"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current account status
                cursor.execute("SELECT * FROM prop_demo_status WHERE id = 1")
                status = cursor.fetchone()
                
                if not status:
                    return False, "Demo account not initialized", {}
                
                current_balance = status[1]
                daily_starting = status[5]
                daily_pnl = status[6]
                challenge_status = status[17]
                
                # Check if challenge is still active
                if challenge_status != 'ACTIVE':
                    return False, f"Challenge already {challenge_status}", {}
                
                # Calculate position metrics
                symbol = signal_data['symbol']
                side = signal_data['side']
                entry = signal_data['entry_price']
                stop_loss = signal_data['stop_loss']
                take_profit = signal_data['take_profit']
                position_size = signal_data.get('position_size', 150)  # Default $150
                
                # Calculate risk
                if side == 'BUY':
                    risk_per_unit = entry - stop_loss
                    reward_per_unit = take_profit - entry
                else:
                    risk_per_unit = stop_loss - entry  
                    reward_per_unit = entry - take_profit
                
                units = position_size / entry
                max_loss = risk_per_unit * units
                max_profit = reward_per_unit * units
                
                # Check risk limits BEFORE taking trade
                potential_daily_loss = daily_pnl - max_loss
                if abs(potential_daily_loss) > self.max_daily_loss:
                    return False, f"Would exceed daily loss limit: ${abs(potential_daily_loss):.2f} > ${self.max_daily_loss}", {}
                
                # Insert trade as OPEN
                cursor.execute("""
                    INSERT INTO prop_demo_trades 
                    (signal_id, symbol, side, entry_price, stop_loss, take_profit,
                     position_size, entry_time, status, running_balance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (
                    signal_data.get('signal_id'),
                    symbol, side, entry, stop_loss, take_profit,
                    position_size, datetime.now(), current_balance
                ))
                
                trade_id = cursor.lastrowid
                
                # Return trade details
                return True, "Trade opened in demo account", {
                    'trade_id': trade_id,
                    'symbol': symbol,
                    'side': side,
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'max_risk': max_loss,
                    'max_reward': max_profit,
                    'current_balance': current_balance
                }
                
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            return False, str(e), {}
    
    def check_open_trades(self):
        """Check open trades against current prices and close if hit TP/SL"""
        # This would need real price data to work properly
        # For demo, we'll simulate based on historical win rate
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get open trades
            cursor.execute("""
                SELECT id, symbol, side, entry_price, stop_loss, take_profit, position_size
                FROM prop_demo_trades
                WHERE status = 'OPEN'
            """)
            
            open_trades = cursor.fetchall()
            
            for trade in open_trades:
                trade_id, symbol, side, entry, sl, tp, size = trade
                
                # Simulate outcome based on 65% win rate (from backtest)
                import random
                is_winner = random.random() < 0.65
                
                if is_winner:
                    exit_price = tp
                    status = 'WIN'
                else:
                    exit_price = sl
                    status = 'LOSS'
                
                # Calculate P&L
                if side == 'BUY':
                    pnl = (exit_price - entry) * (size / entry)
                else:
                    pnl = (entry - exit_price) * (size / entry)
                
                # Commission (0.05% each way)
                commission = size * 0.001  # 0.1% round trip
                net_pnl = pnl - commission
                
                # Update trade
                cursor.execute("""
                    UPDATE prop_demo_trades
                    SET exit_price = ?, exit_time = ?, status = ?, 
                        pnl = ?, commission = ?, net_pnl = ?
                    WHERE id = ?
                """, (exit_price, datetime.now(), status, pnl, commission, net_pnl, trade_id))
                
                # Update account status
                self._update_account_status(net_pnl, status == 'WIN')
                
                logger.info(f"Closed demo trade {trade_id}: {symbol} {status} P&L: ${net_pnl:.2f}")
    
    def _update_account_status(self, pnl: float, is_winner: bool):
        """Update demo account status after trade closes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute("SELECT * FROM prop_demo_status WHERE id = 1")
            status = list(cursor.fetchone())
            
            # Update balances
            old_balance = status[1]
            new_balance = old_balance + pnl
            status[1] = new_balance  # current_balance
            
            # Update peak/lowest
            status[3] = max(status[3], new_balance)  # peak_balance
            status[4] = min(status[4], new_balance)  # lowest_balance
            
            # Update daily P&L
            status[6] += pnl  # daily_pnl
            status[7] += pnl  # total_pnl
            
            # Update drawdown
            drawdown = status[3] - new_balance
            drawdown_pct = (drawdown / status[3]) * 100 if status[3] > 0 else 0
            status[8] = drawdown  # max_drawdown_amount
            status[9] = drawdown_pct  # max_drawdown_pct
            
            # Update daily loss
            daily_loss = status[5] - new_balance if new_balance < status[5] else 0
            daily_loss_pct = (daily_loss / status[5]) * 100 if status[5] > 0 else 0
            status[10] = daily_loss  # daily_loss_amount
            status[11] = daily_loss_pct  # daily_loss_pct
            
            # Update trade stats
            status[12] += 1  # total_trades
            if is_winner:
                status[13] += 1  # winning_trades
            else:
                status[14] += 1  # losing_trades
            
            status[15] = (status[13] / status[12] * 100) if status[12] > 0 else 0  # win_rate
            
            # Check challenge status
            if new_balance >= self.initial_balance + self.profit_target:
                status[17] = 'PASSED'
                status[18] = datetime.now()
                self._send_challenge_passed_alert(new_balance, status[12])
            elif daily_loss > self.max_daily_loss:
                status[17] = 'FAILED'
                status[18] = datetime.now()
                self._send_challenge_failed_alert('Daily loss limit exceeded', daily_loss)
            elif drawdown > self.max_drawdown:
                status[17] = 'FAILED'
                status[18] = datetime.now()
                self._send_challenge_failed_alert('Maximum drawdown exceeded', drawdown)
            
            status[19] = datetime.now()  # last_trade_date
            
            # Update database
            cursor.execute("""
                UPDATE prop_demo_status
                SET current_balance = ?, peak_balance = ?, lowest_balance = ?,
                    daily_pnl = ?, total_pnl = ?, max_drawdown_amount = ?,
                    max_drawdown_pct = ?, daily_loss_amount = ?, daily_loss_pct = ?,
                    total_trades = ?, winning_trades = ?, losing_trades = ?,
                    win_rate = ?, challenge_status = ?, challenge_end_date = ?,
                    last_trade_date = ?
                WHERE id = 1
            """, tuple(status[1:17]) + (status[18], status[19]))
            
            conn.commit()
    
    def _send_challenge_passed_alert(self, final_balance: float, total_trades: int):
        """Send alert when challenge is passed"""
        message = f"""
🎉🎉🎉 PROP FIRM CHALLENGE PASSED! 🎉🎉🎉

✅ Target Achieved: ${self.profit_target:.0f} profit
💰 Final Balance: ${final_balance:.2f}
📈 Total Return: {((final_balance - self.initial_balance) / self.initial_balance * 100):.1f}%
📊 Trades Taken: {total_trades}

🏆 CONGRATULATIONS! Demo account has passed the evaluation!

Next Steps:
1. Review trading history
2. Prepare for live funded account
3. Maintain disciplined risk management
"""
        self._send_telegram_alert(message)
        logger.info(f"CHALLENGE PASSED! Balance: ${final_balance:.2f}")
    
    def _send_challenge_failed_alert(self, reason: str, amount: float):
        """Send alert when challenge fails"""
        message = f"""
❌ PROP FIRM CHALLENGE FAILED ❌

Reason: {reason}
Amount: ${amount:.2f}

The demo account has breached risk limits.
Review trades and risk management before retrying.
"""
        self._send_telegram_alert(message)
        logger.warning(f"CHALLENGE FAILED: {reason} - ${amount:.2f}")
    
    def _send_telegram_alert(self, message: str):
        """Send Telegram alert"""
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=data)
            if response.status_code == 200:
                logger.info("Alert sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def reset_daily_stats(self):
        """Reset daily statistics at day change"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Save today's history
            cursor.execute("""
                INSERT INTO prop_demo_history 
                (date, starting_balance, ending_balance, daily_pnl, daily_pnl_pct, 
                 trades_taken, winning_trades, max_drawdown)
                SELECT 
                    DATE('now'),
                    daily_starting_balance,
                    current_balance,
                    daily_pnl,
                    (daily_pnl / daily_starting_balance * 100),
                    (SELECT COUNT(*) FROM prop_demo_trades WHERE DATE(entry_time) = DATE('now')),
                    (SELECT COUNT(*) FROM prop_demo_trades WHERE DATE(entry_time) = DATE('now') AND status = 'WIN'),
                    max_drawdown_amount
                FROM prop_demo_status WHERE id = 1
            """)
            
            # Reset daily stats
            cursor.execute("""
                UPDATE prop_demo_status
                SET daily_starting_balance = current_balance,
                    daily_pnl = 0,
                    daily_loss_amount = 0,
                    daily_loss_pct = 0,
                    last_reset_date = DATE('now')
                WHERE id = 1
            """)
            
            conn.commit()
            logger.info("Daily stats reset")
    
    def get_demo_status(self) -> Dict:
        """Get current demo account status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM prop_demo_status WHERE id = 1")
            row = cursor.fetchone()
            
            if row:
                return {
                    'balance': row[1],
                    'total_pnl': row[7],
                    'daily_pnl': row[6],
                    'drawdown': row[8],
                    'drawdown_pct': row[9],
                    'daily_loss': row[10],
                    'daily_loss_pct': row[11],
                    'total_trades': row[12],
                    'win_rate': row[15],
                    'challenge_status': row[17],
                    'progress_to_target': (row[7] / self.profit_target * 100) if row[7] > 0 else 0
                }
            return {}

# Integration function for automation
def process_accepted_signal(signal_data: Dict):
    """Process an accepted signal in demo account"""
    tracker = PropFirmDemoTracker()
    success, message, trade_data = tracker.simulate_trade_execution(signal_data)
    
    if success:
        logger.info(f"Demo trade opened: {trade_data}")
        # Simulate checking for closes after some time
        # In production, this would check real prices
        asyncio.create_task(check_trades_after_delay(tracker))
    else:
        logger.warning(f"Demo trade rejected: {message}")
    
    return success, message

async def check_trades_after_delay(tracker: PropFirmDemoTracker):
    """Check trades after a delay (simulating market movement)"""
    await asyncio.sleep(300)  # Check after 5 minutes
    tracker.check_open_trades()

if __name__ == "__main__":
    # Test the demo tracker
    tracker = PropFirmDemoTracker()
    
    # Test with a sample signal
    test_signal = {
        'signal_id': 999,
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 45000,
        'stop_loss': 44500,
        'take_profit': 46500,
        'position_size': 150
    }
    
    success, message, data = tracker.simulate_trade_execution(test_signal)
    print(f"Test trade: {message}")
    
    if success:
        print(f"Trade data: {data}")
        
    # Check status
    status = tracker.get_demo_status()
    print(f"\nDemo Account Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")