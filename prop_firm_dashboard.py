"""
Prop Firm Dashboard Page with Trade Tracking and Alert Controls
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from prop_firm_integration import PropFirmIntegration
from prop_firm_demo_tracker import PropFirmDemoTracker

class PropFirmDashboard:
    """Complete prop firm dashboard with trade tracking"""
    
    def __init__(self):
        self.integration = PropFirmIntegration()
        self.demo_tracker = PropFirmDemoTracker()
        self._ensure_settings_table()
    
    def _ensure_settings_table(self):
        """Ensure settings table exists for storing preferences"""
        with sqlite3.connect(self.integration.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prop_firm_settings (
                    id INTEGER PRIMARY KEY,
                    telegram_alerts_enabled BOOLEAN DEFAULT 0,
                    alert_chat_id TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default settings if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO prop_firm_settings (id, telegram_alerts_enabled)
                VALUES (1, 0)
            """)
            conn.commit()
    
    def get_telegram_alert_status(self):
        """Get current Telegram alert status"""
        with sqlite3.connect(self.integration.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_alerts_enabled FROM prop_firm_settings WHERE id = 1")
            result = cursor.fetchone()
            return bool(result[0]) if result else False
    
    def toggle_telegram_alerts(self, enabled: bool):
        """Toggle Telegram alerts on/off"""
        with sqlite3.connect(self.integration.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE prop_firm_settings 
                SET telegram_alerts_enabled = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (1 if enabled else 0,))
            conn.commit()
    
    def render(self):
        """Render the complete prop firm dashboard"""
        st.title("💼 Breakout Prop Firm Dashboard")
        
        # Alert Control Section
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            # Telegram Alert Toggle
            alerts_enabled = self.get_telegram_alert_status()
            
            if alerts_enabled:
                if st.button("🔔 Alerts ON", type="primary", use_container_width=True):
                    self.toggle_telegram_alerts(False)
                    st.rerun()
            else:
                if st.button("🔕 Alerts OFF", type="secondary", use_container_width=True):
                    self.toggle_telegram_alerts(True)
                    st.rerun()
        
        with col2:
            status = self.integration.get_prop_firm_status()
            if status['status'] == 'ACTIVE':
                st.success(f"✅ Evaluation Active - Balance: ${status['balance']:,.0f}")
            elif status['status'] == 'PASSED':
                st.success(f"🎉 Evaluation PASSED! - Balance: ${status['balance']:,.0f}")
            else:
                st.error(f"❌ Evaluation Failed - Balance: ${status['balance']:,.0f}")
        
        with col3:
            if alerts_enabled:
                st.info("🔔 Telegram alerts are ENABLED - You'll receive trade alerts")
            else:
                st.warning("🔕 Telegram alerts are DISABLED - Manual monitoring mode")
        
        st.divider()
        
        # Demo Account Status
        demo_status = self.demo_tracker.get_demo_status()
        
        if demo_status.get('challenge_status') == 'PASSED':
            st.balloons()
            st.success("🎉🎉 CHALLENGE PASSED! Demo account achieved profit target! 🎉🎉")
        elif demo_status.get('challenge_status') == 'FAILED':
            st.error("❌ Challenge Failed - Risk limits breached")
        
        # Demo Account Overview
        st.subheader("🎮 Demo Account Performance")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            balance = demo_status.get('balance', 10000)
            pnl = demo_status.get('total_pnl', 0)
            pnl_color = "green" if pnl >= 0 else "red"
            st.metric("💰 Demo Balance", f"${balance:,.2f}", f"${pnl:+,.2f}")
            
            # Progress to target
            progress = demo_status.get('progress_to_target', 0)
            st.progress(min(progress / 100, 1.0))
            st.caption(f"{progress:.1f}% to $1,000 target")
        
        with col2:
            daily_pnl = demo_status.get('daily_pnl', 0)
            daily_color = "green" if daily_pnl >= 0 else "red"
            st.metric("📅 Today's P&L", f"${daily_pnl:,.2f}")
            
            # Daily loss meter
            daily_loss = abs(demo_status.get('daily_loss', 0))
            daily_loss_pct = (daily_loss / 500) * 100
            if daily_loss > 0:
                st.progress(min(daily_loss_pct / 100, 1.0))
                st.caption(f"Daily loss: ${daily_loss:.0f}/$500")
        
        with col3:
            drawdown = demo_status.get('drawdown', 0)
            drawdown_pct = demo_status.get('drawdown_pct', 0)
            st.metric("📉 Drawdown", f"${drawdown:.2f}", f"{drawdown_pct:.1f}%")
            
            # Drawdown meter
            dd_limit_pct = (drawdown / 600) * 100
            if drawdown > 0:
                st.progress(min(dd_limit_pct / 100, 1.0))
                st.caption(f"{dd_limit_pct:.1f}% of limit")
        
        with col4:
            win_rate = demo_status.get('win_rate', 0)
            total_trades = demo_status.get('total_trades', 0)
            st.metric("🎯 Win Rate", f"{win_rate:.1f}%", f"{total_trades} trades")
            
            # Challenge status
            status = demo_status.get('challenge_status', 'ACTIVE')
            if status == 'PASSED':
                st.success("✅ PASSED")
            elif status == 'FAILED':
                st.error("❌ FAILED")
            else:
                st.info("🏃 ACTIVE")
        
        st.divider()
        
        # Risk Management Overview
        st.subheader("📊 Signal Filtering Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        status = self.integration.get_prop_firm_status()
        daily_stats = self.integration.get_daily_stats()
        
        with col1:
            profit_pct = (status['profit_made'] / 10000) * 100
            target_pct = min(profit_pct / 10 * 100, 100)  # 10% target
            st.metric("💰 Profit Target", f"${status['profit_made']:,.0f}", 
                     f"{profit_pct:.1f}% of 10%")
            st.progress(target_pct / 100)
        
        with col2:
            daily_loss_pct = (status['daily_loss'] / 500) * 100
            st.metric("📉 Daily Loss", f"${status['daily_loss']:.0f}", 
                     f"{daily_loss_pct:.1f}% of limit")
            st.progress(min(daily_loss_pct / 100, 1.0))
        
        with col3:
            drawdown_pct = (status['max_drawdown'] / 600) * 100
            st.metric("📊 Max Drawdown", f"${status['max_drawdown']:.0f}", 
                     f"{drawdown_pct:.1f}% of limit")
            st.progress(min(drawdown_pct / 100, 1.0))
        
        with col4:
            st.metric("✅ Acceptance Rate", 
                     f"{daily_stats['acceptance_rate']:.1f}%",
                     f"{daily_stats['accepted']}/{daily_stats['total_signals']} signals")
        
        st.divider()
        
        # Trade Tracking Section
        st.subheader("📈 Live Trade Decisions")
        
        # Time filter
        col1, col2 = st.columns([1, 4])
        with col1:
            time_filter = st.selectbox(
                "Time Range",
                ["Last Hour", "Last 6 Hours", "Last 24 Hours", "All Time"],
                index=1
            )
        
        # Map time filter to hours
        time_map = {
            "Last Hour": 1,
            "Last 6 Hours": 6,
            "Last 24 Hours": 24,
            "All Time": 9999
        }
        
        hours = time_map[time_filter]
        decisions_df = self.integration.get_recent_decisions(hours=hours)
        
        if len(decisions_df) > 0:
            # Summary stats
            accepted = len(decisions_df[decisions_df['decision'] == 'ACCEPTED'])
            rejected = len(decisions_df[decisions_df['decision'] == 'REJECTED'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Signals", len(decisions_df))
            with col2:
                st.metric("✅ Accepted", accepted)
            with col3:
                st.metric("❌ Rejected", rejected)
            
            # Decision feed
            st.subheader("🔄 Signal Processing Log")
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["All Decisions", "Accepted Only", "Rejected Only"])
            
            with tab1:
                for _, decision in decisions_df.head(20).iterrows():
                    self._render_decision_card(decision)
            
            with tab2:
                accepted_df = decisions_df[decisions_df['decision'] == 'ACCEPTED']
                if len(accepted_df) > 0:
                    for _, decision in accepted_df.head(20).iterrows():
                        self._render_decision_card(decision)
                else:
                    st.info("No accepted trades in this time period")
            
            with tab3:
                rejected_df = decisions_df[decisions_df['decision'] == 'REJECTED']
                if len(rejected_df) > 0:
                    for _, decision in rejected_df.head(20).iterrows():
                        self._render_decision_card(decision)
                else:
                    st.info("No rejected trades in this time period")
            
            # Acceptance Rate Chart
            st.divider()
            st.subheader("📊 Signal Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart of decisions
                fig = px.pie(
                    values=[accepted, rejected],
                    names=['Accepted', 'Rejected'],
                    title="Decision Breakdown",
                    color_discrete_map={'Accepted': '#00ff00', 'Rejected': '#ff0000'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # R:R distribution
                if 'rr_ratio' in decisions_df.columns:
                    fig = px.histogram(
                        decisions_df,
                        x='rr_ratio',
                        title="Risk:Reward Distribution",
                        nbins=20,
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig.add_vline(x=1.5, line_dash="dash", line_color="red",
                                 annotation_text="Min R:R (1.5)")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🔍 No trading decisions yet. Waiting for signals...")
        
        # Manual Trade Entry (for testing)
        with st.expander("🧪 Test Trade Entry (Development Only)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                test_symbol = st.text_input("Symbol", "BTCUSDT")
                test_side = st.selectbox("Side", ["BUY", "SELL"])
            
            with col2:
                test_entry = st.number_input("Entry Price", value=45000.0, step=100.0)
                test_sl = st.number_input("Stop Loss", value=44500.0, step=100.0)
            
            with col3:
                test_tp = st.number_input("Take Profit", value=46500.0, step=100.0)
                
                if st.button("📝 Log Test Decision"):
                    # Calculate R:R
                    if test_side == "BUY":
                        risk = test_entry - test_sl
                        reward = test_tp - test_entry
                    else:
                        risk = test_sl - test_entry
                        reward = test_entry - test_tp
                    
                    rr_ratio = reward / risk if risk > 0 else 0
                    
                    if rr_ratio >= 1.5:
                        decision = "ACCEPTED"
                        reason = f"Good R:R ratio {rr_ratio:.2f}:1"
                    else:
                        decision = "REJECTED"
                        reason = f"R:R ratio {rr_ratio:.2f}:1 too low"
                    
                    self.integration.log_prop_firm_decision(
                        signal_data={
                            'id': 9999,
                            'symbol': test_symbol,
                            'side': test_side,
                            'entry_price': test_entry,
                            'stop_loss': test_sl,
                            'take_profit': test_tp,
                            'rr_ratio': rr_ratio
                        },
                        decision=decision,
                        reason=reason,
                        position_size=150 if decision == "ACCEPTED" else 0,
                        risk_amount=75 if decision == "ACCEPTED" else 0,
                        alert_sent=alerts_enabled and decision == "ACCEPTED"
                    )
                    st.success(f"Test decision logged: {decision}")
                    st.rerun()
    
    def _render_decision_card(self, decision):
        """Render a single decision card"""
        timestamp = pd.to_datetime(decision['timestamp']).strftime('%H:%M:%S')
        
        if decision['decision'] == 'ACCEPTED':
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    st.success("✅ ACCEPTED")
                
                with col2:
                    st.write(f"**{decision['symbol']} {decision['side']}** @ {decision['entry_price']:.2f}")
                    st.write(f"R:R {decision['rr_ratio']:.2f} | Size: ${decision['position_size']:.0f}")
                    if decision['alert_sent']:
                        st.write("📱 Alert sent")
                
                with col3:
                    st.write(timestamp)
                
                st.divider()
        else:
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    st.error("❌ REJECTED")
                
                with col2:
                    st.write(f"**{decision['symbol']} {decision['side']}** @ {decision['entry_price']:.2f}")
                    st.write(f"📝 {decision['reason']}")
                
                with col3:
                    st.write(timestamp)
                
                st.divider()

def render_prop_firm_page():
    """Main function to render prop firm page"""
    dashboard = PropFirmDashboard()
    dashboard.render()

if __name__ == "__main__":
    st.set_page_config(page_title="Prop Firm Dashboard", layout="wide")
    render_prop_firm_page()