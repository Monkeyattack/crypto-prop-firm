"""
Prop Firm Integration Components for Main Dashboard
Shows prop firm decisions and statistics alongside regular trading data
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from prop_firm_signal_processor import PropFirmSignalProcessor

class PropFirmDashboardIntegration:
    """Integration components for showing prop firm data in main dashboard"""
    
    def __init__(self, db_path="trade_log.db"):
        self.db_path = db_path
        self.processor = PropFirmSignalProcessor(db_path)
    
    def show_prop_firm_status_banner(self):
        """Show prop firm status at top of dashboard"""
        status = self.processor.get_current_status()
        
        if 'error' in status:
            st.error(f"⚠️ Prop Firm Status Error: {status['error']}")
            return
        
        # Status banner
        if status.get('evaluation_failed'):
            st.error("💔 PROP FIRM EVALUATION FAILED - Drawdown or loss limits exceeded")
        elif status.get('evaluation_passed'):
            st.success("🎉 PROP FIRM EVALUATION PASSED! Ready for funded account")
        elif not status.get('is_trading_allowed'):
            st.warning("🛑 PROP FIRM TRADING SUSPENDED - Daily limits reached")
        else:
            # Show current metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                balance = status.get('current_balance', 10000)
                st.metric("Prop Account", f"${balance:.2f}", 
                         delta=f"${status.get('daily_pnl', 0):.2f}")
            
            with col2:
                daily_loss = abs(min(0, status.get('daily_pnl', 0)))
                loss_limit = status.get('daily_loss_limit', 500)
                loss_pct = (daily_loss / loss_limit) * 100
                color = "red" if loss_pct > 75 else "orange" if loss_pct > 50 else "green"
                st.metric("Daily Loss", f"${daily_loss:.2f}", 
                         delta=f"{loss_pct:.1f}% of limit")
            
            with col3:
                trades = status.get('daily_trades', 0)
                st.metric("Prop Signals Today", trades)
            
            with col4:
                profit_target = status.get('profit_target', 1000)
                current_profit = balance - 10000
                progress = (current_profit / profit_target) * 100
                st.metric("Target Progress", f"{progress:.1f}%",
                         delta=f"${current_profit:.2f}/${profit_target:.2f}")
    
    def show_recent_prop_decisions(self, limit=10):
        """Show recent prop firm signal decisions"""
        st.subheader("🤖 Prop Firm Signal Decisions")
        
        decisions = self.processor.get_recent_decisions(limit)
        
        if not decisions:
            st.info("No prop firm decisions yet. Waiting for signals...")
            return
        
        # Create dataframe for display
        df_data = []
        for decision in decisions:
            # Parse timestamp
            timestamp = datetime.fromisoformat(decision['timestamp'].replace('Z', '+00:00'))
            
            df_data.append({
                'Time': timestamp.strftime('%H:%M:%S'),
                'Symbol': decision['symbol'],
                'Side': decision['side'],
                'Decision': decision['decision'],
                'Reason': decision['reason'][:50] + '...' if len(decision['reason']) > 50 else decision['reason'],
                'R:R': f"{decision['risk_reward_ratio']:.2f}" if decision['risk_reward_ratio'] > 0 else 'N/A',
                'Size': f"${decision['position_size_usd']:.0f}" if decision['position_size_usd'] > 0 else 'N/A',
                'Alert': '📤' if decision['has_alert'] else ''
            })
        
        df = pd.DataFrame(df_data)
        
        # Style the dataframe
        def color_decision(val):
            if val == 'ACCEPTED':
                return 'background-color: #d4edda; color: #155724;'
            elif val == 'REJECTED':
                return 'background-color: #f8d7da; color: #721c24;'
            return ''
        
        styled_df = df.style.applymap(color_decision, subset=['Decision'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Quick stats
        accepted = sum(1 for d in decisions if d['decision'] == 'ACCEPTED')
        rejected = len(decisions) - accepted
        acceptance_rate = (accepted / len(decisions)) * 100 if decisions else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Recent Accepted", accepted)
        with col2:
            st.metric("Recent Rejected", rejected)
        with col3:
            st.metric("Acceptance Rate", f"{acceptance_rate:.1f}%")
    
    def show_prop_firm_vs_regular_stats(self):
        """Show comparison between prop firm and regular trading stats"""
        st.subheader("📊 Account Comparison")
        
        # Get prop firm stats
        prop_status = self.processor.get_current_status()
        prop_stats = self.processor.get_daily_stats()
        
        # Get regular account stats (from main database)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Regular account stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN result IN ('tp', 'manual') AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result IN ('sl', 'manual') AND pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl
                FROM trades 
                WHERE timestamp >= date('now', 'start of day')
            """)
            
            regular_row = cursor.fetchone()
            
            # Current capital
            cursor.execute("SELECT value FROM capital ORDER BY timestamp DESC LIMIT 1")
            capital_row = cursor.fetchone()
            current_capital = capital_row[0] if capital_row else 10000
            
        except Exception as e:
            st.error(f"Error fetching regular account stats: {e}")
            return
        finally:
            conn.close()
        
        # Create comparison table
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Paper Trading Account")
            st.metric("Current Balance", f"${current_capital:.2f}")
            st.metric("Today's Trades", regular_row[0] or 0)
            
            if regular_row[0] and regular_row[0] > 0:
                win_rate = ((regular_row[1] or 0) / regular_row[0]) * 100
                st.metric("Win Rate", f"{win_rate:.1f}%")
                st.metric("Total P&L", f"${regular_row[3] or 0:.2f}")
            else:
                st.metric("Win Rate", "N/A")
                st.metric("Total P&L", "$0.00")
        
        with col2:
            st.markdown("#### 💼 Prop Firm Account")
            prop_balance = prop_status.get('current_balance', 10000)
            st.metric("Current Balance", f"${prop_balance:.2f}")
            
            prop_signals = prop_stats.get('total_signals', 0)
            st.metric("Signals Processed", prop_signals)
            st.metric("Acceptance Rate", f"{prop_stats.get('acceptance_rate', 0):.1f}%")
            
            daily_pnl = prop_status.get('daily_pnl', 0)
            st.metric("Daily P&L", f"${daily_pnl:.2f}")
    
    def show_prop_firm_risk_meters(self):
        """Show prop firm risk management meters"""
        st.subheader("⚠️ Prop Firm Risk Management")
        
        status = self.processor.get_current_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily Loss Meter
            daily_loss = abs(min(0, status.get('daily_pnl', 0)))
            daily_limit = status.get('daily_loss_limit', 500)
            
            loss_percentage = (daily_loss / daily_limit) * 100
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=loss_percentage,
                title={'text': "Daily Loss Risk"},
                number={'suffix': "%"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkred"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 75], 'color': "yellow"},
                        {'range': [75, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 95
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"${daily_loss:.2f} / ${daily_limit:.2f}")
        
        with col2:
            # Account Drawdown Meter
            current_balance = status.get('current_balance', 10000)
            account_start = 10000
            max_drawdown_limit = status.get('max_drawdown_limit', 600)
            
            current_drawdown = max(0, account_start - current_balance)
            drawdown_percentage = (current_drawdown / max_drawdown_limit) * 100
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number", 
                value=drawdown_percentage,
                title={'text': "Drawdown Risk"},
                number={'suffix': "%"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 75], 'color': "orange"},
                        {'range': [75, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 95
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"${current_drawdown:.2f} / ${max_drawdown_limit:.2f}")
        
        # Warning messages
        if loss_percentage > 75:
            st.error("🚨 WARNING: Approaching daily loss limit!")
        elif loss_percentage > 50:
            st.warning("⚠️ CAUTION: Over 50% of daily loss limit used")
        
        if drawdown_percentage > 75:
            st.error("💔 WARNING: Approaching maximum drawdown!")
        elif drawdown_percentage > 50:
            st.warning("⚠️ CAUTION: Over 50% of drawdown limit reached")
    
    def show_signal_processing_log(self):
        """Show real-time signal processing with prop firm decisions"""
        st.subheader("📡 Live Signal Processing")
        
        # Process any new signals
        with st.spinner("Processing new signals..."):
            new_decisions = self.processor.process_new_signals()
        
        if new_decisions:
            st.success(f"Processed {len(new_decisions)} new signals")
            
            for decision in new_decisions[-3:]:  # Show last 3
                if decision['decision'] == 'ACCEPTED':
                    st.success(f"✅ {decision['symbol']} {decision['side']} ACCEPTED - {decision['reason']}")
                    if decision.get('telegram_message'):
                        with st.expander(f"📤 Telegram Alert for {decision['symbol']}"):
                            st.code(decision['telegram_message'])
                else:
                    st.error(f"❌ {decision['symbol']} {decision['side']} REJECTED - {decision['reason']}")
        
        # Auto-refresh button
        if st.button("🔄 Refresh Signals"):
            st.rerun()

def show_integrated_dashboard():
    """Main function to show integrated dashboard components"""
    integration = PropFirmDashboardIntegration()
    
    # Status banner at top
    integration.show_prop_firm_status_banner()
    st.markdown("---")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🤖 Signal Decisions", "⚠️ Risk Management"])
    
    with tab1:
        integration.show_prop_firm_vs_regular_stats()
    
    with tab2:
        integration.show_recent_prop_decisions()
        st.markdown("---")
        integration.show_signal_processing_log()
    
    with tab3:
        integration.show_prop_firm_risk_meters()

if __name__ == "__main__":
    # For testing
    st.set_page_config(page_title="Prop Firm Integration Test", layout="wide")
    show_integrated_dashboard()