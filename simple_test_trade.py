"""
Simple Test Trade with Error Handling
"""

import MetaTrader5 as mt5
import aiohttp
import asyncio
import os
from datetime import datetime

class SimpleTestTrader:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
    
    def test_connection(self):
        """Test MT5 connection and account info"""
        print("Testing MT5 connection...")
        
        if not mt5.initialize():
            return False, f"Failed to initialize: {mt5.last_error()}"
        
        account = mt5.account_info()
        if not account:
            return False, "No account info available"
        
        if account.login != 3062432:
            return False, f"Wrong account: {account.login}"
        
        print(f"[OK] Connected to account {account.login}")
        print(f"[OK] Balance: ${account.balance:.2f}")
        print(f"[OK] Trade allowed: {account.trade_allowed}")
        print(f"[OK] Expert advisors: {account.trade_expert}")
        
        return True, account
    
    def test_symbol_access(self):
        """Test access to trading symbols"""
        print("\nTesting symbol access...")
        
        symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']
        available_symbols = []
        
        for symbol in symbols:
            if mt5.symbol_select(symbol, True):
                tick = mt5.symbol_info_tick(symbol)
                info = mt5.symbol_info(symbol)
                
                if tick and info:
                    print(f"  {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}, Min lot={info.volume_min}")
                    available_symbols.append({
                        'symbol': symbol,
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'min_lot': info.volume_min,
                        'spread': tick.ask - tick.bid
                    })
                else:
                    print(f"  {symbol}: Available but no data")
            else:
                print(f"  {symbol}: Not available")
        
        return available_symbols
    
    def check_trading_permissions(self):
        """Check if we can actually place trades"""
        print("\nChecking trading permissions...")
        
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        
        issues = []
        
        if not account.trade_allowed:
            issues.append("Trading not allowed on account")
        
        if not account.trade_expert:
            issues.append("Expert advisors not allowed")
        
        if terminal and not terminal.trade_allowed:
            issues.append("Trading disabled in terminal")
        
        # Check if experts are enabled (attribute may not exist in all MT5 versions)
        try:
            if terminal and hasattr(terminal, 'experts_enabled') and not terminal.experts_enabled:
                issues.append("Expert advisors disabled in terminal")
        except:
            pass  # Skip this check if attribute doesn't exist
        
        if issues:
            print("[WARNING] Trading issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("[OK] All trading permissions enabled")
        
        return len(issues) == 0
    
    async def send_notification(self, test_results):
        """Send test notification"""
        
        # Format the results
        if test_results['connection_ok']:
            connection_status = "[OK] Connected"
            account_info = f"Account {test_results['account'].login}, Balance: ${test_results['account'].balance:.2f}"
        else:
            connection_status = "[FAILED] Failed"
            account_info = test_results['connection_error']
        
        symbols_status = f"[OK] {len(test_results['symbols'])} symbols available" if test_results['symbols'] else "[FAILED] No symbols"
        trading_status = "[OK] Enabled" if test_results['trading_ok'] else "[WARNING] Issues found"
        
        message = f"""
**PAPER TRADING SYSTEM TEST**

**MT5 CONNECTION TEST RESULTS:**

**Connection**: {connection_status}
{account_info}

**Symbol Access**: {symbols_status}
{chr(10).join([f"  - {s['symbol']}: {s['bid']:.5f}/{s['ask']:.5f}" for s in test_results['symbols'][:3]])}

**Trading Permissions**: {trading_status}

**SYSTEM READINESS:**
{chr(10).join(['[OK] ' + item for item in test_results['ready_items']])}
{chr(10).join(['[ISSUE] ' + item for item in test_results['issues']])}

**NEXT STEPS:**
{test_results['recommendation']}

**Test Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**STATUS: {test_results['status_message']}**
        """
        
        print("\n" + "="*60)
        print("TELEGRAM NOTIFICATION PREVIEW")
        print("="*60)
        print(message)
        print("="*60)
        
        if not self.telegram_token:
            print("\n[INFO] No Telegram token - notification preview only")
            print("Set TELEGRAM_BOT_TOKEN environment variable to send real notifications")
            return True
        
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
                        print("\n[OK] Telegram notification sent successfully!")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"\n[ERROR] Telegram failed: {response.status}")
                        print(f"Response: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"\n[ERROR] Failed to send notification: {e}")
            return False
    
    async def run_test(self):
        """Run complete system test"""
        print("PAPER TRADING SYSTEM TEST")
        print("="*60)
        
        test_results = {
            'connection_ok': False,
            'symbols': [],
            'trading_ok': False,
            'ready_items': [],
            'issues': [],
            'recommendation': '',
            'status_message': 'SYSTEM NOT READY'
        }
        
        # Test 1: Connection
        success, result = self.test_connection()
        if success:
            test_results['connection_ok'] = True
            test_results['account'] = result
            test_results['ready_items'].append('MT5 Connection Working')
        else:
            test_results['connection_error'] = result
            test_results['issues'].append('MT5 Connection Failed')
        
        if test_results['connection_ok']:
            # Test 2: Symbols
            symbols = self.test_symbol_access()
            test_results['symbols'] = symbols
            if symbols:
                test_results['ready_items'].append(f'{len(symbols)} Trading Symbols Available')
            else:
                test_results['issues'].append('No Trading Symbols Available')
            
            # Test 3: Trading permissions
            trading_ok = self.check_trading_permissions()
            test_results['trading_ok'] = trading_ok
            if trading_ok:
                test_results['ready_items'].append('Trading Permissions Enabled')
            else:
                test_results['issues'].append('Trading Permission Issues')
        
        # Determine overall status
        if test_results['connection_ok'] and test_results['symbols'] and test_results['trading_ok']:
            test_results['status_message'] = 'SYSTEM READY FOR PAPER TRADING'
            test_results['recommendation'] = 'All systems working! Ready to start 7-day verification.\nRun: python start_paper_trading.py'
        else:
            test_results['status_message'] = 'SYSTEM NEEDS ATTENTION'
            if not test_results['connection_ok']:
                test_results['recommendation'] = 'Fix MT5 connection first. Make sure PlexyTrade MT5 is running and logged in.'
            elif not test_results['symbols']:
                test_results['recommendation'] = 'Symbol access issues. Check internet connection and broker server status.'
            else:
                test_results['recommendation'] = 'Trading permission issues. Check account settings and terminal configuration.'
        
        # Send notification
        await self.send_notification(test_results)
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Overall Status: {test_results['status_message']}")
        print(f"\nReady: {len(test_results['ready_items'])} items")
        print(f"Issues: {len(test_results['issues'])} items")
        print(f"\nRecommendation: {test_results['recommendation']}")
        
        mt5.shutdown()
        return len(test_results['issues']) == 0

if __name__ == "__main__":
    tester = SimpleTestTrader()
    asyncio.run(tester.run_test())