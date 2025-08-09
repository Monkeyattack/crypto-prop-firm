"""
Breakout Prop Integrated Semi-Automation System
Reads signals directly from the existing signal_log database
No duplicate processing - uses what's already been parsed
"""

import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
import os
from dataclasses import dataclass
import aiohttp
import pandas as pd

# Import your existing modules
from prop_firm_manager import PropFirmManager
from adaptive_risk_manager import AdaptiveRiskManager, TradingMode
from database import DatabaseManager
from prop_firm_integration import PropFirmIntegration
from prop_firm_demo_tracker import PropFirmDemoTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SignalAlert:
    """Alert structure for Breakout Terminal execution"""
    signal_id: int
    timestamp: str
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: float
    risk_amount: float
    risk_reward: float
    account_mode: str
    urgency: str
    special_notes: str

class BreakoutIntegratedAutomation:
    """Integrated automation that reads from existing signal database"""
    
    def __init__(self):
        # Initialize managers
        self.prop_manager = PropFirmManager()
        self.risk_manager = AdaptiveRiskManager(10000)
        self.integration = PropFirmIntegration()
        self.demo_tracker = PropFirmDemoTracker()
        
        # Database paths
        self.signal_db_path = 'trade_log.db'  # Existing signal database
        self.prop_db_path = 'prop_firm.db'    # Prop firm tracking
        
        # Tracking
        self.last_processed_signal_id = self.get_last_processed_id()
        self.alerts_sent = []
        self.alert_cooldown = 30  # seconds between alerts
        self.last_alert_time = None
        
        # Telegram settings
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # Breakout specific
        self.max_leverage = {
            'BTC': 5.0, 'BTCUSDT': 5.0,
            'ETH': 5.0, 'ETHUSDT': 5.0,
            'DEFAULT': 2.0
        }
        
        logger.info(f"Starting from signal ID: {self.last_processed_signal_id}")
    
    def get_last_processed_id(self) -> int:
        """Get the last signal ID we processed"""
        try:
            conn = sqlite3.connect(self.prop_db_path)
            cursor = conn.cursor()
            
            # Create tracking table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_signals (
                    id INTEGER PRIMARY KEY,
                    signal_id INTEGER UNIQUE,
                    processed_at DATETIME,
                    alert_sent BOOLEAN,
                    execution_status TEXT
                )
            ''')
            
            # Get last processed ID
            cursor.execute('SELECT MAX(signal_id) FROM processed_signals')
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] else 0
        except:
            return 0
    
    async def check_new_signals(self) -> List[Dict]:
        """Check for new signals in the database"""
        try:
            conn = sqlite3.connect(self.signal_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get unprocessed signals
            query = '''
                SELECT * FROM signal_log 
                WHERE id > ? 
                AND symbol IS NOT NULL 
                AND side IS NOT NULL
                AND entry_price > 0
                AND processed = 0
                ORDER BY id ASC
                LIMIT 10
            '''
            
            cursor.execute(query, (self.last_processed_signal_id,))
            signals = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if signals:
                logger.info(f"Found {len(signals)} new signals to process")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking signals: {e}")
            return []
    
    async def process_signal(self, signal: Dict) -> Optional[SignalAlert]:
        """Process a signal through prop firm validation"""
        try:
            # Extract signal data
            symbol = signal['symbol']
            side = signal['side'].upper()
            entry = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            take_profit = float(signal['take_profit'])
            
            # Calculate risk metrics
            if side in ['BUY', 'LONG']:
                stop_distance = entry - stop_loss
                profit_distance = take_profit - entry
            else:
                stop_distance = stop_loss - entry
                profit_distance = entry - take_profit
            
            if stop_distance <= 0:
                logger.warning(f"Invalid stop distance for signal {signal['id']}")
                return None
            
            stop_loss_pct = (stop_distance / entry) * 100
            risk_reward = profit_distance / stop_distance
            
            # Skip low RR trades - UPDATED: Stricter filtering
            # Crypto needs 2.0+ R:R, Gold/FX needs 2.5+ R:R
            min_rr = 2.0 if 'USD' in symbol else 2.5  # Assume crypto has USD in symbol
            if risk_reward < min_rr:
                reason = f"R:R ratio {risk_reward:.2f} too low (minimum {min_rr}:1)"
                logger.info(f"Skipping signal {signal['id']}: {reason}")
                
                # Log decision to integration system
                self.integration.log_prop_firm_decision(
                    signal_data=signal | {'rr_ratio': risk_reward},
                    decision="REJECTED",
                    reason=reason
                )
                return None
            
            # Calculate position size based on risk
            risk_amount = self.prop_manager.status.current_balance * 0.015  # 1.5% risk
            position_size = risk_amount / (stop_loss_pct / 100)
            
            # Check prop firm rules
            can_trade, reason, params = self.prop_manager.can_open_trade(
                symbol=symbol,
                position_size=position_size,
                stop_loss_amount=risk_amount
            )
            
            if not can_trade:
                logger.info(f"Signal {signal['id']} rejected by prop firm: {reason}")
                
                # Log decision to integration system
                self.integration.log_prop_firm_decision(
                    signal_data=signal | {'rr_ratio': risk_reward},
                    decision="REJECTED",
                    reason=reason,
                    position_size=position_size,
                    risk_amount=risk_amount
                )
                return None
            
            # Check adaptive risk rules
            self.risk_manager.update_account_status(
                balance=self.prop_manager.status.current_balance,
                is_funded=self.prop_manager.status.evaluation_passed,
                drawdown=self.prop_manager.status.current_drawdown
            )
            
            # Count confluences
            confluences = self.count_confluences(signal, risk_reward)
            
            can_trade_risk, reason_risk, risk_params = self.risk_manager.can_take_trade(
                symbol=symbol,
                signal_confidence=0.7,  # Default confidence
                confluences=confluences
            )
            
            if not can_trade_risk:
                logger.info(f"Signal {signal['id']} rejected by risk manager: {reason_risk}")
                
                # Log decision to integration system
                self.integration.log_prop_firm_decision(
                    signal_data=signal | {'rr_ratio': risk_reward},
                    decision="REJECTED",
                    reason=reason_risk,
                    position_size=position_size,
                    risk_amount=risk_amount
                )
                return None
            
            # Adjust position size based on mode
            mode = self.risk_manager.current_mode
            if mode == TradingMode.EVALUATION_FINAL:
                position_size *= 0.33
                urgency = "HIGH"
                special_notes = "CRITICAL: Near profit target! Execute with extreme caution."
            elif mode == TradingMode.RECOVERY:
                position_size *= 0.25
                urgency = "HIGH"
                special_notes = "RECOVERY MODE: Only execute if 100% confident."
            else:
                urgency = "MEDIUM"
                special_notes = "Standard trade - Follow risk management rules."
            
            # Determine leverage
            symbol_base = symbol.replace('USDT', '')
            leverage = self.max_leverage.get(symbol_base, self.max_leverage['DEFAULT'])
            
            # Log accepted signal to integration system
            self.integration.log_prop_firm_decision(
                signal_data=signal | {'rr_ratio': risk_reward},
                decision="ACCEPTED",
                reason=f"Good R:R ratio {risk_reward:.2f}:1, within risk limits",
                position_size=round(position_size, 2),
                risk_amount=round(risk_amount, 2),
                alert_sent=False  # Will be updated when telegram alert is sent
            )
            
            # Track in demo account
            demo_signal_data = {
                'signal_id': signal['id'],
                'symbol': symbol,
                'side': side,
                'entry_price': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': round(position_size, 2)
            }
            
            success, demo_message, trade_data = self.demo_tracker.simulate_trade_execution(demo_signal_data)
            if success:
                logger.info(f"Demo trade opened: {demo_message}")
            else:
                logger.warning(f"Demo trade failed: {demo_message}")
            
            # Create alert
            return SignalAlert(
                signal_id=signal['id'],
                timestamp=signal['timestamp'],
                symbol=symbol,
                side=side,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=round(position_size, 2),
                leverage=leverage,
                risk_amount=round(risk_amount, 2),
                risk_reward=round(risk_reward, 2),
                account_mode=mode.value,
                urgency=urgency,
                special_notes=special_notes
            )
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.get('id')}: {e}")
            return None
    
    def count_confluences(self, signal: Dict, risk_reward: float) -> int:
        """Count trading confluences for the signal"""
        confluences = 0
        
        # Preferred symbols
        symbol = signal['symbol']
        if symbol in ['BTCUSDT', 'SOLUSDT', 'DOTUSDT', 'ADAUSDT']:
            confluences += 2
        elif symbol in ['ETHUSDT', 'LINKUSDT']:
            confluences += 1
        
        # Risk-reward ratio
        if risk_reward >= 3.0:
            confluences += 2
        elif risk_reward >= 2.0:
            confluences += 1
        
        # Time of day (peak hours)
        hour = datetime.now(timezone.utc).hour
        if 14 <= hour <= 20:
            confluences += 1
        
        # Signal is fresh (< 5 minutes old)
        if signal.get('timestamp'):
            signal_time = datetime.fromisoformat(signal['timestamp'])
            age = (datetime.now(timezone.utc) - signal_time).seconds
            if age < 300:  # 5 minutes
                confluences += 1
        
        return confluences
    
    def check_telegram_alerts_enabled(self) -> bool:
        """Check if Telegram alerts are enabled in settings"""
        try:
            conn = sqlite3.connect(self.signal_db_path)
            cursor = conn.cursor()
            
            # Check if settings table exists and get alert status
            cursor.execute("""
                SELECT telegram_alerts_enabled 
                FROM prop_firm_settings 
                WHERE id = 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return bool(result[0])
            else:
                return False  # Default to disabled
                
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return False
        except Exception as e:
            logger.error(f"Error checking alert settings: {e}")
            return False
    
    async def send_alert(self, alert: SignalAlert):
        """Send formatted alert to Telegram if enabled"""
        # Check if alerts are enabled
        if not self.check_telegram_alerts_enabled():
            logger.info(f"Telegram alerts disabled - Signal #{alert.signal_id} accepted but not sent")
            # Update the decision to show alert not sent
            self.integration.log_prop_firm_decision(
                signal_data={'id': alert.signal_id, 'symbol': alert.symbol, 'side': alert.side,
                           'entry_price': alert.entry_price, 'stop_loss': alert.stop_loss,
                           'take_profit': alert.take_profit, 'rr_ratio': alert.risk_reward},
                decision="ACCEPTED",
                reason=f"Good R:R ratio {alert.risk_reward:.2f}:1",
                position_size=alert.position_size,
                risk_amount=alert.risk_amount,
                alert_sent=False
            )
            return
        
        # Check cooldown
        if self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time).seconds
            if elapsed < self.alert_cooldown:
                await asyncio.sleep(self.alert_cooldown - elapsed)
        
        # Format message
        urgency_emoji = {
            'HIGH': '🚨🚨🚨',
            'MEDIUM': '⚠️',
            'LOW': '📊'
        }
        
        side_emoji = '🟢' if alert.side in ['BUY', 'LONG'] else '🔴'
        
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

🔧 **Account Mode**: {alert.account_mode}
📝 **Note**: {alert.special_notes}

**QUICK EXECUTION:**
1️⃣ Open Breakout Terminal
2️⃣ Go to {alert.symbol}
3️⃣ {alert.side} ${alert.position_size:.2f} @ {alert.entry_price:.4f}
4️⃣ SL: {alert.stop_loss:.4f} | TP: {alert.take_profit:.4f}
5️⃣ Leverage: {alert.leverage}x

⏰ Signal ID: #{alert.signal_id}
📅 Time: {datetime.now().strftime('%H:%M:%S')}

**Reply with trade ID when executed**
        """
        
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
                        logger.info(f"Alert sent for signal #{alert.signal_id}")
                        self.last_alert_time = datetime.now()
                        self.mark_signal_processed(alert.signal_id)
                        
                        # Update decision to show alert was sent
                        with sqlite3.connect(self.signal_db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE prop_firm_decisions 
                                SET alert_sent = 1 
                                WHERE signal_id = ?
                                ORDER BY id DESC
                                LIMIT 1
                            """, (alert.signal_id,))
                            conn.commit()
                    else:
                        logger.error(f"Failed to send alert: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def mark_signal_processed(self, signal_id: int):
        """Mark signal as processed in our tracking database"""
        try:
            conn = sqlite3.connect(self.prop_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO processed_signals 
                (signal_id, processed_at, alert_sent, execution_status)
                VALUES (?, ?, ?, ?)
            ''', (signal_id, datetime.now().isoformat(), True, 'alert_sent'))
            
            conn.commit()
            conn.close()
            
            # Update last processed ID
            self.last_processed_signal_id = max(self.last_processed_signal_id, signal_id)
            
        except Exception as e:
            logger.error(f"Error marking signal processed: {e}")
    
    async def check_risk_status(self):
        """Monitor risk limits and send warnings"""
        status = self.prop_manager.get_status_report()
        
        # Parse percentages
        daily_loss_used = float(status['limits']['daily_loss_used'].replace('%', ''))
        drawdown_used = float(status['limits']['drawdown_used'].replace('%', ''))
        progress = float(status['progress']['progress_percent'].replace('%', ''))
        
        # Send warnings if needed
        if daily_loss_used >= 75 and 'daily_loss_warning' not in self.alerts_sent:
            await self.send_risk_alert(
                f"⚠️ WARNING: {daily_loss_used:.1f}% of daily loss limit used!",
                "Consider stopping for the day"
            )
            self.alerts_sent.append('daily_loss_warning')
        
        if drawdown_used >= 75 and 'drawdown_warning' not in self.alerts_sent:
            await self.send_risk_alert(
                f"🔴 CRITICAL: {drawdown_used:.1f}% of max drawdown used!",
                "Stop trading immediately"
            )
            self.alerts_sent.append('drawdown_warning')
        
        if progress >= 90 and 'near_target' not in self.alerts_sent:
            await self.send_risk_alert(
                f"🎯 NEAR TARGET: {progress:.1f}% complete!",
                "Switch to ultra-conservative mode"
            )
            self.alerts_sent.append('near_target')
    
    async def send_risk_alert(self, message: str, action: str):
        """Send risk management alert"""
        full_message = f"""
🚨 **RISK MANAGEMENT ALERT** 🚨

{message}

**Recommended Action:**
{action}

**Current Status:**
Balance: ${self.prop_manager.status.current_balance:.2f}
Daily P&L: ${self.prop_manager.status.daily_pnl:.2f}
Drawdown: ${self.prop_manager.status.current_drawdown:.2f}

Trading Mode: {self.risk_manager.current_mode.value}
        """
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': full_message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=data)
                
        except Exception as e:
            logger.error(f"Error sending risk alert: {e}")
    
    async def run(self):
        """Main execution loop"""
        logger.info("Starting Breakout Integrated Automation...")
        logger.info(f"Reading signals from: {self.signal_db_path}")
        logger.info(f"Last processed signal ID: {self.last_processed_signal_id}")
        
        # Send startup notification
        await self.send_startup_message()
        
        while True:
            try:
                # Check for daily reset
                self.prop_manager.check_daily_reset()
                
                # Update risk manager
                self.risk_manager.update_account_status(
                    balance=self.prop_manager.status.current_balance,
                    is_funded=self.prop_manager.status.evaluation_passed,
                    drawdown=self.prop_manager.status.current_drawdown
                )
                
                # Reset daily alerts if needed
                if self.prop_manager.status.daily_trades == 0:
                    self.alerts_sent = [a for a in self.alerts_sent if 'daily' not in a]
                
                # Check for new signals
                new_signals = await self.check_new_signals()
                
                for signal in new_signals:
                    logger.info(f"Processing signal #{signal['id']}: {signal['symbol']} {signal['side']}")
                    
                    # Process and validate
                    alert = await self.process_signal(signal)
                    
                    if alert:
                        # Send alert
                        await self.send_alert(alert)
                    else:
                        # Mark as processed even if rejected
                        self.mark_signal_processed(signal['id'])
                
                # Check risk status
                await self.check_risk_status()
                
                # Check demo trades periodically (every 30 seconds)
                if hasattr(self, '_last_demo_check'):
                    if (datetime.now() - self._last_demo_check).seconds > 30:
                        self.demo_tracker.check_open_trades()
                        self._last_demo_check = datetime.now()
                        
                        # Check for daily reset
                        if datetime.now().date() != self.demo_tracker.last_reset_date:
                            self.demo_tracker.reset_daily_stats()
                else:
                    self._last_demo_check = datetime.now()
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)
    
    async def send_startup_message(self):
        """Send startup notification"""
        message = f"""
🚀 **Breakout Automation Started**

Reading signals from existing database.
No duplicate processing - using parsed signals only.

**Current Status:**
Balance: ${self.prop_manager.status.current_balance:.2f}
Mode: {self.risk_manager.current_mode.value}
Last Signal ID: #{self.last_processed_signal_id}

System is monitoring for new signals...
        """
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=data)
                
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")


async def main():
    """Main entry point"""
    automation = BreakoutIntegratedAutomation()
    await automation.run()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/breakout_automation.log'),
            logging.StreamHandler()
        ]
    )
    
    # Run
    asyncio.run(main())