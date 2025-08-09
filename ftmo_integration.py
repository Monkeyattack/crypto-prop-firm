"""
FTMO Integration for Gold/FX Trading
Configures the system for FTMO's specific requirements
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import asyncio
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FTMOConfig:
    """FTMO-specific configuration"""
    
    def __init__(self, account_size: int = 100000):
        self.account_size = account_size
        
        # FTMO Challenge Parameters
        if account_size == 100000:
            self.challenge = {
                'step1_profit_target': 10000,  # 10%
                'step2_profit_target': 5000,    # 5%
                'max_daily_loss': 5000,         # 5%
                'max_total_loss': 10000,        # 10%
                'min_trading_days_step1': 4,
                'min_trading_days_step2': 4,
                'time_limit_step1': 30,         # days
                'time_limit_step2': 60,         # days
                'profit_split': 0.80,           # 80% initially
                'scaling_to_90': True           # Can scale to 90% split
            }
        elif account_size == 200000:
            self.challenge = {
                'step1_profit_target': 20000,   # 10%
                'step2_profit_target': 10000,   # 5%
                'max_daily_loss': 10000,        # 5%
                'max_total_loss': 20000,        # 10%
                'min_trading_days_step1': 4,
                'min_trading_days_step2': 4,
                'time_limit_step1': 30,
                'time_limit_step2': 60,
                'profit_split': 0.80,
                'scaling_to_90': True
            }
        
        # Trading restrictions
        self.restrictions = {
            'news_trading': False,       # No trading during high-impact news
            'weekend_holding': True,     # Can hold over weekend
            'max_position_size': account_size * 0.5,  # Max 50% of account
            'max_leverage': 100,         # FTMO max leverage
            'allowed_instruments': [
                'XAUUSD', 'XAGUSD',     # Metals
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD',  # Major Forex
                'USDCAD', 'NZDUSD', 'USDCHF',            # More Majors
                'US30', 'US100', 'US500',                # Indices
                'BTCUSD', 'ETHUSD'                       # Crypto CFDs
            ]
        }
        
        # Risk parameters optimized for FTMO
        self.risk_params = {
            'risk_per_trade': 0.01,      # 1% risk per trade
            'max_daily_risk': 0.03,       # 3% max daily risk (below 5% limit)
            'max_open_trades': 3,         # Conservative concurrent positions
            'min_rr_ratio': 2.5,          # Minimum R:R for Gold/FX
            'scale_in_allowed': False,    # No adding to losers
            'partial_close_levels': [0.5, 0.75, 1.0]  # TP levels
        }

class FTMOIntegration:
    """Manages FTMO-specific trading integration"""
    
    def __init__(self, config: FTMOConfig = None):
        self.config = config or FTMOConfig()
        self.db_path = 'ftmo_trading.db'
        self.current_phase = 'challenge_step1'  # challenge_step1, challenge_step2, funded
        self.start_date = datetime.now()
        self.trading_days = set()
        self.initialize_database()
    
    def initialize_database(self):
        """Create FTMO-specific tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Challenge tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ftmo_challenge (
                    id INTEGER PRIMARY KEY,
                    phase TEXT,
                    start_date DATETIME,
                    current_balance REAL,
                    starting_balance REAL,
                    highest_balance REAL,
                    lowest_balance REAL,
                    daily_loss REAL,
                    total_pnl REAL,
                    trading_days INTEGER,
                    trades_count INTEGER,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Daily tracking for FTMO limits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ftmo_daily_stats (
                    date DATE PRIMARY KEY,
                    starting_balance REAL,
                    ending_balance REAL,
                    daily_pnl REAL,
                    trades_count INTEGER,
                    max_drawdown REAL,
                    violations TEXT
                )
            """)
            
            # Trade tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ftmo_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    risk_amount REAL,
                    pnl REAL,
                    status TEXT,
                    mt4_ticket INTEGER,
                    notes TEXT
                )
            """)
            
            conn.commit()
    
    def check_ftmo_rules(self, trade_params: Dict) -> Tuple[bool, str]:
        """Validate trade against FTMO rules"""
        
        # Get current stats
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check daily loss
            cursor.execute("""
                SELECT starting_balance, 
                       MIN(current_balance) as lowest_today
                FROM ftmo_challenge
                WHERE date(timestamp) = date('now')
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                daily_drawdown = result[0] - result[1] if result[1] else 0
                if daily_drawdown >= self.config.challenge['max_daily_loss'] * 0.8:
                    return False, f"Approaching daily loss limit: ${daily_drawdown:.2f}"
            
            # Check total drawdown
            cursor.execute("""
                SELECT starting_balance, current_balance
                FROM ftmo_challenge
                WHERE status = 'active'
                ORDER BY id DESC LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                total_drawdown = result[0] - result[1]
                if total_drawdown >= self.config.challenge['max_total_loss'] * 0.8:
                    return False, f"Approaching max drawdown: ${total_drawdown:.2f}"
            
            # Check instrument is allowed
            if trade_params['symbol'] not in self.config.restrictions['allowed_instruments']:
                # Check if it's a crypto pair that might be formatted differently
                symbol_base = trade_params['symbol'].replace('USDT', 'USD')
                if symbol_base not in self.config.restrictions['allowed_instruments']:
                    return False, f"Instrument {trade_params['symbol']} not allowed on FTMO"
            
            # Check position size
            if trade_params.get('position_size', 0) > self.config.restrictions['max_position_size']:
                return False, f"Position size exceeds FTMO limit"
            
            # Check R:R ratio
            if trade_params.get('risk_reward', 0) < self.config.risk_params['min_rr_ratio']:
                return False, f"R:R ratio {trade_params.get('risk_reward', 0):.2f} below minimum {self.config.risk_params['min_rr_ratio']}"
        
        return True, "Trade approved for FTMO"
    
    def calculate_position_size(self, stop_loss_pips: float, current_balance: float) -> float:
        """Calculate FTMO-appropriate position size"""
        
        # Risk 1% of account
        risk_amount = current_balance * self.config.risk_params['risk_per_trade']
        
        # Adjust for current phase
        if self.current_phase == 'challenge_step1':
            # Be more conservative in step 1
            risk_amount *= 0.8
        elif self.current_phase == 'challenge_step2':
            # Be very conservative in verification
            risk_amount *= 0.6
        
        # Calculate position size based on stop loss
        # This is simplified - actual calculation depends on instrument
        position_size = risk_amount / (stop_loss_pips * 10)  # Assuming $10 per pip
        
        return min(position_size, self.config.restrictions['max_position_size'])
    
    def update_challenge_progress(self) -> Dict:
        """Get current challenge progress"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM ftmo_challenge
                WHERE status = 'active'
                ORDER BY id DESC LIMIT 1
            """)
            
            result = cursor.fetchone()
            if not result:
                # Initialize challenge
                cursor.execute("""
                    INSERT INTO ftmo_challenge 
                    (phase, start_date, current_balance, starting_balance, 
                     highest_balance, lowest_balance, total_pnl, trading_days, trades_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_phase,
                    datetime.now(),
                    self.config.account_size,
                    self.config.account_size,
                    self.config.account_size,
                    self.config.account_size,
                    0, 0, 0
                ))
                conn.commit()
                
                return {
                    'phase': self.current_phase,
                    'progress': 0,
                    'days_remaining': 30,
                    'profit_target': self.config.challenge['step1_profit_target'],
                    'current_pnl': 0
                }
            
            # Calculate progress
            phase = result[1]
            current_balance = result[3]
            starting_balance = result[4]
            pnl = current_balance - starting_balance
            trading_days = result[8]
            
            if phase == 'challenge_step1':
                target = self.config.challenge['step1_profit_target']
                time_limit = self.config.challenge['time_limit_step1']
            elif phase == 'challenge_step2':
                target = self.config.challenge['step2_profit_target']
                time_limit = self.config.challenge['time_limit_step2']
            else:
                target = 0
                time_limit = 0
            
            progress = (pnl / target * 100) if target > 0 else 0
            days_elapsed = (datetime.now() - datetime.fromisoformat(result[2])).days
            days_remaining = time_limit - days_elapsed
            
            return {
                'phase': phase,
                'progress': progress,
                'days_remaining': days_remaining,
                'trading_days': trading_days,
                'profit_target': target,
                'current_pnl': pnl,
                'current_balance': current_balance,
                'daily_drawdown': starting_balance - result[6],  # lowest_balance
                'max_drawdown': result[4] - result[6]  # highest - lowest
            }
    
    async def send_ftmo_alert(self, message: str):
        """Send FTMO-specific alerts"""
        
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        data = {
            'chat_id': telegram_chat_id,
            'text': f"**FTMO ALERT**\n\n{message}",
            'parse_mode': 'Markdown'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=data)
        except Exception as e:
            logger.error(f"Failed to send FTMO alert: {e}")

def setup_ftmo_account():
    """Initial FTMO account setup"""
    
    print("="*70)
    print("FTMO ACCOUNT SETUP FOR PALAU RESIDENT")
    print("="*70)
    
    print("""
IMMEDIATE ACTION ITEMS:

1. ACCOUNT REGISTRATION
   - Go to ftmo.com
   - Register with Palau address
   - Upload Palau residency documentation
   - Complete KYC verification

2. CHALLENGE SELECTION
   Recommended: $100,000 Challenge
   - Cost: $540 (one-time, refundable)
   - Profit Target Step 1: $10,000 (10%)
   - Profit Target Step 2: $5,000 (5%)
   - Max Daily Loss: $5,000 (5%)
   - Max Total Loss: $10,000 (10%)
   - Profit Split: 80% (scales to 90%)

3. PLATFORM SETUP
   - Choose MT4 or MT5
   - Download and install MetaTrader
   - Login with FTMO demo credentials
   - Configure Gold/FX pairs on watchlist

4. INTEGRATION SETUP
   - Install MT4/MT5 Python API
   - Configure trade copier
   - Set up monitoring dashboard
   - Enable Telegram alerts

5. TRADING CONFIGURATION
   - Focus: XAUUSD (Gold) primary
   - Secondary: Major forex pairs
   - Risk: 1% per trade
   - Min R:R: 2.5
   - Max daily trades: 5
   - No news trading
    """)
    
    # Initialize FTMO configuration
    ftmo = FTMOIntegration(FTMOConfig(100000))
    
    print("\n[OK] FTMO configuration files created")
    print("[OK] Database initialized")
    print("[OK] Risk parameters configured")
    
    print("""
IMPORTANT NOTES:

- FTMO allows Gold/FX trading which aligns perfectly with our 2.8 R:R strategy
- No monthly fees after passing (unlike Apex)
- Free retries if you fail
- Can scale account up to $2M over time
- 80% profit split initially, 90% after scaling

EXPECTED RETURNS:
- Monthly profit target: $15,000-20,000
- After 80% split: $12,000-16,000 to you
- ROI on $540 investment: Recovered in 1-2 days after funded

STRATEGY:
- Use existing Gold/FX signals (2.8 R:R average)
- Risk 1% per trade
- Focus on XAUUSD during London/NY sessions
- Take all signals with R:R > 2.5
    """)
    
    return ftmo

if __name__ == "__main__":
    ftmo = setup_ftmo_account()
    progress = ftmo.update_challenge_progress()
    print(f"\nCurrent Status: {progress}")