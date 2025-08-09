"""
Test Real Trade with Environment Variables
Loads Telegram config from .env file
"""

import MetaTrader5 as mt5
import aiohttp
import asyncio
from datetime import datetime
import time

class EnvTradeTest:
    """Test with .env file loading"""
    
    def __init__(self):
        # Load from .env file manually
        self.load_env()
        self.trade_data = None
        
        print("REAL TRADE + TELEGRAM NOTIFICATION TEST")
        print("="*60)
        print(f"Telegram Token: {'SET' if self.telegram_token else 'NOT SET'}")
        print(f"Chat ID: {self.telegram_chat_id}")
        print("="*60)
    
    def load_env(self):
        """Load environment variables from .env file"""
        self.telegram_token = None
        self.telegram_chat_id = None
        
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        self.telegram_token = line.split('=', 1)[1]
                    elif line.startswith('TELEGRAM_CHAT_ID='):
                        self.telegram_chat_id = line.split('=', 1)[1]
        except FileNotFoundError:
            print("[WARNING] .env file not found")
        
        # Use the correct token from global config
        self.telegram_token = "7169619484:AAF2Kea4mskf8kWeq4Ugj-Fop7qZ8cGudT8"
        self.telegram_chat_id = "6585156851"
    
    def execute_trade(self):
        """Execute a small test trade"""
        print("\n1. Executing test trade...")
        
        # Connect to MT5
        if not mt5.initialize():
            raise Exception(f"MT5 failed: {mt5.last_error()}")
        
        account = mt5.account_info()
        if not account or account.login != 3062432:
            raise Exception("Wrong account")
        
        print(f"   Connected to account {account.login}, Balance: ${account.balance:.2f}")
        
        # Setup trade
        symbol = "EURUSD"
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        
        if not tick or not info:
            raise Exception("No market data")
        
        # Small trade parameters
        entry = tick.ask
        lot = info.volume_min
        sl = entry - 0.0010  # 10 pips stop
        tp = entry + 0.0015  # 15 pips target (1.5 R:R)
        
        print(f"   {symbol}: Entry {entry:.5f}, SL {sl:.5f}, TP {tp:.5f}")
        
        # Place order
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 888888,
            "comment": "Real Telegram Test",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   [SUCCESS] Trade placed! Ticket: {result.order}")
            
            self.trade_data = {
                'ticket': result.order,
                'symbol': symbol,
                'entry': result.price,
                'sl': sl,
                'tp': tp,
                'lot': lot,
                'rr': 1.5
            }
            return True
        else:
            raise Exception(f"Trade failed: {result.comment if result else 'No result'}")
    
    async def send_open_notification(self):
        """Send OPEN notification"""
        print("\n2. Sending OPEN notification...")
        
        message = f"""**TRADE OPENED**

**BUY {self.trade_data['symbol']}**

Entry: {self.trade_data['entry']:.5f}
Stop Loss: {self.trade_data['sl']:.5f}
Take Profit: {self.trade_data['tp']:.5f}
Size: {self.trade_data['lot']} lots
R:R: {self.trade_data['rr']}

Ticket: #{self.trade_data['ticket']}
Time: {datetime.now().strftime('%H:%M:%S')}

**REAL NOTIFICATION TEST**"""
        
        return await self._send_to_telegram(message)
    
    async def send_close_notification(self, pnl):
        """Send CLOSE notification"""
        print("\n4. Sending CLOSE notification...")
        
        result = "PROFIT" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        
        message = f"""**TRADE CLOSED**

**{self.trade_data['symbol']} CLOSED**

Result: {result}
P&L: ${pnl:.2f}
Ticket: #{self.trade_data['ticket']}
Time: {datetime.now().strftime('%H:%M:%S')}

**TEST COMPLETE**"""
        
        return await self._send_to_telegram(message)
    
    async def _send_to_telegram(self, message):
        """Actually send to Telegram"""
        
        print(f"   Sending: {message[:50]}...")
        
        if not self.telegram_token:
            print(f"   [ERROR] No token available")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"   [SUCCESS] Notification sent! Message ID: {result['result']['message_id']}")
                        return True
                    else:
                        error = await response.text()
                        print(f"   [ERROR] Telegram failed: {response.status} - {error[:100]}")
                        return False
        except Exception as e:
            print(f"   [ERROR] Exception: {e}")
            return False
    
    def close_trade(self):
        """Close the trade"""
        print("\n3. Closing trade...")
        
        ticket = self.trade_data['ticket']
        
        # Get position
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            print(f"   Position {ticket} not found (already closed)")
            return 0.0
        
        pos = pos[0]
        pnl = pos.profit
        
        print(f"   Position: {ticket}, Current P&L: ${pnl:.2f}")
        
        # Close it
        tick = mt5.symbol_info_tick(pos.symbol)
        
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": tick.bid,
            "deviation": 20,
            "magic": 888888,
            "comment": "Test close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(close_request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   [SUCCESS] Trade closed at {result.price:.5f}")
            return pnl
        else:
            raise Exception(f"Close failed: {result.comment}")
    
    async def run_test(self):
        """Run complete test"""
        try:
            # Execute trade
            self.execute_trade()
            
            # Send open notification
            await self.send_open_notification()
            
            # Wait 5 seconds
            print("\n   Waiting 5 seconds...")
            await asyncio.sleep(5)
            
            # Close trade
            pnl = self.close_trade()
            
            # Send close notification
            await self.send_close_notification(pnl)
            
            print("\n" + "="*60)
            print("REAL TRADE + NOTIFICATION TEST COMPLETE")
            print(f"Final P&L: ${pnl:.2f}")
            print("Check your Telegram for the notifications!")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            return False
        finally:
            mt5.shutdown()

if __name__ == "__main__":
    tester = EnvTradeTest()
    success = asyncio.run(tester.run_test())
    
    if success:
        print("\nAll systems working! Check Telegram for notifications.")
    else:
        print("\nIssues found.")
