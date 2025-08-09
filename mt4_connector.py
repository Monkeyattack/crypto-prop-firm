"""
MT4/MT5 Connector for FTMO Trading
Bridges signal system to MetaTrader for execution
"""

import MetaTrader5 as mt5
import logging
import json
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import asyncio
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5Connector:
    """Connects to MetaTrader 5 for FTMO trading"""
    
    def __init__(self, account: int = None, password: str = None, server: str = None):
        self.account = account
        self.password = password
        self.server = server or "FTMO-Demo"  # Will be provided by FTMO
        self.connected = False
        self.initialize_mt5()
    
    def initialize_mt5(self) -> bool:
        """Initialize MT5 connection"""
        
        # Initialize MT5
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Login if credentials provided
        if self.account and self.password:
            authorized = mt5.login(
                login=self.account,
                password=self.password,
                server=self.server
            )
            
            if not authorized:
                logger.error(f"Failed to login: {mt5.last_error()}")
                return False
            
            logger.info(f"Connected to account {self.account}")
            self.connected = True
            
            # Get account info
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"Account balance: ${account_info.balance:.2f}")
                logger.info(f"Account equity: ${account_info.equity:.2f}")
                logger.info(f"Account leverage: 1:{account_info.leverage}")
        
        return True
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        
        # Ensure symbol is visible
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Failed to select symbol {symbol}")
            return None
        
        info = mt5.symbol_info(symbol)
        if not info:
            return None
        
        return {
            'symbol': symbol,
            'bid': info.bid,
            'ask': info.ask,
            'spread': info.spread,
            'digits': info.digits,
            'contract_size': info.trade_contract_size,
            'min_lot': info.volume_min,
            'max_lot': info.volume_max,
            'lot_step': info.volume_step,
            'point': info.point,
            'tick_value': info.trade_tick_value
        }
    
    def calculate_lot_size(self, symbol: str, risk_amount: float, stop_loss_points: float) -> float:
        """Calculate appropriate lot size for risk"""
        
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return 0.01  # Minimum lot
        
        # Calculate lot size
        # Risk = Lots × Contract Size × Stop Loss Points × Tick Value
        tick_value = symbol_info['tick_value']
        if tick_value > 0 and stop_loss_points > 0:
            lots = risk_amount / (stop_loss_points * tick_value)
            
            # Round to lot step
            lot_step = symbol_info['lot_step']
            lots = round(lots / lot_step) * lot_step
            
            # Ensure within limits
            lots = max(symbol_info['min_lot'], min(lots, symbol_info['max_lot']))
            
            return lots
        
        return symbol_info['min_lot']
    
    def place_order(self, signal: Dict) -> Tuple[bool, str, Optional[int]]:
        """Place order based on signal"""
        
        if not self.connected:
            return False, "Not connected to MT5", None
        
        symbol = signal['symbol']
        
        # Ensure symbol is available
        if not mt5.symbol_select(symbol, True):
            return False, f"Symbol {symbol} not available", None
        
        # Get current price
        symbol_info = mt5.symbol_info_tick(symbol)
        if not symbol_info:
            return False, "Failed to get symbol prices", None
        
        # Determine order type and price
        if signal['side'].upper() in ['BUY', 'LONG']:
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        
        # Calculate lot size
        account_info = mt5.account_info()
        risk_amount = account_info.balance * 0.01  # 1% risk
        
        if signal['side'].upper() in ['BUY', 'LONG']:
            sl_points = abs(price - signal['stop_loss'])
        else:
            sl_points = abs(signal['stop_loss'] - price)
        
        lot = self.calculate_lot_size(symbol, risk_amount, sl_points)
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": signal['stop_loss'],
            "tp": signal['take_profit'],
            "deviation": 20,
            "magic": 234000,  # Magic number for identification
            "comment": f"FTMO Signal #{signal.get('signal_id', 0)}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed: {result.comment}"
            logger.error(error_msg)
            return False, error_msg, None
        
        logger.info(f"Order placed: {result.order} for {symbol}")
        
        # Log to database
        self.log_trade(signal, result.order, lot, price)
        
        return True, f"Order {result.order} placed", result.order
    
    def log_trade(self, signal: Dict, ticket: int, lot: float, price: float):
        """Log trade to database"""
        
        with sqlite3.connect('ftmo_trading.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ftmo_trades 
                (symbol, side, entry_price, stop_loss, take_profit, 
                 position_size, risk_amount, status, mt4_ticket, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['symbol'],
                signal['side'],
                price,
                signal['stop_loss'],
                signal['take_profit'],
                lot,
                signal.get('risk_amount', 0),
                'open',
                ticket,
                f"Signal #{signal.get('signal_id', 0)}"
            ))
            conn.commit()
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        return [{
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': 'BUY' if pos.type == 0 else 'SELL',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'price_current': pos.price_current,
            'sl': pos.sl,
            'tp': pos.tp,
            'profit': pos.profit,
            'comment': pos.comment
        } for pos in positions]
    
    def close_position(self, ticket: int) -> Tuple[bool, str]:
        """Close specific position"""
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, "Position not found"
        
        position = position[0]
        symbol_info = mt5.symbol_info_tick(position.symbol)
        
        # Determine close price
        if position.type == 0:  # Buy position
            price = symbol_info.bid
            close_type = mt5.ORDER_TYPE_SELL
        else:  # Sell position
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
            "magic": 234000,
            "comment": "Close by FTMO system",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"Failed to close: {result.comment}"
        
        return True, f"Position {ticket} closed"
    
    def get_account_status(self) -> Dict:
        """Get current account status"""
        
        if not self.connected:
            return {'error': 'Not connected'}
        
        account = mt5.account_info()
        if not account:
            return {'error': 'Failed to get account info'}
        
        return {
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'margin_level': account.margin_level,
            'profit': account.profit,
            'leverage': account.leverage,
            'currency': account.currency
        }
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 connection closed")

