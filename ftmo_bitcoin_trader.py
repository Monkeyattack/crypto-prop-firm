"""
FTMO Bitcoin Trading System
Optimized for FTMO prop firm challenges using Bitcoin (BTCUSD)
Based on backtesting: 6.8% monthly returns, 0.4% max drawdown
"""

import MetaTrader5 as mt5
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ftmo_bitcoin.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FTMOBitcoin')

class FTMOBitcoinTrader:
    """Bitcoin-focused trading for FTMO prop firm challenges"""
    
    def __init__(self, account: int, password: str, server: str):
        # MT5 credentials
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        
        # Trading parameters with weekend risk management
        self.config = {
            'target_profit_pct': 5.0,      # Target 5% profit per trade
            'activation_pct': 4.0,          # Start trailing at 4.0% (optimized)
            'trail_distance_pct': 1.0,      # Trail by 1.0% (tighter)
            'min_profit_pct': 3.0,          # Min 3.0% to exit (40.6% better performance)
            'stop_loss_pct': 2.0,           # 2% stop loss (Mon-Wed)
            'stop_loss_pct_weekend': 2.5,   # 2.5% stop loss (Thu-Fri)
            'stop_loss_pct_event': 3.0,     # 3% stop loss (major events)
            'risk_per_trade': 0.01,         # 1% risk per trade
            'max_positions': 2,             # Max 2 concurrent positions
            'max_positions_weekend': 1,     # Max 1 position over weekends
            'min_momentum_pct': 0.3,        # Lower threshold for BTC (was 0.5)
            'timeframe': mt5.TIMEFRAME_M15, # 15-min for better signals
            'friday_profit_close': 3.0,     # Close if >3% profit on Friday
        }
        
        # FTMO-specific rules (scaled to our $50k demo)
        self.ftmo_rules = {
            'demo_account_size': 50000,     # Our demo account
            'ftmo_account_size': 100000,    # FTMO $100k challenge
            'phase1': {
                'duration_days': None,       # No time limit!
                'profit_target': 5000,       # 10% of $50k demo
                'max_drawdown': 5000,        # 10% of $50k demo
                'max_daily_loss': 2500,      # 5% of $50k demo
                'min_trading_days': 4        # Only 4 days required
            },
            'phase2': {
                'duration_days': None,       # No time limit!
                'profit_target': 2500,       # 5% of $50k demo
                'max_drawdown': 5000,        # 10% of $50k demo
                'max_daily_loss': 2500,      # 5% of $50k demo
                'min_trading_days': 4        # Only 4 days required
            }
        }
        
        # Crypto settings for FTMO
        self.crypto_config = {
            'BTCUSD': {
                'symbol': 'BTCUSD',
                'weight': 0.7,  # 70% of positions
                'leverage': 2,  # FTMO allows 1:2 for crypto
                'commission_per_lot': 3,  # $3 per lot
                'expected_monthly_return': 6.8,  # From backtesting
                'expected_drawdown': 0.4,  # From backtesting
                'win_rate': 0.758,  # 75.8% from backtesting
                'min_momentum_pct': 0.3,
            },
            'ETHUSD': {
                'symbol': 'ETHUSD',
                'weight': 0.3,  # 30% of positions
                'leverage': 2,
                'commission_per_lot': 3,
                'expected_monthly_return': 2.5,
                'expected_drawdown': 0.0,
                'win_rate': 0.576,
                'min_momentum_pct': 0.25,  # Lower threshold for ETH
            }
        }
        
        # Performance tracking
        self.positions = {}
        self.daily_pnl = 0
        self.total_pnl = 0
        self.peak_balance = 50000  # Demo account
        self.trading_days = set()
        self.phase_start = datetime.now()
        self.current_phase = 1
        
        self.db_path = 'ftmo_bitcoin.db'
        self.init_database()
        self.connect()
    
    def init_database(self):
        """Initialize database for FTMO tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ftmo_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                highest_price REAL,
                highest_profit_pct REAL,
                trailing_activated BOOLEAN,
                stop_loss REAL,
                take_profit REAL,
                lot_size REAL,
                open_time DATETIME,
                close_time DATETIME,
                pnl REAL,
                pnl_pct REAL,
                status TEXT,
                exit_reason TEXT,
                phase INTEGER,
                daily_pnl_before REAL,
                daily_pnl_after REAL,
                total_pnl_before REAL,
                total_pnl_after REAL,
                drawdown_impact REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ftmo_daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                starting_balance REAL,
                ending_balance REAL,
                daily_pnl REAL,
                daily_return_pct REAL,
                trades_count INTEGER,
                wins INTEGER,
                losses INTEGER,
                max_drawdown REAL,
                phase INTEGER,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect(self):
        """Connect to MT5"""
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        authorized = mt5.login(self.account, password=self.password, server=self.server)
        if authorized:
            self.connected = True
            account_info = mt5.account_info()
            logger.info(f"Connected to MT5 Account: {account_info.login}")
            logger.info(f"Balance: ${account_info.balance:.2f}")
            logger.info(f"Server: {self.server}")
            
            # Check crypto availability
            for symbol_config in self.crypto_config.values():
                symbol = symbol_config['symbol']
                if mt5.symbol_select(symbol, True):
                    logger.info(f"[OK] {symbol} available for trading")
                else:
                    logger.error(f"[ERROR] {symbol} NOT available!")
            
            return True
        else:
            logger.error(f"Failed to login: {mt5.last_error()}")
            return False
    
    def get_current_stop_loss_pct(self) -> float:
        """Get appropriate stop loss based on day of week"""
        now = datetime.now()
        weekday = now.weekday()
        
        # Thursday (3) or Friday (4)
        if weekday >= 3:
            return self.config['stop_loss_pct_weekend']
        else:
            return self.config['stop_loss_pct']
    
    def check_weekend_risk(self) -> Dict:
        """Check if we should limit positions for weekend"""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        
        # Friday after 12 PM or weekend
        is_weekend_risk = (weekday == 4 and hour >= 12) or weekday >= 5
        
        # Check if we should close profitable positions
        should_check_friday_close = weekday == 4 and hour >= 14  # Friday after 2 PM
        
        return {
            'is_weekend_risk': is_weekend_risk,
            'max_positions': self.config['max_positions_weekend'] if is_weekend_risk else self.config['max_positions'],
            'should_check_friday_close': should_check_friday_close,
            'current_day': now.strftime('%A'),
            'stop_loss_pct': self.get_current_stop_loss_pct()
        }
    
    def check_ftmo_compliance(self) -> Dict:
        """Check FTMO rule compliance"""
        account = mt5.account_info()
        if not account:
            return {'can_trade': False, 'reason': 'No account info'}
        
        balance = account.balance
        equity = account.equity
        
        # Update peak for drawdown calculation
        if equity > self.peak_balance:
            self.peak_balance = equity
        
        current_drawdown = self.peak_balance - equity
        drawdown_pct = (current_drawdown / self.peak_balance) * 100
        
        # Determine current phase
        phase_rules = self.ftmo_rules[f'phase{self.current_phase}']
        
        # No scaling needed - we're using $50k demo to simulate $100k FTMO
        # The percentages are the same, just the absolute values differ
        scaled_drawdown = current_drawdown
        scaled_daily_loss = abs(self.daily_pnl) if self.daily_pnl < 0 else 0
        scaled_total_pnl = self.total_pnl
        
        # Check violations
        violations = []
        warnings = []
        
        # Maximum drawdown check
        if scaled_drawdown > phase_rules['max_drawdown']:
            violations.append(f"Max drawdown exceeded: ${scaled_drawdown:.0f} > ${phase_rules['max_drawdown']:.0f}")
        elif scaled_drawdown > phase_rules['max_drawdown'] * 0.8:
            warnings.append(f"Approaching max drawdown: ${scaled_drawdown:.0f} (80% of limit)")
        
        # Daily loss check
        if scaled_daily_loss > phase_rules['max_daily_loss']:
            violations.append(f"Daily loss exceeded: ${scaled_daily_loss:.0f} > ${phase_rules['max_daily_loss']:.0f}")
        elif scaled_daily_loss > phase_rules['max_daily_loss'] * 0.8:
            warnings.append(f"Approaching daily loss limit: ${scaled_daily_loss:.0f} (80% of limit)")
        
        # Progress tracking
        days_elapsed = (datetime.now() - self.phase_start).days
        progress_pct = (scaled_total_pnl / phase_rules['profit_target']) * 100
        
        return {
            'can_trade': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'current_drawdown': scaled_drawdown,
            'drawdown_pct': drawdown_pct,
            'daily_pnl': scaled_daily_loss,
            'total_pnl': scaled_total_pnl,
            'progress_pct': progress_pct,
            'days_elapsed': days_elapsed,
            'days_remaining': 'No time limit',  # FTMO removed time limits
            'trading_days': len(self.trading_days),
            'min_days_needed': phase_rules['min_trading_days'],
            'profit_needed': phase_rules['profit_target'] - scaled_total_pnl,
            'phase': self.current_phase
        }
    
    def find_crypto_entry(self, symbol: str) -> Optional[Dict]:
        """Find entry signal for crypto with optimized parameters"""
        
        # Get config for this symbol
        config = None
        for cfg in self.crypto_config.values():
            if cfg['symbol'] == symbol:
                config = cfg
                break
        
        if not config:
            return None
        
        # Get recent price data (15-min bars)
        rates = mt5.copy_rates_from_pos(symbol, self.config['timeframe'], 0, 30)
        if rates is None or len(rates) < 30:
            return None
        
        # Calculate multiple momentum indicators
        recent_close = rates[-1]['close']
        
        # 1. Short-term momentum (5 bars)
        momentum_5 = ((recent_close - rates[-6]['close']) / rates[-6]['close']) * 100
        
        # 2. Medium-term momentum (15 bars)
        momentum_15 = ((recent_close - rates[-16]['close']) / rates[-16]['close']) * 100
        
        # 3. Volume analysis (if available)
        recent_volume = rates[-1]['tick_volume']
        avg_volume = sum(r['tick_volume'] for r in rates[-20:]) / 20
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # 4. Volatility check (ATR)
        atr = self.calculate_atr(rates)
        volatility_ok = atr > recent_close * 0.001  # Min 0.1% ATR
        
        # Entry conditions (optimized per crypto)
        strong_momentum = abs(momentum_5) > config['min_momentum_pct']
        trend_aligned = (momentum_5 > 0 and momentum_15 > 0) or (momentum_5 < 0 and momentum_15 < 0)
        volume_surge = volume_ratio > 1.2  # 20% above average
        
        if strong_momentum and trend_aligned and volatility_ok:
            side = 'BUY' if momentum_5 > 0 else 'SELL'
            
            # Dynamic stop/target with weekend adjustment
            stop_loss_pct = self.get_current_stop_loss_pct()
            
            # Adjust ATR multiplier based on stop loss percentage
            # Mon-Wed: 2.5 ATR (2% stop), Thu-Fri: 3.0 ATR (2.5% stop)
            atr_multiplier = 2.5 if stop_loss_pct == 2.0 else 3.0 if stop_loss_pct == 2.5 else 3.5
            
            if side == 'BUY':
                stop_loss = recent_close - (atr * atr_multiplier)
                take_profit = recent_close * (1 + self.config['target_profit_pct'] / 100)
            else:
                stop_loss = recent_close + (atr * atr_multiplier)
                take_profit = recent_close * (1 - self.config['target_profit_pct'] / 100)
            
            # Calculate R:R ratio
            risk = abs(recent_close - stop_loss)
            reward = abs(take_profit - recent_close)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Only take trades with good R:R (at least 2:1)
            if rr_ratio >= 2:
                return {
                    'symbol': symbol,
                    'side': side,
                    'entry': recent_close,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'momentum_5': momentum_5,
                    'momentum_15': momentum_15,
                    'volume_ratio': volume_ratio,
                    'atr': atr,
                    'rr_ratio': rr_ratio
                }
        
        return None
    
    def calculate_atr(self, rates) -> float:
        """Calculate Average True Range"""
        if len(rates) < 2:
            return 0
        
        tr_values = []
        for i in range(1, min(14, len(rates))):
            high = rates[i]['high']
            low = rates[i]['low']
            prev_close = rates[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values) if tr_values else 0
    
    def execute_bitcoin_trade(self, signal: Dict) -> Optional[int]:
        """Execute Bitcoin trade with FTMO position sizing"""
        
        # Check FTMO compliance
        compliance = self.check_ftmo_compliance()
        if not compliance['can_trade']:
            logger.warning(f"Cannot trade - FTMO violations: {compliance['violations']}")
            return None
        
        # Log warnings if any
        for warning in compliance['warnings']:
            logger.warning(f"FTMO Warning: {warning}")
        
        symbol = signal['symbol']
        
        # Ensure symbol is selected
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Failed to select {symbol}")
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info or not symbol_info.visible:
            return None
        
        # Calculate position size (1% risk)
        account = mt5.account_info()
        risk_amount = account.balance * self.config['risk_per_trade']
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if signal['side'] == 'BUY':
            entry = tick.ask
            stop_distance = entry - signal['stop_loss']
        else:
            entry = tick.bid
            stop_distance = signal['stop_loss'] - entry
        
        if stop_distance <= 0:
            return None
        
        # Calculate lots
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        
        if tick_value > 0 and tick_size > 0:
            stop_points = stop_distance / tick_size
            lots = risk_amount / (stop_points * tick_value)
            
            # Apply leverage based on symbol
            leverage = 2  # Default FTMO crypto leverage
            for cfg in self.crypto_config.values():
                if cfg['symbol'] == symbol:
                    leverage = cfg['leverage']
                    break
            lots = lots * leverage
            
            # Round to lot step
            lot_step = symbol_info.volume_step
            lots = round(lots / lot_step) * lot_step
            
            # Apply limits
            lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
        else:
            lots = symbol_info.volume_min
        
        # Create order
        order_type = mt5.ORDER_TYPE_BUY if signal['side'] == 'BUY' else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lots,
            "type": order_type,
            "price": entry,
            "sl": signal['stop_loss'],
            "tp": signal['take_profit'],
            "deviation": 20,
            "magic": 777,  # FTMO magic number
            "comment": f"FTMO BTC Phase{self.current_phase}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"[TRADE OPENED] {symbol} {signal['side']} @ {entry:.2f}")
            logger.info(f"  Lots: {lots:.2f}, SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f}")
            logger.info(f"  R:R: {signal['rr_ratio']:.2f}, Risk: ${risk_amount:.2f}")
            logger.info(f"  Momentum: 5-bar={signal['momentum_5']:.2f}%, 15-bar={signal['momentum_15']:.2f}%")
            
            # Track position
            self.positions[result.order] = {
                'symbol': symbol,
                'side': signal['side'],
                'entry': entry,
                'highest_price': entry,
                'highest_profit_pct': 0,
                'trailing_activated': False,
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'lots': lots,
                'open_time': datetime.now(),
                'phase': self.current_phase,
                'signal_data': signal
            }
            
            # Mark as trading day
            self.trading_days.add(datetime.now().date())
            
            # Save to database
            self.save_trade(result.order, self.positions[result.order])
            
            return result.order
        else:
            logger.error(f"[ORDER FAILED] {mt5.last_error()}")
            return None
    
    def check_friday_profit_close(self):
        """Check if we should close profitable positions on Friday"""
        positions = mt5.positions_get()
        if not positions:
            return
        
        for pos in positions:
            if pos.ticket not in self.positions:
                continue
            
            position_data = self.positions[pos.ticket]
            current_price = pos.price_current
            
            # Calculate profit percentage
            if position_data['side'] == 'BUY':
                profit_pct = ((current_price - position_data['entry']) / position_data['entry']) * 100
            else:
                profit_pct = ((position_data['entry'] - current_price) / position_data['entry']) * 100
            
            # Close if profit > 3% on Friday afternoon
            if profit_pct >= self.config['friday_profit_close']:
                logger.info(f"[FRIDAY CLOSE] Closing {pos.symbol} with {profit_pct:.2f}% profit")
                self.close_position(pos.ticket, f"Friday profit close: {profit_pct:.2f}%")
    
    def update_positions(self):
        """Update positions with dynamic trailing stop"""
        
        positions = mt5.positions_get()
        if not positions:
            return
        
        for pos in positions:
            if pos.ticket not in self.positions:
                continue
            
            position_data = self.positions[pos.ticket]
            current_price = pos.price_current
            
            # Calculate profit percentage
            if position_data['side'] == 'BUY':
                profit_pct = ((current_price - position_data['entry']) / position_data['entry']) * 100
                position_data['highest_price'] = max(current_price, position_data['highest_price'])
            else:
                profit_pct = ((position_data['entry'] - current_price) / position_data['entry']) * 100
                position_data['highest_price'] = min(current_price, position_data['highest_price'])
            
            position_data['highest_profit_pct'] = max(profit_pct, position_data['highest_profit_pct'])
            
            # Check for trailing activation
            if profit_pct >= self.config['activation_pct'] and not position_data['trailing_activated']:
                position_data['trailing_activated'] = True
                logger.info(f"[TRAILING] Activated for {pos.symbol} at {profit_pct:.2f}%")
            
            # Check exit conditions
            should_exit = False
            exit_reason = ""
            
            # 1. Target reached
            if profit_pct >= self.config['target_profit_pct']:
                should_exit = True
                exit_reason = f"Target reached: {profit_pct:.2f}%"
            
            # 2. Trailing stop hit
            elif position_data['trailing_activated']:
                trail_from = position_data['highest_profit_pct'] - self.config['trail_distance_pct']
                if profit_pct <= trail_from and profit_pct >= self.config['min_profit_pct']:
                    should_exit = True
                    exit_reason = f"Trailing stop: {profit_pct:.2f}% (peak: {position_data['highest_profit_pct']:.2f}%)"
            
            # 3. Stop loss
            elif profit_pct <= -self.config['stop_loss_pct']:
                should_exit = True
                exit_reason = f"Stop loss: {profit_pct:.2f}%"
            
            # 4. FTMO violation risk
            compliance = self.check_ftmo_compliance()
            if compliance['warnings'] and profit_pct > 1:  # If warnings and in profit
                should_exit = True
                exit_reason = f"Risk management: {compliance['warnings'][0]}"
            
            if should_exit:
                self.close_position(pos.ticket, exit_reason)
    
    def close_position(self, ticket: int, reason: str):
        """Close position and update tracking"""
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return
        
        pos = position[0]
        symbol = pos.symbol
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        
        # Determine close type
        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": pos.volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 777,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            pnl = pos.profit
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            # Calculate percentage return
            position_data = self.positions[ticket]
            if position_data['side'] == 'BUY':
                pnl_pct = ((price - position_data['entry']) / position_data['entry']) * 100
            else:
                pnl_pct = ((position_data['entry'] - price) / position_data['entry']) * 100
            
            if pnl > 0:
                logger.info(f"[WIN] {symbol} - {reason}")
            else:
                logger.info(f"[LOSS] {symbol} - {reason}")
            
            logger.info(f"  P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
            logger.info(f"  Daily P&L: ${self.daily_pnl:.2f}, Total: ${self.total_pnl:.2f}")
            
            # Update database
            self.update_trade_database(ticket, pnl, pnl_pct, price, reason)
            
            # Check phase completion
            self.check_phase_completion()
            
            # Remove from tracking
            del self.positions[ticket]
    
    def save_trade(self, ticket: int, data: Dict):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ftmo_trades 
            (ticket, symbol, side, entry_price, highest_price,
             highest_profit_pct, trailing_activated, stop_loss, take_profit,
             lot_size, open_time, status, phase, daily_pnl_before, total_pnl_before)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket, data['symbol'], data['side'], data['entry'],
            data['highest_price'], 0, False, data['stop_loss'], data['take_profit'],
            data['lots'], data['open_time'], 'OPEN', self.current_phase,
            self.daily_pnl, self.total_pnl
        ))
        
        conn.commit()
        conn.close()
    
    def update_trade_database(self, ticket: int, pnl: float, pnl_pct: float, exit_price: float, reason: str):
        """Update trade when closed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE ftmo_trades 
            SET close_time = ?, pnl = ?, pnl_pct = ?, exit_price = ?,
                status = ?, exit_reason = ?, daily_pnl_after = ?, total_pnl_after = ?
            WHERE ticket = ?
        ''', (
            datetime.now(), pnl, pnl_pct, exit_price, 'CLOSED', reason,
            self.daily_pnl, self.total_pnl, ticket
        ))
        
        conn.commit()
        conn.close()
    
    def save_daily_stats(self):
        """Save daily statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        account = mt5.account_info()
        if not account:
            return
        
        # Count today's trades
        today = datetime.now().date()
        cursor.execute('''
            SELECT COUNT(*) as trades, 
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses
            FROM ftmo_trades 
            WHERE DATE(close_time) = ? AND status = 'CLOSED'
        ''', (today,))
        
        result = cursor.fetchone()
        trades_count = result[0] if result else 0
        wins = result[1] if result else 0
        losses = result[2] if result else 0
        
        # Save daily stats
        cursor.execute('''
            INSERT OR REPLACE INTO ftmo_daily_stats 
            (date, starting_balance, ending_balance, daily_pnl, daily_return_pct,
             trades_count, wins, losses, max_drawdown, phase, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today,
            account.balance - self.daily_pnl,
            account.balance,
            self.daily_pnl,
            (self.daily_pnl / (account.balance - self.daily_pnl)) * 100 if account.balance > self.daily_pnl else 0,
            trades_count,
            wins,
            losses,
            self.peak_balance - account.equity,
            self.current_phase,
            f"Trading day {len(self.trading_days)}"
        ))
        
        conn.commit()
        conn.close()
    
    def check_phase_completion(self):
        """Check if current phase is complete"""
        compliance = self.check_ftmo_compliance()
        phase_rules = self.ftmo_rules[f'phase{self.current_phase}']
        
        # No scaling - using actual demo account values
        scaled_pnl = self.total_pnl
        
        if scaled_pnl >= phase_rules['profit_target'] and len(self.trading_days) >= phase_rules['min_trading_days']:
            logger.info("="*60)
            logger.info(f"[PHASE {self.current_phase} COMPLETE!]")
            logger.info(f"   Profit: ${scaled_pnl:.2f} / ${phase_rules['profit_target']:.2f}")
            logger.info(f"   Trading days: {len(self.trading_days)} / {phase_rules['min_trading_days']}")
            logger.info(f"   Days taken: {compliance['days_elapsed']}")
            logger.info("="*60)
            
            if self.current_phase == 1:
                self.current_phase = 2
                self.phase_start = datetime.now()
                self.daily_pnl = 0
                self.total_pnl = 0
                self.trading_days = set()
                logger.info("Starting Phase 2...")
            else:
                logger.info("[FTMO CHALLENGE PASSED!] Ready for funded account!")
    
    def display_status(self):
        """Display current FTMO status"""
        compliance = self.check_ftmo_compliance()
        weekend_risk = self.check_weekend_risk()
        
        logger.info("-"*60)
        logger.info(f"FTMO Phase {self.current_phase} Status:")
        logger.info(f"  Progress: {compliance['progress_pct']:.1f}% (${compliance['total_pnl']:.2f} / ${self.ftmo_rules[f'phase{self.current_phase}']['profit_target']:.2f})")
        logger.info(f"  Days elapsed: {compliance['days_elapsed']} (Trading: {len(self.trading_days)}/{compliance['min_days_needed']})")
        logger.info(f"  Time limit: None - Trade at your own pace!")
        logger.info(f"  Daily P&L: ${compliance['daily_pnl']:.2f}")
        logger.info(f"  Drawdown: ${compliance['current_drawdown']:.2f} ({compliance['drawdown_pct']:.2f}%)")
        logger.info(f"  Active positions: {len(self.positions)}")
        logger.info(f"  Weekend Risk: {weekend_risk['current_day']} - Max {weekend_risk['max_positions']} pos, {weekend_risk['stop_loss_pct']}% stops")
        
        if compliance['profit_needed'] > 0:
            # Show average daily needed based on monthly target pace
            avg_daily_target = compliance['profit_needed'] / 20  # ~20 trading days per month
            logger.info(f"  Suggested pace: ${avg_daily_target:.2f}/day (no rush!)")
        
        logger.info("-"*60)
    
    async def run_ftmo_trading(self):
        """Main FTMO trading loop"""
        
        logger.info("="*60)
        logger.info("FTMO MULTI-CRYPTO TRADING SYSTEM")
        logger.info("="*60)
        logger.info(f"Strategy: Dynamic 5% target with trailing stops")
        logger.info(f"Symbols: BTCUSD (70%), ETHUSD (30%)")
        logger.info(f"Expected monthly: 5.5% combined")
        logger.info(f"Risk per trade: {self.config['risk_per_trade']*100}%")
        logger.info(f"Demo Account: $50,000 (simulating FTMO $100k)")
        logger.info(f"Phase 1 target: $5,000 (10%) - No time limit, min 4 days")
        logger.info(f"Phase 2 target: $2,500 (5%) - No time limit, min 4 days")
        logger.info("="*60)
        
        last_status_time = datetime.now()
        last_daily_reset = datetime.now().date()
        
        while True:
            try:
                # Daily reset
                if datetime.now().date() > last_daily_reset:
                    self.save_daily_stats()
                    self.daily_pnl = 0
                    last_daily_reset = datetime.now().date()
                    logger.info("[NEW DAY] Trading day started")
                
                # Check FTMO compliance
                compliance = self.check_ftmo_compliance()
                if not compliance['can_trade']:
                    logger.error(f"[SUSPENDED] Trading suspended: {compliance['violations']}")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Check weekend risk
                weekend_risk = self.check_weekend_risk()
                
                # Update existing positions
                self.update_positions()
                
                # Check Friday profit close
                if weekend_risk['should_check_friday_close']:
                    self.check_friday_profit_close()
                
                # Look for new entries (respecting weekend limits)
                max_pos = weekend_risk['max_positions']
                if len(self.positions) < max_pos:
                    # Check both BTC and ETH for opportunities
                    for symbol_config in self.crypto_config.values():
                        if len(self.positions) >= self.config['max_positions']:
                            break
                        
                        symbol = symbol_config['symbol']
                        # Check if we already have position in this symbol
                        has_position = any(p['symbol'] == symbol for p in self.positions.values())
                        if has_position:
                            continue
                        
                        signal = self.find_crypto_entry(symbol)
                        if signal:
                            ticket = self.execute_bitcoin_trade(signal)
                            if ticket:
                                logger.info(f"[POSITION] New {symbol} position opened")
                
                # Display status every 5 minutes
                if (datetime.now() - last_status_time).seconds > 300:
                    self.display_status()
                    last_status_time = datetime.now()
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    trader = FTMOBitcoinTrader(
        account=3062432,
        password="d07uL40Z%I",
        server="PlexyTrade-Server01"
    )
    
    if trader.connected:
        asyncio.run(trader.run_ftmo_trading())