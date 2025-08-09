#!/usr/bin/env python3
"""
Prop Firm Signal Processor
Reads signals from signal_log, applies strict filtering, and logs decisions
Integrates with existing dashboard for real-time status updates
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropFirmSignalProcessor:
    """Processes trading signals with prop firm risk management rules"""
    
    def __init__(self, db_path="trade_log.db"):
        self.db_path = db_path
        
        # Prop firm rules (Breakout Prop $10K evaluation)
        self.rules = {
            'min_risk_reward': 1.5,      # Minimum 1.5:1 R:R
            'max_risk_percent': 2.0,     # Max 2% risk per trade
            'daily_loss_limit': 500.00,  # Max $500 daily loss
            'max_drawdown': 600.00,      # Max $600 total drawdown
            'max_daily_trades': 10,      # Reasonable daily trade limit
            'account_size': 10000.00,    # $10K account
            'profit_target': 1000.00     # $1K target (10%)
        }
        
    def calculate_risk_reward_ratio(self, entry: float, tp: float, sl: float, side: str) -> float:
        """Calculate risk:reward ratio for a trade"""
        try:
            if side.upper() == 'BUY' or side.upper() == 'LONG':
                risk = abs(entry - sl)
                reward = abs(tp - entry)
            else:  # SELL/SHORT
                risk = abs(sl - entry)
                reward = abs(entry - tp)
                
            if risk <= 0:
                return 0.0
                
            return reward / risk
        except:
            return 0.0
    
    def calculate_position_size(self, entry: float, sl: float, risk_percent: float = 2.0) -> float:
        """Calculate position size based on risk percentage"""
        try:
            risk_amount = self.rules['account_size'] * (risk_percent / 100)
            price_risk = abs(entry - sl)
            
            if price_risk <= 0:
                return 0.0
                
            position_size = risk_amount / price_risk
            return min(position_size, self.rules['account_size'] * 0.95)  # Max 95% of account
        except:
            return 0.0
    
    def get_current_status(self) -> Dict:
        """Get current prop firm account status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute("SELECT * FROM prop_firm_status WHERE id = 1")
            status_row = cursor.fetchone()
            
            if not status_row:
                # Initialize if doesn't exist
                cursor.execute("""
                    INSERT INTO prop_firm_status (id, current_balance, daily_reset_time)
                    VALUES (1, ?, datetime('now'))
                """, (self.rules['account_size'],))
                conn.commit()
                return self.get_current_status()
            
            # Check if daily reset needed (00:30 UTC daily)
            now = datetime.utcnow()
            last_reset = datetime.fromisoformat(status_row[8])  # daily_reset_time
            
            # If more than 24 hours since reset, perform daily reset
            if (now - last_reset).total_seconds() > 86400:  # 24 hours
                self.perform_daily_reset()
                return self.get_current_status()
            
            return {
                'is_trading_allowed': bool(status_row[1]),
                'current_balance': status_row[2],
                'daily_pnl': status_row[3],
                'daily_trades': status_row[4],
                'daily_loss_limit': status_row[5],
                'max_drawdown_limit': status_row[6],
                'profit_target': status_row[7],
                'evaluation_passed': bool(status_row[8]),
                'evaluation_failed': bool(status_row[9]),
                'last_updated': status_row[11]
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    def perform_daily_reset(self):
        """Reset daily metrics at 00:30 UTC"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Reset daily counters
            cursor.execute("""
                UPDATE prop_firm_status 
                SET daily_pnl = 0.0,
                    daily_trades = 0,
                    daily_reset_time = datetime('now'),
                    last_updated = datetime('now')
                WHERE id = 1
            """)
            
            conn.commit()
            logger.info("Daily prop firm reset performed")
            
        except Exception as e:
            logger.error(f"Error performing daily reset: {e}")
        finally:
            if conn:
                conn.close()
    
    def process_new_signals(self) -> List[Dict]:
        """Process all unprocessed signals from signal_log"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get unprocessed signals
            cursor.execute("""
                SELECT id, timestamp, symbol, side, entry_price, take_profit, stop_loss, raw_message
                FROM signal_log 
                WHERE prop_firm_processed = 0 OR prop_firm_processed IS NULL
                ORDER BY timestamp DESC
            """)
            
            signals = cursor.fetchall()
            decisions = []
            
            for signal in signals:
                decision = self.evaluate_signal(signal)
                decisions.append(decision)
                
                # Update signal_log with prop firm decision
                cursor.execute("""
                    UPDATE signal_log 
                    SET prop_firm_processed = 1,
                        prop_firm_decision = ?,
                        prop_firm_reason = ?
                    WHERE id = ?
                """, (decision['decision'], decision['reason'], signal[0]))
            
            conn.commit()
            logger.info(f"Processed {len(signals)} new signals")
            return decisions
            
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def evaluate_signal(self, signal) -> Dict:
        """Evaluate a single signal against prop firm rules"""
        signal_id, timestamp, symbol, side, entry, tp, sl, raw_message = signal
        
        # Get current account status
        status = self.get_current_status()
        
        decision = {
            'signal_id': signal_id,
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'entry_price': entry,
            'take_profit': tp,
            'stop_loss': sl,
            'decision': 'REJECTED',
            'reason': '',
            'risk_reward_ratio': 0.0,
            'position_size_usd': 0.0,
            'risk_percent': 0.0,
            'telegram_message': ''
        }
        
        # Rule 1: Check if trading is allowed
        if not status.get('is_trading_allowed', False):
            decision['reason'] = 'Trading suspended - Daily loss limit or max drawdown reached'
            return self.log_decision(decision)
        
        # Rule 2: Validate signal data
        if not all([entry, tp, sl]) or entry <= 0 or tp <= 0 or sl <= 0:
            decision['reason'] = 'Invalid signal data - Missing or zero prices'
            return self.log_decision(decision)
        
        # Rule 3: Calculate and check R:R ratio
        rr_ratio = self.calculate_risk_reward_ratio(entry, tp, sl, side)
        decision['risk_reward_ratio'] = rr_ratio
        
        if rr_ratio < self.rules['min_risk_reward']:
            decision['reason'] = f'R:R ratio {rr_ratio:.2f} below minimum {self.rules["min_risk_reward"]}'
            return self.log_decision(decision)
        
        # Rule 4: Calculate position size
        position_size = self.calculate_position_size(entry, sl, self.rules['max_risk_percent'])
        decision['position_size_usd'] = position_size
        decision['risk_percent'] = self.rules['max_risk_percent']
        
        if position_size <= 0:
            decision['reason'] = 'Cannot calculate valid position size'
            return self.log_decision(decision)
        
        # Rule 5: Check daily trade limit
        if status.get('daily_trades', 0) >= self.rules['max_daily_trades']:
            decision['reason'] = f'Daily trade limit reached ({self.rules["max_daily_trades"]} trades)'
            return self.log_decision(decision)
        
        # Rule 6: Check daily loss limit
        daily_loss = abs(min(0, status.get('daily_pnl', 0)))
        if daily_loss >= self.rules['daily_loss_limit'] * 0.95:  # 95% of limit
            decision['reason'] = f'Near daily loss limit: ${daily_loss:.2f}/${self.rules["daily_loss_limit"]:.2f}'
            return self.log_decision(decision)
        
        # Rule 7: Check overall drawdown
        current_balance = status.get('current_balance', self.rules['account_size'])
        drawdown = self.rules['account_size'] - current_balance
        
        if drawdown >= self.rules['max_drawdown'] * 0.95:  # 95% of limit
            decision['reason'] = f'Near max drawdown: ${drawdown:.2f}/${self.rules["max_drawdown"]:.2f}'
            return self.log_decision(decision)
        
        # All checks passed - ACCEPT the signal
        decision['decision'] = 'ACCEPTED'
        decision['reason'] = f'Trade approved - R:R {rr_ratio:.2f}, Risk {self.rules["max_risk_percent"]}%, Size ${position_size:.2f}'
        decision['telegram_message'] = self.create_telegram_message(decision)
        
        return self.log_decision(decision)
    
    def create_telegram_message(self, decision: Dict) -> str:
        """Create Telegram alert message for accepted trades"""
        return f"""
🚨 PROP FIRM TRADE ALERT 🚨

Symbol: {decision['symbol']}
Side: {decision['side']}
Entry: ${decision['entry_price']:.4f}
TP: ${decision['take_profit']:.4f}
SL: ${decision['stop_loss']:.4f}

R:R Ratio: {decision['risk_reward_ratio']:.2f}
Position Size: ${decision['position_size_usd']:.2f}
Risk: {decision['risk_percent']}%

⚠️ MANUAL EXECUTION REQUIRED
Execute this trade immediately on your prop firm account.
        """.strip()
    
    def log_decision(self, decision: Dict) -> Dict:
        """Log the decision to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current status for context
            status = self.get_current_status()
            
            # Insert decision record
            cursor.execute("""
                INSERT INTO prop_firm_decisions 
                (signal_id, symbol, side, entry_price, take_profit, stop_loss,
                 risk_reward_ratio, position_size_usd, risk_percent, decision, reason,
                 daily_loss, daily_loss_limit, current_drawdown, max_drawdown_limit, 
                 daily_trades_count, alert_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision['signal_id'], decision['symbol'], decision['side'],
                decision['entry_price'], decision['take_profit'], decision['stop_loss'],
                decision['risk_reward_ratio'], decision['position_size_usd'], decision['risk_percent'],
                decision['decision'], decision['reason'],
                abs(min(0, status.get('daily_pnl', 0))),  # daily_loss
                self.rules['daily_loss_limit'],
                self.rules['account_size'] - status.get('current_balance', self.rules['account_size']),  # current_drawdown
                self.rules['max_drawdown'],
                status.get('daily_trades', 0),
                decision.get('telegram_message', '')
            ))
            
            conn.commit()
            
            # If accepted, increment daily trades counter
            if decision['decision'] == 'ACCEPTED':
                cursor.execute("""
                    UPDATE prop_firm_status 
                    SET daily_trades = daily_trades + 1,
                        last_updated = datetime('now')
                    WHERE id = 1
                """)
                conn.commit()
            
            logger.info(f"Decision logged: {decision['decision']} - {decision['reason']}")
            
        except Exception as e:
            logger.error(f"Error logging decision: {e}")
        finally:
            if conn:
                conn.close()
        
        return decision
    
    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        """Get recent prop firm decisions for dashboard display"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, symbol, side, decision, reason, 
                       risk_reward_ratio, position_size_usd, alert_message
                FROM prop_firm_decisions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            decisions = []
            for row in cursor.fetchall():
                decisions.append({
                    'timestamp': row[0],
                    'symbol': row[1],
                    'side': row[2],
                    'decision': row[3],
                    'reason': row[4],
                    'risk_reward_ratio': row[5],
                    'position_size_usd': row[6],
                    'has_alert': bool(row[7])
                })
            
            return decisions
            
        except Exception as e:
            logger.error(f"Error getting recent decisions: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_daily_stats(self) -> Dict:
        """Get today's prop firm statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.utcnow().date()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN decision = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                    AVG(CASE WHEN decision = 'ACCEPTED' THEN risk_reward_ratio ELSE NULL END) as avg_rr_accepted
                FROM prop_firm_decisions
                WHERE date(timestamp) = ?
            """, (today,))
            
            row = cursor.fetchone()
            
            return {
                'total_signals': row[0] or 0,
                'accepted': row[1] or 0,
                'rejected': row[2] or 0,
                'acceptance_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
                'avg_rr_accepted': row[3] or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}
        finally:
            if conn:
                conn.close()

def main():
    """Main function to process signals"""
    processor = PropFirmSignalProcessor()
    
    print("Processing new signals...")
    decisions = processor.process_new_signals()
    
    if decisions:
        print(f"Processed {len(decisions)} signals:")
        for decision in decisions:
            status = "✅ ACCEPTED" if decision['decision'] == 'ACCEPTED' else "❌ REJECTED"
            print(f"  {status}: {decision['symbol']} - {decision['reason']}")
    else:
        print("No new signals to process")
    
    # Show daily stats
    stats = processor.get_daily_stats()
    if stats:
        print(f"\nToday's Stats:")
        print(f"  Total Signals: {stats['total_signals']}")
        print(f"  Accepted: {stats['accepted']}")
        print(f"  Rejected: {stats['rejected']}")
        print(f"  Acceptance Rate: {stats['acceptance_rate']:.1f}%")

if __name__ == "__main__":
    main()