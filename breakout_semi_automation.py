"""
Breakout Prop Semi-Automation System
Generates precise trade alerts for manual execution in Breakout Terminal
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List
import os
from dataclasses import dataclass
import aiohttp
import pandas as pd

# Import your existing modules
from prop_firm_manager import PropFirmManager
from adaptive_risk_manager import AdaptiveRiskManager
from signal_processor import SignalProcessor
from telegram_notifier import send_telegram_message
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeAlert:
    """Structured trade alert for Breakout Terminal execution"""
    timestamp: str
    symbol: str
    side: str  # BUY/SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: float
    risk_amount: float
    risk_reward: float
    account_mode: str
    urgency: str  # HIGH/MEDIUM/LOW
    special_notes: str
    execution_steps: List[str]

class BreakoutSemiAutomation:
    """Semi-automated trading system for Breakout Prop"""
    
    def __init__(self):
        # Initialize components
        self.prop_manager = PropFirmManager()
        self.risk_manager = AdaptiveRiskManager(10000)
        self.signal_processor = SignalProcessor()
        self.db = DatabaseManager()
        
        # Breakout-specific settings
        self.min_position_size = 10  # Minimum $10 position
        self.max_leverage = {
            'BTC': 5.0,
            'ETH': 5.0,
            'DEFAULT': 2.0
        }
        
        # Alert settings
        self.alert_cooldown = 30  # Seconds between alerts
        self.last_alert_time = None
        
        # Mobile notification settings
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
    async def start_monitoring(self):
        """Main monitoring loop"""
        logger.info("Starting Breakout Semi-Automation System...")
        
        while True:
            try:
                # Check for daily reset
                self.prop_manager.check_daily_reset()
                self.risk_manager.reset_daily_counters()
                
                # Get current account status
                status = self.prop_manager.get_status_report()
                
                # Check if trading is allowed
                if not status['status']['is_trading_allowed']:
                    logger.warning("Trading currently disabled")
                    await asyncio.sleep(60)
                    continue
                
                # Process new signals
                await self.process_signals()
                
                # Monitor open positions
                await self.monitor_positions()
                
                # Check risk limits
                await self.check_risk_alerts()
                
                # Wait before next check
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def process_signals(self):
        """Process new trading signals"""
        # Get new signals from your source
        signals = await self.get_new_signals()
        
        for signal in signals:
            # Validate with prop firm rules
            can_trade, reason, params = self.validate_signal(signal)
            
            if can_trade:
                # Create detailed alert
                alert = self.create_trade_alert(signal, params)
                
                # Send to mobile
                await self.send_alert(alert)
                
                # Log to database
                self.log_alert(alert)
            else:
                logger.info(f"Signal rejected: {reason}")
    
    def validate_signal(self, signal) -> tuple:
        """Validate signal against all rules"""
        # Check prop firm rules
        can_trade_prop, reason_prop, params_prop = self.prop_manager.can_open_trade(
            signal['symbol'],
            signal['position_size'],
            signal['stop_loss_amount']
        )
        
        if not can_trade_prop:
            return False, reason_prop, {}
        
        # Check adaptive risk rules
        mode = self.risk_manager.update_account_status(
            self.prop_manager.status.current_balance,
            self.prop_manager.status.evaluation_passed,
            self.prop_manager.status.current_drawdown
        )
        
        # Get confluence count
        confluences = self.count_confluences(signal)
        
        can_trade_risk, reason_risk, params_risk = self.risk_manager.can_take_trade(
            signal['symbol'],
            signal['confidence'],
            confluences
        )
        
        if not can_trade_risk:
            return False, reason_risk, {}
        
        # Merge parameters
        params = {**params_prop, **params_risk}
        params['mode'] = mode.value
        
        return True, "Signal approved", params
    
    def count_confluences(self, signal) -> int:
        """Count signal confluences for risk management"""
        confluences = 0
        
        # Check if preferred symbol
        if signal['symbol'] in ['BTCUSDT', 'SOLUSDT', 'DOTUSDT']:
            confluences += 1
        
        # Check risk-reward ratio
        if signal.get('risk_reward', 0) >= 2.0:
            confluences += 1
        
        # Check if trending market
        if signal.get('trend_aligned', False):
            confluences += 1
        
        # Check volume confirmation
        if signal.get('volume_confirmed', False):
            confluences += 1
        
        # Check time of day (avoid low liquidity)
        hour = datetime.now(timezone.utc).hour
        if 14 <= hour <= 20:  # Peak trading hours
            confluences += 1
        
        return confluences
    
    def create_trade_alert(self, signal: Dict, params: Dict) -> TradeAlert:
        """Create detailed trade alert for mobile execution"""
        # Calculate exact position sizing
        position_size = self.calculate_position_size(signal, params)
        
        # Determine leverage
        symbol_base = signal['symbol'].replace('USDT', '')
        leverage = self.max_leverage.get(symbol_base, self.max_leverage['DEFAULT'])
        
        # Calculate risk metrics
        risk_amount = params['risk_amount']
        risk_reward = abs((signal['take_profit'] - signal['entry']) / 
                         (signal['entry'] - signal['stop_loss']))
        
        # Determine urgency
        urgency = self.determine_urgency(signal, params)
        
        # Create execution steps
        execution_steps = self.create_execution_steps(signal, position_size, leverage)
        
        # Special notes based on mode
        special_notes = self.get_special_notes(params)
        
        return TradeAlert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=signal['symbol'],
            side=signal['side'],
            entry_price=signal['entry'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            position_size=position_size,
            leverage=leverage,
            risk_amount=risk_amount,
            risk_reward=risk_reward,
            account_mode=params['mode'],
            urgency=urgency,
            special_notes=special_notes,
            execution_steps=execution_steps
        )
    
    def calculate_position_size(self, signal: Dict, params: Dict) -> float:
        """Calculate exact position size for Breakout"""
        base_size = params.get('position_size', 100)
        
        # Apply mode-specific adjustments
        if params['mode'] == 'evaluation_final':
            base_size *= 0.33  # Reduce size near target
        elif params['mode'] == 'recovery':
            base_size *= 0.25  # Minimal size in recovery
        
        # Ensure minimum size
        return max(base_size, self.min_position_size)
    
    def determine_urgency(self, signal: Dict, params: Dict) -> str:
        """Determine alert urgency"""
        if params['mode'] in ['evaluation_final', 'recovery']:
            return "HIGH"
        elif signal.get('confidence', 0) > 0.8:
            return "HIGH"
        elif self.prop_manager.status.daily_trades >= 2:
            return "LOW"  # Already traded today
        else:
            return "MEDIUM"
    
    def create_execution_steps(self, signal: Dict, position_size: float, leverage: float) -> List[str]:
        """Create step-by-step execution instructions"""
        return [
            f"1. Open Breakout Terminal app",
            f"2. Navigate to {signal['symbol']}",
            f"3. Select {signal['side']} order",
            f"4. Set leverage to {leverage}x",
            f"5. Enter position size: ${position_size:.2f}",
            f"6. Set entry price: {signal['entry']:.4f}",
            f"7. Set stop loss: {signal['stop_loss']:.4f}",
            f"8. Set take profit: {signal['take_profit']:.4f}",
            f"9. Review order details",
            f"10. Confirm and execute",
            f"11. Screenshot confirmation",
            f"12. Reply 'DONE' to this message"
        ]
    
    def get_special_notes(self, params: Dict) -> str:
        """Get mode-specific special notes"""
        notes = {
            'evaluation_final': "⚠️ CRITICAL: Near profit target! Execute with extreme caution. Consider taking partial profits early.",
            'recovery': "🔴 RECOVERY MODE: Only take this if 100% confident. Consider skipping if unsure.",
            'funded_conservative': "💼 Funded account - Focus on consistency over profit size.",
            'evaluation_normal': "Standard trade - Follow normal risk management."
        }
        return notes.get(params['mode'], "Execute according to plan.")
    
    async def send_alert(self, alert: TradeAlert):
        """Send formatted alert to mobile"""
        # Check cooldown
        if self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time).seconds
            if elapsed < self.alert_cooldown:
                await asyncio.sleep(self.alert_cooldown - elapsed)
        
        # Format message
        message = self.format_alert_message(alert)
        
        # Send via Telegram
        await self.send_telegram_alert(message)
        
        # Update last alert time
        self.last_alert_time = datetime.now()
    
    def format_alert_message(self, alert: TradeAlert) -> str:
        """Format alert for mobile display"""
        urgency_emoji = {
            'HIGH': '🚨',
            'MEDIUM': '⚠️',
            'LOW': '📊'
        }
        
        side_emoji = '🟢' if alert.side == 'BUY' else '🔴'
        
        message = f"""
{urgency_emoji[alert.urgency]} **BREAKOUT TRADE ALERT** {urgency_emoji[alert.urgency]}

