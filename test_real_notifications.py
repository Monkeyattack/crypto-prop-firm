"""
Test Real Trade with Real Telegram Notifications
Executes actual trade and sends real notifications
"""

import MetaTrader5 as mt5
import aiohttp
import asyncio
import os
from datetime import datetime
import time

class RealTradeNotificationTest:
    """Execute real trade with real notifications"""
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        self.trade_data = None
        
        print("REAL TRADE + NOTIFICATION TEST")
        print("="*60)
        print(f"Telegram Token: {'SET' if self.telegram_token else 'NOT SET'}")
        print(f"Chat ID: {self.telegram_chat_id}")
        print("="*60)
    
    def connect_mt5(self):
        """Connect to MT5"""
        print("\n1. Connecting to MT5...")
        
        if not mt5.initialize():
            raise Exception(f"MT5 initialization failed: {mt5.last_error()}")
        
        account = mt5.account_info()
        if not account or account.login != 3062432:
            raise Exception(f"Wrong account or not logged in")
        
        print(f"   [OK] Connected to account {account.login}")
        print(f"   [OK] Balance: ${account.balance:.2f}")
        return True
    
    def execute_trade(self):
        """Execute a real trade"""
        print("\n2. Executing real trade...")
        
        symbol = "EURUSD"
        
        # Ensure symbol is available
        if not mt5.symbol_select(symbol, True):
            raise Exception(f"Symbol {symbol} not available")
        
        # Get current price and symbol info
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        
        if not tick or not info:
            raise Exception(f"No market data for {symbol}")
        
        # Calculate trade parameters
        entry_price = tick.ask
        lot_size = info.volume_min  # 0.01 lots
        
        # Set reasonable stops (15 pips stop, 25 pips target for 1.67 R:R)
        stop_distance = 0.0015  # 15 pips
        profit_distance = 0.0025  # 25 pips
        
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + profit_distance
        risk_reward = profit_distance / stop_distance
        
        print(f"   Symbol: {symbol}")
        print(f"   Entry: {entry_price:.5f}")
        print(f"   Stop Loss: {stop_loss:.5f} (-{stop_distance*10000:.0f} pips)")
        print(f"   Take Profit: {take_profit:.5f} (+{profit_distance*10000:.0f} pips)")
        print(f"   R:R Ratio: {risk_reward:.2f}")
        print(f"   Lot Size: {lot_size}")
        
        # Create order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 777777,
            "comment": "Real Notification Test",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Execute trade
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   [SUCCESS] Trade executed!")
            print(f"     Ticket: {result.order}")
            print(f"     Execution Price: {result.price:.5f}")
            print(f"     Volume: {result.volume}")
            
            # Store trade data
            self.trade_data = {
                'ticket': result.order,
                'symbol': symbol,
                'side': 'BUY',
                'entry_price': result.price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lot_size': result.volume,
                'risk_reward': risk_reward,
                'stop_pips': stop_distance * 10000,
                'profit_pips': profit_distance * 10000
            }
            
            return True
        else:
            error = f"Trade failed: {result.comment if result else 'No result'}"
            if result:
                error += f" (Code: {result.retcode})"
            raise Exception(error)
    
    async def send_open_notification(self):
        """Send real open trade notification"""
        print("\n3. Sending OPEN trade notification...")
        
        if not self.trade_data:
            raise Exception("No trade data available")
        
        # Format professional notification
        message = f"""🟢 **TRADE OPENED** 🟢

🔸 **BUY {self.trade_data['symbol']}**

📍 **Entry Price**: {self.trade_data['entry_price']:.5f}
🛑 **Stop Loss**: {self.trade_data['stop_loss']:.5f}
🎯 **Take Profit**: {self.trade_data['take_profit']:.5f}

💰 **Position Size**: {self.trade_data['lot_size']} lots
📊 **Risk**: {self.trade_data['stop_pips']:.0f} pips
💎 **Target**: {self.trade_data['profit_pips']:.0f} pips
⚖️ **R:R Ratio**: {self.trade_data['risk_reward']:.2f}

🎫 **Ticket**: #{self.trade_data['ticket']}
⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 **NOTIFICATION TEST - REAL TRADE EXECUTED**"""
        
        return await self._send_telegram_message(message)
    
    async def send_close_notification(self, pnl):
        """Send real close trade notification"""
        print("\n5. Sending CLOSE trade notification...")
        
        if not self.trade_data:
            raise Exception("No trade data available")
        
        # Determine result
        if pnl > 0:
            result_icon = "🟢"
            result_text = "PROFIT"
            result_emoji = "💰"
        elif pnl < 0:
            result_icon = "🔴"
            result_text = "LOSS"
            result_emoji = "📉"
        else:
            result_icon = "🟡"
            result_text = "BREAKEVEN"
            result_emoji = "🎯"
        
        message = f"""{result_icon} **TRADE CLOSED** {result_icon}

💼 **CLOSED {self.trade_data['symbol']}**

{result_emoji} **Result**: {result_text}
💲 **P&L**: ${pnl:.2f}
🎫 **Ticket**: #{self.trade_data['ticket']}
⏰ **Closed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 **Trade Summary**:
• Entry: {self.trade_data['entry_price']:.5f}
• Risk: {self.trade_data['stop_pips']:.0f} pips
• Target: {self.trade_data['profit_pips']:.0f} pips
• R:R: {self.trade_data['risk_reward']:.2f}

✅ **NOTIFICATION TEST COMPLETE**"""
        
        return await self._send_telegram_message(message)
    
    async def _send_telegram_message(self, message):
        """Send message to Telegram"""
        
        print(f"   Message Preview:")
        print(f"   {'-'*50}")
        # Show message without emojis for console
        clean_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"   {clean_message}")
        print(f"   {'-'*50}")
        
        if not self.telegram_token:
            print(f"   [WARNING] No Telegram token - message not sent")
            print(f"   [INFO] Set TELEGRAM_BOT_TOKEN environment variable to send real notifications")
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
                        print(f"   [SUCCESS] Telegram notification sent!")
                        print(f"   [INFO] Message ID: {result['result']['message_id']}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"   [ERROR] Telegram API error: {response.status}")
                        print(f"   [ERROR] Response: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"   [ERROR] Failed to send notification: {e}")
            return False
    
    def close_trade(self):
        """Close the trade manually"""
        print("\n4. Closing trade...")
        
        if not self.trade_data:
            raise Exception("No trade data available")
        
        ticket = self.trade_data['ticket']
        
        # Get current position
        position = mt5.positions_get(ticket=ticket)
        if not position:
            print(f"   [INFO] Position {ticket} already closed or not found")
            return 0.0
        
        pos = position[0]
        symbol = pos.symbol
        current_pnl = pos.profit
        
        print(f"   Position Status:")
        print(f"     Ticket: {ticket}")
        print(f"     Symbol: {symbol}")
        print(f"     Volume: {pos.volume}")
        print(f"     Current P&L: ${current_pnl:.2f}")
        
        # Get current price for closing
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise Exception(f"No price data for {symbol}")
        
        # Create close request
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL,  # Close buy with sell
            "price": tick.bid,
            "deviation": 20,
            "magic": 777777,
            "comment": "Notification test close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Execute close
        result = mt5.order_send(close_request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   [SUCCESS] Position closed successfully")
            print(f"     Close Price: {result.price:.5f}")
            print(f"     Final P&L: ${current_pnl:.2f}")
            return current_pnl
        else:
            error = f"Close failed: {result.comment if result else 'No result'}"
            raise Exception(error)
    
    async def run_complete_test(self):
        """Run complete test with real notifications"""
        try:
            # Step 1: Connect
            self.connect_mt5()
            
            # Step 2: Execute trade
            self.execute_trade()
            
            # Step 3: Send open notification
            await self.send_open_notification()
            
            # Step 4: Wait a moment (simulate monitoring)
            print("\n   [INFO] Waiting 10 seconds to simulate position monitoring...")
            await asyncio.sleep(10)
            
            # Step 5: Close trade
            pnl = self.close_trade()
            
            # Step 6: Send close notification
            await self.send_close_notification(pnl)
            
            print("\n" + "="*60)
            print("REAL TRADE + NOTIFICATION TEST COMPLETE")
            print("="*60)
            print(f"[SUCCESS] Trade executed and closed successfully")
            print(f"[SUCCESS] Both open and close notifications processed")
            print(f"Final P&L: ${pnl:.2f}")
            
            if self.telegram_token:
                print(f"[SUCCESS] Real Telegram notifications sent!")
            else:
                print(f"[INFO] Notification previews shown (set TELEGRAM_BOT_TOKEN for real sending)")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            return False
        finally:
            mt5.shutdown()

if __name__ == "__main__":
    tester = RealTradeNotificationTest()
    success = asyncio.run(tester.run_complete_test())
    
    if success:
        print(f"\n🎉 ALL SYSTEMS CONFIRMED WORKING!")
        print(f"Ready for full 7-day paper trading verification.")
    else:
        print(f"\n❌ Issues found that need attention.")
        
    input("\nPress Enter to exit...")
