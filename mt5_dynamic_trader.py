"""
MT5 Dynamic Trading with 5% Target and Prop Firm Rules
Implements the same strategy as crypto-paper-trading but with MT5 and prop firm compliance
"""

import MetaTrader5 as mt5
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5DynamicTrader:
    """Dynamic trading with 5% profit target and trailing stops"""
    
    def __init__(self, account: int, password: str, server: str):
        # MT5 credentials
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        
        # Trading parameters - same as paper trading
        self.config = {
            'target_profit_pct': 5.0,      # Target 5% profit
            'activation_pct': 4.5,          # Start trailing at 4.5%
            'trail_distance_pct': 1.5,      # Trail by 1.5%
            'min_profit_pct': 3.5,          # Min 3.5% to exit
            'stop_loss_pct': 2.0,           # 2% stop loss
            'risk_per_trade': 0.01,         # 1% risk per trade
        }
        
        # Prop firm rules
        self.prop_rules = {
            'ftmo': {
                'account_size': 100000,
                'max_drawdown': 10000,      # 10%
                'max_daily_loss': 5000,      # 5%
                'profit_target': 10000,      # 10%
                'min_trading_days': 10
            },
            'breakout': {
                'account_size': 10000,
                'max_drawdown': 600,         # 6%
                'max_daily_loss': 500,       # 5%
                'profit_target': 1000,       # 10%
                'min_trading_days': 5
            }
        }
        
        # Track positions and performance
        self.positions = {}  # {ticket: position_data}
        self.daily_pnl = 0
        self.total_pnl = 0
        self.peak_balance = 50000  # Demo account
        
        self.db_path = 'prop_trades.db'
        self.init_database()
        self.connect()
    
    def init_database(self):
        """Initialize database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                current_price REAL,
                highest_price REAL,
                highest_profit_pct REAL,
                trailing_activated BOOLEAN,
                stop_loss REAL,
                take_profit REAL,
                lot_size REAL,
                open_time DATETIME,
                close_time DATETIME,
                pnl REAL,
                status TEXT,
                prop_firm_impact TEXT
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
            logger.info(f"Connected to MT5: {account_info.login}")
            logger.info(f"Balance: ${account_info.balance:.2f}")
            return True
        else:
            logger.error(f"Failed to login: {mt5.last_error()}")
            return False
    
    def check_prop_firm_limits(self) -> Dict:
        """Check if we're within prop firm limits"""
        account = mt5.account_info()
        if not account:
            return {'can_trade': False, 'reason': 'No account info'}
        
        balance = account.balance
        equity = account.equity
        
        # Calculate drawdown from peak
        if equity > self.peak_balance:
            self.peak_balance = equity
        
        current_drawdown = self.peak_balance - equity
        
        # Check both prop firms
        violations = []
        
        for firm, rules in self.prop_rules.items():
            # Scale to prop firm account size
            scale = rules['account_size'] / 50000  # Demo is $50k
            
            scaled_dd = current_drawdown * scale
            scaled_daily = abs(self.daily_pnl) * scale if self.daily_pnl < 0 else 0
            
            if scaled_dd > rules['max_drawdown']:
                violations.append(f"{firm}: Max drawdown exceeded")
            
            if scaled_daily > rules['max_daily_loss']:
                violations.append(f"{firm}: Daily loss limit exceeded")
        
        return {
            'can_trade': len(violations) == 0,
            'violations': violations,
            'current_drawdown': current_drawdown,
            'daily_pnl': self.daily_pnl
        }
    
    def find_entry_signal(self, symbol: str) -> Optional[Dict]:
        """Look for entry based on momentum/price action"""
        
        # Get recent price data
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 20)
        if rates is None or len(rates) < 20:
            return None
        
        # Calculate simple momentum
        recent_close = rates[-1]['close']
        prev_close = rates[-10]['close']  # 10 bars ago
        
        momentum_pct = ((recent_close - prev_close) / prev_close) * 100
        
        # Look for strong momentum (simplified)
        if abs(momentum_pct) > 0.5:  # 0.5% move in 50 minutes
            side = 'BUY' if momentum_pct > 0 else 'SELL'
            
            # Calculate dynamic stop/target
            atr = self.calculate_atr(rates)
            
            if side == 'BUY':
                stop_loss = recent_close - (atr * 2)  # 2 ATR stop
                take_profit = recent_close * 1.05  # 5% target
            else:
                stop_loss = recent_close + (atr * 2)
                take_profit = recent_close * 0.95
            
            return {
                'symbol': symbol,
                'side': side,
                'entry': recent_close,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'momentum': momentum_pct
            }
        
        return None
    
    def calculate_atr(self, rates) -> float:
        """Calculate ATR for stop loss"""
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
    
    def execute_trade(self, signal: Dict) -> Optional[int]:
        """Execute trade with prop firm position sizing"""
        
        # Check prop firm limits
        limits = self.check_prop_firm_limits()
        if not limits['can_trade']:
            logger.warning(f"Cannot trade: {limits['violations']}")
            return None
        
        symbol = signal['symbol']
        
        # Ensure symbol is selected
        if not mt5.symbol_select(symbol, True):
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info or not symbol_info.visible:
            return None
        
        # Calculate position size (1% risk)
        account = mt5.account_info()
        risk_amount = account.balance * self.config['risk_per_trade']
        
        # Calculate stop distance
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
            "magic": 555,
            "comment": "Dynamic 5% strategy",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Trade opened: {symbol} {signal['side']} @ {entry:.5f}")
            
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
                'open_time': datetime.now()
            }
            
            # Save to database
            self.save_trade(result.order, self.positions[result.order])
            
            return result.order
        
        return None
    
    def update_positions(self):
        """Update all positions and check for exits"""
        
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
                logger.info(f"Trailing activated for {pos.symbol} at {profit_pct:.2f}%")
            
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
                    exit_reason = f"Trailing stop: {profit_pct:.2f}%"
            
            # 3. Stop loss (redundant with MT5 stop but good to track)
            elif profit_pct <= -self.config['stop_loss_pct']:
                should_exit = True
                exit_reason = f"Stop loss: {profit_pct:.2f}%"
            
            if should_exit:
                self.close_position(pos.ticket, exit_reason)
    
    def close_position(self, ticket: int, reason: str):
        """Close a position"""
        
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
            "magic": 555,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            pnl = pos.profit
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            logger.info(f"Position closed: {symbol} - {reason} - P&L: ${pnl:.2f}")
            
            # Update database
            self.update_trade_database(ticket, pnl, reason)
            
            # Remove from tracking
            del self.positions[ticket]
    
    def save_trade(self, ticket: int, data: Dict):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dynamic_trades 
            (ticket, symbol, side, entry_price, current_price, highest_price,
             highest_profit_pct, trailing_activated, stop_loss, take_profit,
             lot_size, open_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket, data['symbol'], data['side'], data['entry'], data['entry'],
            data['highest_price'], 0, False, data['stop_loss'], data['take_profit'],
            data['lots'], data['open_time'], 'OPEN'
        ))
        
        conn.commit()
        conn.close()
    
    def update_trade_database(self, ticket: int, pnl: float, reason: str):
        """Update trade in database when closed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check prop firm impact
        limits = self.check_prop_firm_limits()
        impact = json.dumps(limits)
        
        cursor.execute('''
            UPDATE dynamic_trades 
            SET close_time = ?, pnl = ?, status = ?, prop_firm_impact = ?
            WHERE ticket = ?
        ''', (datetime.now(), pnl, f"CLOSED: {reason}", impact, ticket))
        
        conn.commit()
        conn.close()
    
    async def run_dynamic_trading(self):
        """Main trading loop with dynamic strategy"""
        
        logger.info("Starting dynamic 5% target trading with prop firm rules")
        
        # Symbols to trade (focus on liquid forex pairs)
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
        
        while True:
            try:
                # Reset daily P&L at midnight
                now = datetime.now()
                if now.hour == 0 and now.minute == 0:
                    self.daily_pnl = 0
                
                # Check prop firm limits
                limits = self.check_prop_firm_limits()
                if not limits['can_trade']:
                    logger.warning(f"Trading suspended: {limits['violations']}")
                    await asyncio.sleep(60)
                    continue
                
                # Update existing positions
                self.update_positions()
                
                # Look for new entries if we have capacity
                if len(self.positions) < 3:  # Max 3 positions
                    for symbol in symbols:
                        if len(self.positions) >= 3:
                            break
                        
                        # Check if already have position in this symbol
                        has_position = any(p['symbol'] == symbol for p in self.positions.values())
                        if has_position:
                            continue
                        
                        # Look for entry signal
                        signal = self.find_entry_signal(symbol)
                        if signal:
                            ticket = self.execute_trade(signal)
                            if ticket:
                                logger.info(f"New position: {symbol} - Targeting 5% profit")
                
                # Log status
                if len(self.positions) > 0:
                    logger.info(f"Active positions: {len(self.positions)}, Daily P&L: ${self.daily_pnl:.2f}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    trader = MT5DynamicTrader(
        account=3062432,
        password="d07uL40Z%I",
        server="PlexyTrade-Server01"
    )
    
    if trader.connected:
        asyncio.run(trader.run_dynamic_trading())