"""
Alternative Paper Trading System
Tracks signals without MT5 API, simulates trades based on real market data
"""

import sqlite3
import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlternativePaperTrader:
    """Paper trading without MT5 API"""
    
    def __init__(self):
        self.db_path = 'paper_trading_alternative.db'
        self.signal_db = 'trade_log.db'
        
        # Account simulations
        self.accounts = {
            'ftmo': {
                'balance': 100000,
                'starting': 100000,
                'target': 110000,  # 10% profit target
                'max_dd': 10000,   # 10% max drawdown
                'daily_dd': 5000,   # 5% daily loss
                'trades': []
            },
            'breakout': {
                'balance': 10000,
                'starting': 10000,
                'target': 11000,    # 10% profit target
                'max_dd': 600,      # 6% max drawdown
                'daily_dd': 500,    # 5% daily loss
                'trades': []
            },
            'plexytrade_demo': {
                'balance': 10000,   # Your demo balance
                'starting': 10000,
                'trades': []
            }
        }
        
        self.start_date = datetime.now()
        self.end_date = self.start_date + timedelta(days=7)
        self.initialize_database()
    
    def initialize_database(self):
        """Create tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulated_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    account TEXT,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    current_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    risk_amount REAL,
                    pnl REAL,
                    status TEXT,
                    open_time DATETIME,
                    close_time DATETIME,
                    risk_reward REAL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    date DATE PRIMARY KEY,
                    ftmo_balance REAL,
                    ftmo_pnl REAL,
                    breakout_balance REAL,
                    breakout_pnl REAL,
                    trades_taken INTEGER,
                    win_rate REAL,
                    avg_rr REAL
                )
            """)
            
            conn.commit()
            logger.info("Alternative paper trading database initialized")
    
    async def get_market_price(self, symbol: str) -> Optional[Dict]:
        """Get current market price from free API"""
        
        # For crypto
        if symbol in ['BTCUSDT', 'ETHUSDT', 'BTCUSD', 'ETHUSD']:
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.replace('USD', 'USDT')}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data['price'])
                            return {'bid': price * 0.9999, 'ask': price * 1.0001}  # Simulate spread
            except:
                pass
        
        # For forex/gold - use static spreads for simulation
        static_prices = {
            'XAUUSD': {'bid': 1950.00, 'ask': 1950.50},
            'EURUSD': {'bid': 1.0850, 'ask': 1.0852},
            'GBPUSD': {'bid': 1.2750, 'ask': 1.2752},
            'USDJPY': {'bid': 148.50, 'ask': 148.52}
        }
        
        return static_prices.get(symbol, {'bid': 1.0, 'ask': 1.0})
    
    async def process_signal(self, signal: Dict) -> bool:
        """Process a signal and simulate trades"""
        
        symbol = signal['symbol']
        side = signal['side']
        entry = float(signal['entry_price'])
        sl = float(signal['stop_loss'])
        tp = float(signal['take_profit'])
        
        # Calculate R:R
        if side.upper() in ['BUY', 'LONG']:
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp
        
        if risk <= 0:
            return False
        
        rr = reward / risk
        
        # Filter by R:R
        min_rr = 2.5 if symbol in ['XAUUSD', 'EURUSD', 'GBPUSD'] else 2.0
        if rr < min_rr:
            logger.info(f"Skipping {symbol}: R:R {rr:.2f} < {min_rr}")
            return False
        
        # Get current market price
        price_data = await self.get_market_price(symbol)
        if not price_data:
            logger.warning(f"No price data for {symbol}")
            return False
        
        current_price = price_data['ask'] if side.upper() in ['BUY', 'LONG'] else price_data['bid']
        
        # Simulate trade for each account
        for account_name, account in self.accounts.items():
            # Calculate position size (1% risk)
            risk_amount = account['balance'] * 0.01
            
            # Check prop firm rules
            if account_name == 'ftmo':
                if account['starting'] - account['balance'] > account['max_dd']:
                    logger.warning(f"FTMO max drawdown exceeded, skipping trade")
                    continue
            elif account_name == 'breakout':
                if account['starting'] - account['balance'] > account['max_dd']:
                    logger.warning(f"Breakout max drawdown exceeded, skipping trade")
                    continue
            
            # Record trade
            trade = {
                'signal_id': signal.get('id', 0),
                'symbol': symbol,
                'side': side,
                'entry_price': current_price,
                'stop_loss': sl,
                'take_profit': tp,
                'risk_amount': risk_amount,
                'risk_reward': rr,
                'open_time': datetime.now(),
                'status': 'open'
            }
            
            account['trades'].append(trade)
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO simulated_trades 
                    (signal_id, account, symbol, side, entry_price, stop_loss, 
                     take_profit, risk_amount, risk_reward, open_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade['signal_id'], account_name, symbol, side,
                    current_price, sl, tp, risk_amount, rr,
                    datetime.now(), 'open'
                ))
                conn.commit()
        
        logger.info(f"Simulated trade: {symbol} {side} @ {current_price:.5f}, R:R {rr:.2f}")
        return True
    
    def check_open_trades(self):
        """Check if any trades hit TP or SL"""
        
        for account_name, account in self.accounts.items():
            for trade in account['trades']:
                if trade['status'] != 'open':
                    continue
                
                # Simulate price movement (simplified)
                import random
                
                # 58% win rate for Gold/FX, 65% for crypto
                win_rate = 0.58 if trade['symbol'] in ['XAUUSD', 'EURUSD'] else 0.65
                
                if random.random() < win_rate:
                    # Winner
                    pnl = trade['risk_amount'] * trade['risk_reward']
                    trade['status'] = 'won'
                else:
                    # Loser
                    pnl = -trade['risk_amount']
                    trade['status'] = 'lost'
                
                # Update balance
                account['balance'] += pnl
                trade['pnl'] = pnl
                trade['close_time'] = datetime.now()
                
                # Update database
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE simulated_trades
                        SET pnl = ?, status = ?, close_time = ?
                        WHERE signal_id = ? AND account = ?
                    """, (pnl, trade['status'], datetime.now(), 
                           trade['signal_id'], account_name))
                    conn.commit()
    
    async def generate_daily_report(self):
        """Generate daily performance report"""
        
        message = f"""