{side_emoji} **{alert.side} {alert.symbol}**

📍 **Entry**: {alert.entry_price:.4f}
🛑 **Stop Loss**: {alert.stop_loss:.4f} 
🎯 **Take Profit**: {alert.take_profit:.4f}

💰 **Position Size**: ${alert.position_size:.2f}
⚡ **Leverage**: {alert.leverage}x
⚠️ **Risk**: ${alert.risk_amount:.2f}
📊 **RR Ratio**: {alert.risk_reward:.2f}

🔧 **Mode**: {alert.account_mode}
📝 **Note**: {alert.special_notes}

**EXECUTION STEPS:**
"""
        for step in alert.execution_steps:
            message += f"\n{step}"
        
        message += f"\n\n⏰ **Time**: {alert.timestamp}"
        message += f"\n\n**Reply 'DONE' when executed**"
        
        return message
    
    async def send_telegram_alert(self, message: str):
        """Send alert via Telegram"""
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
                        logger.info("Alert sent successfully")
                    else:
                        logger.error(f"Failed to send alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    async def monitor_positions(self):
        """Monitor open positions for management alerts"""
        # This would connect to your position tracking
        # For now, using placeholder
        positions = self.get_open_positions()
        
        for position in positions:
            # Check if stop should move to breakeven
            if self.should_move_to_breakeven(position):
                await self.send_position_alert(
                    position,
                    "Move stop loss to breakeven",
                    "HIGH"
                )
            
            # Check if should take partial profits
            if self.should_take_partial(position):
                await self.send_position_alert(
                    position,
                    "Consider taking 50% profit",
                    "MEDIUM"
                )
    
    async def check_risk_alerts(self):
        """Check for risk limit warnings"""
        status = self.prop_manager.get_status_report()
        
        # Daily loss warning
        daily_loss_used = float(status['limits']['daily_loss_used'].strip('%'))
        if daily_loss_used >= 75:
            await self.send_risk_alert(
                f"WARNING: {daily_loss_used}% of daily loss limit used!",
                "HIGH"
            )
        
        # Drawdown warning
        drawdown_used = float(status['limits']['drawdown_used'].strip('%'))
        if drawdown_used >= 75:
            await self.send_risk_alert(
                f"CRITICAL: {drawdown_used}% of max drawdown used!",
                "HIGH"
            )
        
        # Near profit target
        if status['progress']['progress_percent'].strip('%'):
            progress = float(status['progress']['progress_percent'].strip('%'))
            if progress >= 90:
                await self.send_risk_alert(
                    f"NEAR TARGET: {progress}% complete! Switch to conservative mode.",
                    "HIGH"
                )
    
    async def send_risk_alert(self, message: str, urgency: str):
        """Send risk management alert"""
        full_message = f"""