class SignalBridge:
    """Bridge between signal system and MT5"""
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.db_path = 'trade_log.db'
        self.last_processed_id = 0
    
    async def monitor_signals(self):
        """Monitor for new signals and execute on MT5"""
        
        while True:
            try:
                # Check for new signals
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM signal_log
                        WHERE id > ?
                        AND processed = 0
                        AND symbol IN ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY')
                        ORDER BY id ASC
                        LIMIT 5
                    """, (self.last_processed_id,))
                    
                    signals = cursor.fetchall()
                
                for signal in signals:
                    # Parse signal
                    signal_dict = {
                        'signal_id': signal[0],
                        'symbol': signal[2],
                        'side': signal[3],
                        'entry_price': signal[4],
                        'stop_loss': signal[5],
                        'take_profit': signal[6]
                    }
                    
                    # Execute on MT5
                    success, message, ticket = self.mt5.place_order(signal_dict)
                    
                    if success:
                        logger.info(f"Signal {signal[0]} executed: {message}")
                        self.last_processed_id = signal[0]
                        
                        # Mark as processed
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE signal_log
                                SET processed = 1
                                WHERE id = ?
                            """, (signal[0],))
                            conn.commit()
                    else:
                        logger.error(f"Signal {signal[0]} failed: {message}")
                
                # Check account status
                status = self.mt5.get_account_status()
                if status.get('margin_level', float('inf')) < 200:
                    logger.warning(f"Low margin level: {status['margin_level']:.2f}%")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in signal monitor: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    print("""
    ============================================================
    MT4/MT5 SETUP FOR FTMO
    ============================================================
    
    1. INSTALL METATRADER 5
       - Download from: https://www.metatrader5.com
       - Install and launch
    
    2. ADD FTMO SERVER
       - File → Login to Trade Account
       - Server: Will be provided by FTMO after registration
       - Login: Your FTMO demo account number
       - Password: Provided by FTMO
    
    3. INSTALL PYTHON PACKAGE
       pip install MetaTrader5
    
    4. CONFIGURE CREDENTIALS
       - Update account number in code
       - Update password
       - Update server name
    
    5. TEST CONNECTION
       Run this script to test MT5 connection
    
    ============================================================
    """)
    
    # Test connection (update with your credentials)
    connector = MT5Connector(
        # account=12345678,  # Your FTMO account
        # password="your_password",
        # server="FTMO-Demo"
    )
    
    if connector.connected:
        print("\n✅ Connected to MT5")
        print(f"Account Status: {connector.get_account_status()}")
        print(f"Open Positions: {connector.get_open_positions()}")
    else:
        print("\n❌ Not connected - please configure credentials")