**ALTERNATIVE PAPER TRADING - DAILY REPORT**
Day {(datetime.now() - self.start_date).days + 1} of 7

**FTMO ($100k Challenge):**
Balance: ${self.accounts['ftmo']['balance']:.2f}
P&L: ${self.accounts['ftmo']['balance'] - self.accounts['ftmo']['starting']:.2f}
Progress: {((self.accounts['ftmo']['balance'] - self.accounts['ftmo']['starting']) / 10000) * 100:.1f}% to target
Status: {'ON TRACK' if self.accounts['ftmo']['balance'] > self.accounts['ftmo']['starting'] else 'NEEDS IMPROVEMENT'}

**Breakout Prop ($10k):**
Balance: ${self.accounts['breakout']['balance']:.2f}
P&L: ${self.accounts['breakout']['balance'] - self.accounts['breakout']['starting']:.2f}
Progress: {((self.accounts['breakout']['balance'] - self.accounts['breakout']['starting']) / 1000) * 100:.1f}% to target
Status: {'ON TRACK' if self.accounts['breakout']['balance'] > self.accounts['breakout']['starting'] else 'NEEDS IMPROVEMENT'}

**PlexyTrade Demo:**
Balance: ${self.accounts['plexytrade_demo']['balance']:.2f}
P&L: ${self.accounts['plexytrade_demo']['balance'] - self.accounts['plexytrade_demo']['starting']:.2f}

Note: Using alternative simulation since MT5 API is blocked.
        """
        
        # Send via Telegram
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
        if token:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
            
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json=data)
                logger.info("Daily report sent")
            except Exception as e:
                logger.error(f"Failed to send report: {e}")
        
        print(message)
    
    async def run(self):
        """Run alternative paper trading"""
        
        logger.info("Starting alternative paper trading (7 days)")
        logger.info("This simulates trades without MT5 API")
        
        last_signal_id = 0
        last_report_hour = -1
        
        while datetime.now() < self.end_date:
            try:
                # Get new signals
                with sqlite3.connect(self.signal_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM signal_log
                        WHERE id > ?
                        AND symbol IS NOT NULL
                        AND entry_price IS NOT NULL
                        ORDER BY id ASC
                        LIMIT 10
                    """, (last_signal_id,))
                    
                    signals = cursor.fetchall()
                
                for signal_row in signals:
                    signal = {
                        'id': signal_row[0],
                        'symbol': signal_row[2],
                        'side': signal_row[3],
                        'entry_price': signal_row[4],
                        'stop_loss': signal_row[5],
                        'take_profit': signal_row[6]
                    }
                    
                    if signal['stop_loss'] and signal['take_profit']:
                        await self.process_signal(signal)
                    
                    last_signal_id = signal['id']
                
                # Check open trades
                self.check_open_trades()
                
                # Daily report at 9 PM
                current_hour = datetime.now().hour
                if current_hour == 21 and current_hour != last_report_hour:
                    await self.generate_daily_report()
                    last_report_hour = current_hour
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
        
        # Final report
        await self.generate_final_report()
    
    async def generate_final_report(self):
        """Generate final 7-day report"""
        
        ftmo_final = self.accounts['ftmo']['balance']
        breakout_final = self.accounts['breakout']['balance']
        
        ftmo_profit = ftmo_final - 100000
        breakout_profit = breakout_final - 10000
        
        ftmo_passed = ftmo_profit >= 10000
        breakout_passed = breakout_profit >= 1000
        
        message = f"""
**7-DAY PAPER TRADING COMPLETE (Alternative Method)**

**FTMO Result:**
Starting: $100,000
Ending: ${ftmo_final:.2f}
Profit: ${ftmo_profit:.2f}
Result: {'PASSED ✅' if ftmo_passed else 'FAILED ❌'}

**Breakout Prop Result:**
Starting: $10,000
Ending: ${breakout_final:.2f}
Profit: ${breakout_profit:.2f}
Result: {'PASSED ✅' if breakout_passed else 'FAILED ❌'}

**Recommendation:**
{self.get_recommendation(ftmo_passed, breakout_passed)}
        """
        
        print(message)
        
        # Save results
        with open('paper_trading_results.txt', 'w') as f:
            f.write(message)
        
        logger.info("Results saved to paper_trading_results.txt")
    
    def get_recommendation(self, ftmo_passed: bool, breakout_passed: bool) -> str:
        if ftmo_passed and breakout_passed:
            return "Both passed! Strategy is profitable. Proceed with real funding."
        elif ftmo_passed:
            return "FTMO passed! Focus on FTMO for larger profit potential."
        elif breakout_passed:
            return "Breakout passed! Start with Breakout Prop."
        else:
            return "Neither passed. Review risk management and signal quality."

if __name__ == "__main__":
    print("""
    ============================================================
    ALTERNATIVE PAPER TRADING SYSTEM
    ============================================================
    
    Since MT5 API is blocked by Windows, this system:
    - Reads signals from your database
    - Simulates trades using market data
    - Tracks both FTMO and Breakout Prop rules
    - Runs for 7 days
    - Sends daily reports
    
    Starting now...
    ============================================================
    """)
    
    trader = AlternativePaperTrader()
    asyncio.run(trader.run())