⚠️ **RISK MANAGEMENT ALERT** ⚠️

{message}

Current Status:
{json.dumps(self.prop_manager.get_status_report(), indent=2)}

Recommended Action:
- Reduce position sizes
- Only take A+ setups
- Consider stopping for the day
"""
        await self.send_telegram_alert(full_message)
    
    def log_alert(self, alert: TradeAlert):
        """Log alert to database for tracking"""
        # Store in database for analysis
        pass
    
    def get_open_positions(self) -> List[Dict]:
        """Get open positions (placeholder)"""
        # This would connect to your actual position tracking
        return []
    
    def should_move_to_breakeven(self, position: Dict) -> bool:
        """Check if position should move to breakeven"""
        # Implement your breakeven logic
        return False
    
    def should_take_partial(self, position: Dict) -> bool:
        """Check if should take partial profits"""
        # Implement your partial profit logic
        return False
    
    async def get_new_signals(self) -> List[Dict]:
        """Get new signals from your source"""
        # This connects to your signal source
        # For now, returning empty list
        return []
    
    async def send_position_alert(self, position: Dict, action: str, urgency: str):
        """Send position management alert"""
        message = f"""
📊 **POSITION MANAGEMENT** 📊

Symbol: {position.get('symbol', 'N/A')}
Current P&L: {position.get('pnl', 0):.2f}

Action Required: {action}
Urgency: {urgency}

Open Breakout Terminal and adjust position.
"""
        await self.send_telegram_alert(message)


async def main():
    """Main entry point"""
    automation = BreakoutSemiAutomation()
    await automation.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())