"""
MT5 Paper Trading Verification System
Tracks real signals on demo account to verify prop firm profitability
Runs for 1 week to prove the strategy works
"""

import MetaTrader5 as mt5
import sqlite3
import json
import logging
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PaperTrade:
    """Paper trade record"""
    signal_id: int
    mt5_ticket: int
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_amount: float
    risk_reward: float
    open_time: datetime
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str = 'open'
    prop_firm_rules: Dict = None

class MT5PaperTrader:
    """Paper trading system with MT5 demo account"""
    
    def __init__(self, account: int, password: str, server: str):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        
        # Database for tracking
        self.db_path = 'paper_trading_verification.db'
        self.signal_db = 'trade_log.db'  # Your existing signals
        
        # Prop firm simulations
        self.ftmo_balance = 100000
        self.breakout_balance = 10000
        self.ftmo_starting = 100000
        self.breakout_starting = 10000
        
        # Tracking
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(days=7)
        self.trades = []
        self.daily_stats = {}
        
        # Initialize
        self.initialize_database()
        self.connect_mt5()
    
    def initialize_database(self):
        """Create tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Main trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    mt5_ticket INTEGER,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    lot_size REAL,
                    risk_amount REAL,
                    risk_reward REAL,
                    open_time DATETIME,
                    close_time DATETIME,
                    close_price REAL,
                    pnl REAL,
                    ftmo_pnl REAL,
                    breakout_pnl REAL,
                    status TEXT,
                    notes TEXT
                )
            """)
            
            # Daily performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    date DATE PRIMARY KEY,
                    trades_taken INTEGER,
                    winners INTEGER,
                    losers INTEGER,
                    total_pnl REAL,
                    ftmo_balance REAL,
                    breakout_balance REAL,
                    ftmo_daily_dd REAL,
                    breakout_daily_dd REAL,
                    win_rate REAL,
                    avg_rr REAL,
                    violations TEXT
                )
            """)
            
            # Prop firm tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_firm_simulation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    firm TEXT,
                    balance REAL,
                    equity REAL,
                    daily_pnl REAL,
                    total_pnl REAL,
                    max_drawdown REAL,
                    daily_drawdown REAL,
                    trades_count INTEGER,
                    status TEXT,
                    violations TEXT
                )
            """)
            
            conn.commit()
            logger.info("Paper trading database initialized")
    
    def connect_mt5(self) -> bool:
        """Connect to MT5 demo account"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Login
            authorized = mt5.login(
                login=self.account,
                password=self.password,
                server=self.server
            )
            
            if not authorized:
                logger.error(f"Failed to login to {self.account}: {mt5.last_error()}")
                return False
            
            self.connected = True
            account_info = mt5.account_info()
            
            logger.info(f"Connected to MT5 Demo Account {self.account}")
            logger.info(f"Balance: ${account_info.balance:.2f}")
            logger.info(f"Server: {self.server}")
            logger.info(f"Company: {account_info.company}")
            
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    def calculate_lot_size(self, symbol: str, risk_pct: float, stop_loss_points: float) -> float:
        """Calculate appropriate lot size"""
        
        # Get account info
        account = mt5.account_info()
        if not account:
            return 0.01
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.warning(f"Symbol {symbol} not found")
            return 0.01
        
        # Calculate risk amount
        risk_amount = account.balance * risk_pct
        
        # Calculate lot size
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        
        if stop_loss_points > 0 and tick_value > 0:
            # Points to ticks
            ticks = stop_loss_points / tick_size
            # Lot size calculation
            lots = risk_amount / (ticks * tick_value)
            
            # Round to lot step
            lot_step = symbol_info.volume_step
            lots = round(lots / lot_step) * lot_step
            
            # Apply limits
            lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
            
            return lots
        
        return symbol_info.volume_min
    
    async def process_signal(self, signal: Dict) -> Optional[PaperTrade]:
        """Process a signal and place paper trade"""
        
        if not self.connected:
            logger.error("Not connected to MT5")
            return None
        
        try:
            symbol = signal['symbol']
            
            # Convert crypto symbols if needed
            if 'USDT' in symbol:
                symbol = symbol.replace('USDT', 'USD')
            
            # Ensure symbol is available
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Symbol {symbol} not available")
                return None
            
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None
            
            # Determine side and entry price
            if signal['side'].upper() in ['BUY', 'LONG']:
                order_type = mt5.ORDER_TYPE_BUY
                entry_price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                entry_price = tick.bid
            
            # Calculate risk metrics
            if signal['side'].upper() in ['BUY', 'LONG']:
                sl_points = abs(entry_price - signal['stop_loss'])
                tp_points = abs(signal['take_profit'] - entry_price)
            else:
                sl_points = abs(signal['stop_loss'] - entry_price)
                tp_points = abs(entry_price - signal['take_profit'])
            
            risk_reward = tp_points / sl_points if sl_points > 0 else 0
            
            # Skip low R:R trades
            min_rr = 2.5 if symbol in ['XAUUSD', 'EURUSD', 'GBPUSD'] else 2.0
            if risk_reward < min_rr:
                logger.info(f"Skipping {symbol}: R:R {risk_reward:.2f} < {min_rr}")
                return None
            
            # Calculate lot size (1% risk)
            lots = self.calculate_lot_size(symbol, 0.01, sl_points)
            
            # Place order on MT5
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lots,
                "type": order_type,
                "price": entry_price,
                "sl": signal['stop_loss'],
                "tp": signal['take_profit'],
                "deviation": 20,
                "magic": 777,  # Paper trading magic number
                "comment": f"Paper Signal #{signal.get('id', 0)}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                # Check if market is closed
                if result and "Market" in str(result.comment) and "closed" in str(result.comment):
                    logger.warning(f"Market closed for {symbol} - will retry when market opens")
                    # Mark signal as unprocessed so it gets retried
                    return None
                else:
                    logger.error(f"Order failed: {result.comment}")
                return None
            
            # Calculate risk amounts for prop firms
            symbol_info = mt5.symbol_info(symbol)
            tick_value = symbol_info.trade_tick_value
            risk_amount = sl_points * lots * tick_value
            
            # Create paper trade record
            trade = PaperTrade(
                signal_id=signal.get('id', 0),
                mt5_ticket=result.order,
                symbol=symbol,
                side=signal['side'],
                entry_price=entry_price,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                lot_size=lots,
                risk_amount=risk_amount,
                risk_reward=risk_reward,
                open_time=datetime.now(),
                prop_firm_rules={
                    'ftmo_risk': self.ftmo_balance * 0.01,
                    'breakout_risk': self.breakout_balance * 0.01
                }
            )
            
            # Save to database
            self.save_trade(trade)
            
            # Log success
            logger.info(f"Paper trade opened: {symbol} {signal['side']} @ {entry_price:.5f}")
            logger.info(f"  Lots: {lots}, R:R: {risk_reward:.2f}, Risk: ${risk_amount:.2f}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return None
    
    def save_trade(self, trade: PaperTrade):
        """Save trade to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO paper_trades 
                (signal_id, mt5_ticket, symbol, side, entry_price, stop_loss, 
                 take_profit, lot_size, risk_amount, risk_reward, open_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.signal_id, trade.mt5_ticket, trade.symbol, trade.side,
                trade.entry_price, trade.stop_loss, trade.take_profit,
                trade.lot_size, trade.risk_amount, trade.risk_reward,
                trade.open_time, trade.status
            ))
            conn.commit()
    
    def check_open_positions(self):
        """Check and update open positions"""
        
        if not self.connected:
            return
        
        positions = mt5.positions_get(magic=777)
        if not positions:
            return
        
        for position in positions:
            # Check if hit TP or SL
            current_price = position.price_current
            pnl = position.profit
            
            # Update database if closed
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if position should be closed
                if position.type == 0:  # Buy
                    if current_price <= position.sl or current_price >= position.tp:
                        self.close_position(position.ticket, pnl)
                else:  # Sell
                    if current_price >= position.sl or current_price <= position.tp:
                        self.close_position(position.ticket, pnl)
    
    def close_position(self, ticket: int, pnl: float):
        """Close position and update records"""
        
        # Close on MT5
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return
        
        position = position[0]
        symbol_info = mt5.symbol_info_tick(position.symbol)
        
        # Determine close request
        if position.type == 0:  # Buy
            price = symbol_info.bid
            close_type = mt5.ORDER_TYPE_SELL
        else:
            price = symbol_info.ask
            close_type = mt5.ORDER_TYPE_BUY
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": 777,
            "comment": "Paper close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate prop firm impacts
                ftmo_pnl = pnl * (self.ftmo_balance / mt5.account_info().balance)
                breakout_pnl = pnl * (self.breakout_balance / mt5.account_info().balance)
                
                cursor.execute("""
                    UPDATE paper_trades
                    SET close_time = ?, close_price = ?, pnl = ?,
                        ftmo_pnl = ?, breakout_pnl = ?, status = 'closed'
                    WHERE mt5_ticket = ?
                """, (datetime.now(), price, pnl, ftmo_pnl, breakout_pnl, ticket))
                
                # Update balances
                self.ftmo_balance += ftmo_pnl
                self.breakout_balance += breakout_pnl
                
                conn.commit()
                
                logger.info(f"Position {ticket} closed: PnL ${pnl:.2f}")
    
    def check_prop_firm_rules(self):
        """Check if violating any prop firm rules"""
        
        violations = []
        
        # FTMO Rules Check
        ftmo_daily_loss = self.ftmo_starting - self.ftmo_balance
        if ftmo_daily_loss > 5000:  # 5% daily loss
            violations.append("FTMO: Daily loss limit exceeded")
        
        ftmo_total_dd = self.ftmo_starting - self.ftmo_balance
        if ftmo_total_dd > 10000:  # 10% max drawdown
            violations.append("FTMO: Maximum drawdown exceeded")
        
        # Breakout Prop Rules Check
        breakout_daily_loss = self.breakout_starting - self.breakout_balance
        if breakout_daily_loss > 500:  # 5% daily loss
            violations.append("Breakout: Daily loss limit exceeded")
        
        breakout_total_dd = self.breakout_starting - self.breakout_balance
        if breakout_total_dd > 600:  # 6% max drawdown
            violations.append("Breakout: Maximum drawdown exceeded")
        
        return violations
    
    async def generate_daily_report(self):
        """Generate daily performance report"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get today's trades
            cursor.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                       SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                       SUM(pnl) as total_pnl,
                       AVG(risk_reward) as avg_rr
                FROM paper_trades
                WHERE DATE(close_time) = DATE('now')
                AND status = 'closed'
            """)
            
            stats = cursor.fetchone()
            
            if stats[0] > 0:
                win_rate = (stats[1] / stats[0]) * 100 if stats[0] > 0 else 0
                
                message = f"""
**PAPER TRADING DAILY REPORT**
Day {(datetime.now() - self.start_time).days + 1} of 7

**Today's Performance:**
Trades: {stats[0]}
Winners: {stats[1]}
Losers: {stats[2]}
Win Rate: {win_rate:.1f}%
Avg R:R: {stats[4]:.2f}
Total PnL: ${stats[3]:.2f}

**Prop Firm Simulations:**

FTMO ($100k):
Balance: ${self.ftmo_balance:.2f}
P&L: ${self.ftmo_balance - self.ftmo_starting:.2f}
Progress: {((self.ftmo_balance - self.ftmo_starting) / 10000) * 100:.1f}% to target

Breakout ($10k):
Balance: ${self.breakout_balance:.2f}
P&L: ${self.breakout_balance - self.breakout_starting:.2f}
Progress: {((self.breakout_balance - self.breakout_starting) / 1000) * 100:.1f}% to target

**Rule Violations:** {self.check_prop_firm_rules() or 'None'}
                """
                
                await self.send_telegram_report(message)
    
    async def send_telegram_report(self, message: str):
        """Send report via Telegram"""
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=data)
        except Exception as e:
            logger.error(f"Failed to send report: {e}")
    
    async def run_paper_trading(self):
        """Main paper trading loop"""
        
        logger.info(f"Starting 7-day paper trading verification")
        logger.info(f"End time: {self.end_time}")
        
        last_signal_id = 0
        
        while datetime.now() < self.end_time:
            try:
                # Check for new signals
                with sqlite3.connect(self.signal_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM signal_log
                        WHERE id > ?
                        AND processed = 0
                        ORDER BY id ASC
                        LIMIT 5
                    """, (last_signal_id,))
                    
                    signals = cursor.fetchall()
                
                for signal_row in signals:
                    signal = {
                        'id': signal_row[0],
                        'symbol': signal_row[4],  # Column 4 is symbol
                        'side': signal_row[5],    # Column 5 is side
                        'entry_price': signal_row[6],  # Column 6 is entry_price
                        'stop_loss': signal_row[8],    # Column 8 is stop_loss
                        'take_profit': signal_row[7]   # Column 7 is take_profit
                    }
                    
                    # Process signal
                    trade = await self.process_signal(signal)
                    if trade:
                        self.trades.append(trade)
                    
                    last_signal_id = signal['id']
                
                # Check open positions
                self.check_open_positions()
                
                # Daily report at 9 PM
                if datetime.now().hour == 21 and datetime.now().minute == 0:
                    await self.generate_daily_report()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in paper trading loop: {e}")
                await asyncio.sleep(60)
        
        # Final report
        await self.generate_final_report()
    
    async def generate_final_report(self):
        """Generate final 7-day report"""
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("""
                SELECT * FROM paper_trades WHERE status = 'closed'
            """, conn)
        
        if len(df) > 0:
            total_trades = len(df)
            winners = len(df[df['pnl'] > 0])
            losers = len(df[df['pnl'] < 0])
            win_rate = (winners / total_trades) * 100
            avg_rr = df['risk_reward'].mean()
            total_pnl = df['pnl'].sum()
            
            ftmo_final = self.ftmo_balance
            breakout_final = self.breakout_balance
            ftmo_profit = ftmo_final - self.ftmo_starting
            breakout_profit = breakout_final - self.breakout_starting
            
            ftmo_passed = ftmo_profit >= 10000  # 10% target
            breakout_passed = breakout_profit >= 1000  # 10% target
            
            message = f"""
**7-DAY PAPER TRADING VERIFICATION COMPLETE**

**Overall Statistics:**
Total Trades: {total_trades}
Winners: {winners}
Losers: {losers}
Win Rate: {win_rate:.1f}%
Average R:R: {avg_rr:.2f}
Total P&L: ${total_pnl:.2f}

**PROP FIRM RESULTS:**

**FTMO Challenge ($100k):**
Starting: ${self.ftmo_starting:,.2f}
Ending: ${ftmo_final:,.2f}
Profit: ${ftmo_profit:,.2f}
Target: $10,000
Result: {'PASSED' if ftmo_passed else 'FAILED'}
{f'Would earn: ${ftmo_profit * 0.8:.2f}/month' if ftmo_passed else ''}

**Breakout Prop ($10k):**
Starting: ${self.breakout_starting:,.2f}
Ending: ${breakout_final:,.2f}
Profit: ${breakout_profit:,.2f}
Target: $1,000
Result: {'PASSED' if breakout_passed else 'FAILED'}
{f'Would earn: ${breakout_profit * 0.8:.2f}/month' if breakout_passed else ''}

**Violations:** {self.check_prop_firm_rules() or 'None'}

**RECOMMENDATION:**
{self.generate_recommendation(ftmo_passed, breakout_passed, win_rate, avg_rr)}
            """
            
            await self.send_telegram_report(message)
            
            # Save detailed report
            df.to_csv('paper_trading_results.csv', index=False)
            logger.info("Results saved to paper_trading_results.csv")
    
    def generate_recommendation(self, ftmo_passed: bool, breakout_passed: bool, 
                               win_rate: float, avg_rr: float) -> str:
        """Generate recommendation based on results"""
        
        if ftmo_passed and breakout_passed:
            return "Both challenges PASSED! Strategy is profitable. Proceed with real funding."
        elif ftmo_passed:
            return "FTMO passed! Focus on FTMO with larger account size."
        elif breakout_passed:
            return "Breakout passed! Consider starting with Breakout Prop."
        elif win_rate > 50 and avg_rr > 2.0:
            return "Close to passing. Fine-tune risk management and try again."
        else:
            return "Strategy needs improvement. Review signal quality and risk parameters."

if __name__ == "__main__":
    print("""
    ============================================================
    MT5 PAPER TRADING VERIFICATION SYSTEM
    ============================================================
    
    This will run for 7 days and track whether we would pass
    prop firm challenges with real signals.
    
    SETUP REQUIRED:
    1. Create MT5 demo account (free)
    2. Download MT5 from metatrader5.com
    3. Login to demo account
    4. Update credentials below
    
    DEMO ACCOUNT OPTIONS:
    - ICMarkets Demo
    - Pepperstone Demo
    - FBS Demo
    - Any broker offering MT5 demo
    
    ============================================================
    """)
    
    # Get credentials from user
    print("\nEnter your MT5 Demo Account credentials:")
    print("(Leave blank to skip for now)\n")
    
    account = input("Account Number: ").strip()
    password = input("Password: ").strip()
    server = input("Server (e.g., 'ICMarkets-Demo'): ").strip()
    
    if account and password and server:
        # Initialize paper trader
        trader = MT5PaperTrader(
            account=int(account),
            password=password,
            server=server
        )
        
        if trader.connected:
            print("\n[OK] Connected to MT5 Demo Account")
            print("[OK] Starting 7-day paper trading verification")
            print("[OK] Will track both FTMO and Breakout Prop rules")
            print("[OK] Daily reports will be sent at 9 PM")
            print("\nPaper trading started. Check back in 7 days for results.")
            
            # Run paper trading
            asyncio.run(trader.run_paper_trading())
        else:
            print("\n[ERROR] Failed to connect to MT5")
            print("Please check your credentials and try again")
    else:
        print("\nNo credentials provided. Please set up when ready.")
        print("\nTo get a demo account:")
        print("1. Visit any MT5 broker (ICMarkets, Pepperstone, etc.)")
        print("2. Sign up for free demo account")
        print("3. Download MT5 and login")
        print("4. Run this script again with credentials")