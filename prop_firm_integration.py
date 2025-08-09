"""
Prop Firm Integration Components
Adds prop firm decision tracking and UI integration to existing dashboard
"""

import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class PropFirmIntegration:
    """Handles prop firm data and UI integration"""
    
    def __init__(self, db_path: str = "trade_log.db"):
        self.db_path = db_path
        self._ensure_prop_firm_tables()
    
    def _ensure_prop_firm_tables(self):
        """Create prop firm tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Prop firm decisions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_firm_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    rr_ratio REAL,
                    decision TEXT,  -- 'ACCEPTED', 'REJECTED'
                    reason TEXT,    -- Detailed reason
                    position_size REAL,
                    risk_amount REAL,
                    alert_sent BOOLEAN DEFAULT 0,
                    FOREIGN KEY (signal_id) REFERENCES signal_log (id)
                )
            """)
            
            # Prop firm statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_firm_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    signals_processed INTEGER DEFAULT 0,
                    signals_accepted INTEGER DEFAULT 0,
                    signals_rejected INTEGER DEFAULT 0,
                    daily_loss REAL DEFAULT 0,
                    total_drawdown REAL DEFAULT 0,
                    account_balance REAL DEFAULT 10000,
                    profit_target_progress REAL DEFAULT 0,
                    alerts_sent INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Prop firm account status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_firm_status (
                    id INTEGER PRIMARY KEY,
                    account_balance REAL DEFAULT 10000,
                    daily_loss REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    profit_made REAL DEFAULT 0,
                    last_reset_date DATE DEFAULT CURRENT_DATE,
                    evaluation_status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, PASSED, FAILED
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert initial status if doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO prop_firm_status (id, account_balance)
                VALUES (1, 10000)
            """)
            
            conn.commit()
    
    def log_prop_firm_decision(self, signal_data: Dict, decision: str, reason: str, 
                              position_size: float = 0, risk_amount: float = 0, 
                              alert_sent: bool = False):
        """Log a prop firm decision for a signal"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO prop_firm_decisions 
                (signal_id, symbol, side, entry_price, stop_loss, take_profit, 
                 rr_ratio, decision, reason, position_size, risk_amount, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get('id'),
                signal_data.get('symbol'),
                signal_data.get('side'),
                signal_data.get('entry_price'),
                signal_data.get('stop_loss'),
                signal_data.get('take_profit'),
                signal_data.get('rr_ratio', 0),
                decision,
                reason,
                position_size,
                risk_amount,
                alert_sent
            ))
            
            conn.commit()
    
    def get_recent_decisions(self, hours: int = 24) -> pd.DataFrame:
        """Get recent prop firm decisions"""
        with sqlite3.connect(self.db_path) as conn:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    timestamp,
                    symbol,
                    side,
                    entry_price,
                    rr_ratio,
                    decision,
                    reason,
                    position_size,
                    alert_sent
                FROM prop_firm_decisions 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 50
            """
            
            return pd.read_sql_query(query, conn, params=(cutoff_time,))
    
    def get_prop_firm_status(self) -> Dict:
        """Get current prop firm account status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    account_balance,
                    daily_loss,
                    max_drawdown,
                    profit_made,
                    last_reset_date,
                    evaluation_status
                FROM prop_firm_status 
                WHERE id = 1
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'balance': row[0],
                    'daily_loss': row[1],
                    'max_drawdown': row[2],
                    'profit_made': row[3],
                    'last_reset_date': row[4],
                    'status': row[5]
                }
            else:
                return {
                    'balance': 10000,
                    'daily_loss': 0,
                    'max_drawdown': 0,
                    'profit_made': 0,
                    'last_reset_date': datetime.now().date(),
                    'status': 'ACTIVE'
                }
    
    def get_daily_stats(self) -> Dict:
        """Get today's prop firm statistics"""
        with sqlite3.connect(self.db_path) as conn:
            today = datetime.now().date()
            
            query = """
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN decision = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN alert_sent = 1 THEN 1 ELSE 0 END) as alerts_sent
                FROM prop_firm_decisions 
                WHERE DATE(timestamp) = ?
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (today,))
            row = cursor.fetchone()
            
            if row:
                total = row[0] or 0
                accepted = row[1] or 0
                rejected = row[2] or 0
                alerts = row[3] or 0
                
                return {
                    'total_signals': total,
                    'accepted': accepted,
                    'rejected': rejected,
                    'alerts_sent': alerts,
                    'acceptance_rate': (accepted / total * 100) if total > 0 else 0
                }
            
            return {
                'total_signals': 0,
                'accepted': 0,
                'rejected': 0,
                'alerts_sent': 0,
                'acceptance_rate': 0
            }

def render_prop_firm_status_banner():
    """Render prop firm status banner for main dashboard"""
    integration = PropFirmIntegration()
    status = integration.get_prop_firm_status()
    daily_stats = integration.get_daily_stats()
    
    # Status banner
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        balance_color = "green" if status['profit_made'] >= 0 else "red"
        st.metric(
            "🏦 Prop Account", 
            f"${status['balance']:,.0f}",
            f"${status['profit_made']:+,.0f}",
            delta_color=balance_color
        )
    
    with col2:
        daily_loss_pct = (status['daily_loss'] / 500) * 100  # 5% daily limit = $500
        loss_color = "red" if daily_loss_pct > 80 else "orange" if daily_loss_pct > 60 else "green"
        st.metric(
            "📉 Daily Loss", 
            f"${status['daily_loss']:.0f} / $500",
            f"{daily_loss_pct:.1f}% of limit"
        )
        if daily_loss_pct > 0:
            st.progress(min(daily_loss_pct / 100, 1.0))
    
    with col3:
        drawdown_pct = (status['max_drawdown'] / 600) * 100  # 6% drawdown limit = $600
        dd_color = "red" if drawdown_pct > 80 else "orange" if drawdown_pct > 60 else "green"
        st.metric(
            "📊 Max Drawdown", 
            f"${status['max_drawdown']:.0f} / $600",
            f"{drawdown_pct:.1f}% of limit"
        )
        if drawdown_pct > 0:
            st.progress(min(drawdown_pct / 100, 1.0))
    
    with col4:
        acceptance_rate = daily_stats['acceptance_rate']
        rate_color = "green" if acceptance_rate > 20 else "orange" if acceptance_rate > 10 else "red"
        st.metric(
            "✅ Today's Signals", 
            f"{daily_stats['accepted']} / {daily_stats['total_signals']}",
            f"{acceptance_rate:.1f}% accepted"
        )

def render_recent_prop_decisions():
    """Render recent prop firm decisions"""
    integration = PropFirmIntegration()
    decisions_df = integration.get_recent_decisions(hours=6)  # Last 6 hours
    
    if len(decisions_df) > 0:
        st.subheader("🤖 Recent Prop Firm Decisions")
        
        for _, decision in decisions_df.head(10).iterrows():
            timestamp = pd.to_datetime(decision['timestamp']).strftime('%H:%M:%S')
            
            if decision['decision'] == 'ACCEPTED':
                st.success(
                    f"✅ **{timestamp}** - {decision['symbol']} {decision['side']} - "
                    f"**ACCEPTED** - R:R {decision['rr_ratio']:.2f} - Alert sent: {decision['alert_sent']}"
                )
            else:
                st.error(
                    f"❌ **{timestamp}** - {decision['symbol']} {decision['side']} - "
                    f"**REJECTED** - {decision['reason']}"
                )
    else:
        st.info("🔍 No recent prop firm decisions. Waiting for signals...")

def render_account_comparison():
    """Render paper vs prop account comparison"""
    integration = PropFirmIntegration()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Paper Trading Account")
        # Get paper trading stats from existing system
        # This would integrate with your existing dashboard data
        st.metric("Balance", "$50,000", "+$2,340")
        st.metric("Win Rate", "64.2%", "+2.1%")
        st.metric("Trades Today", "23", "+5")
    
    with col2:
        st.subheader("💼 Prop Firm Account")
        status = integration.get_prop_firm_status()
        daily_stats = integration.get_daily_stats()
        
        st.metric("Balance", f"${status['balance']:,.0f}", f"${status['profit_made']:+,.0f}")
        st.metric("Acceptance Rate", f"{daily_stats['acceptance_rate']:.1f}%")
        st.metric("Alerts Sent", f"{daily_stats['alerts_sent']}")

# Test function to populate sample data
def populate_sample_decisions():
    """Populate sample prop firm decisions for testing"""
    integration = PropFirmIntegration()
    
    sample_decisions = [
        {
            'signal_data': {'id': 780, 'symbol': 'BTCUSDT', 'side': 'BUY', 'entry_price': 45000, 'stop_loss': 44500, 'take_profit': 46500, 'rr_ratio': 3.0},
            'decision': 'ACCEPTED',
            'reason': 'Good R:R ratio 3.0:1, within risk limits',
            'position_size': 150,
            'risk_amount': 75,
            'alert_sent': True
        },
        {
            'signal_data': {'id': 781, 'symbol': 'ETHUSDT', 'side': 'SELL', 'entry_price': 2800, 'stop_loss': 2850, 'take_profit': 2750, 'rr_ratio': 1.0},
            'decision': 'REJECTED',
            'reason': 'R:R ratio 1.0:1 too low (minimum 1.5:1)',
            'position_size': 0,
            'risk_amount': 0,
            'alert_sent': False
        },
        {
            'signal_data': {'id': 782, 'symbol': 'SOLUSD', 'side': 'BUY', 'entry_price': 167.17, 'stop_loss': 172.18, 'take_profit': 164.43, 'rr_ratio': 0.55},
            'decision': 'REJECTED',
            'reason': 'R:R ratio 0.55:1 too low (minimum 1.5:1)',
            'position_size': 0,
            'risk_amount': 0,
            'alert_sent': False
        }
    ]
    
    for sample in sample_decisions:
        integration.log_prop_firm_decision(**sample)
    
    print("Sample prop firm decisions added!")

if __name__ == "__main__":
    # Test the integration
    populate_sample_decisions()