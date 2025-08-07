"""
Prop Firm Dashboard for $10,000 One-Step Evaluation
Streamlit page for monitoring prop firm evaluation progress
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prop_firm_manager import PropFirmManager, PropFirmConfig
import sqlite3
import json

def create_gauge_chart(value, max_value, title, danger_zone=0.75):
    """Create a gauge chart for metrics"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value * danger_zone], 'color': "yellow"},
                {'range': [max_value * danger_zone, max_value], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    fig.update_layout(height=250)
    return fig

def create_progress_bar(current, target, title):
    """Create a progress bar chart"""
    progress = (current / target) * 100 if target > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode="number+gauge",
        value=progress,
        title={'text': title},
        number={'suffix': "%"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [None, 100]},
            'bar': {'color': "green" if progress >= 100 else "blue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 75], 'color': "lightyellow"},
                {'range': [75, 100], 'color': "lightgreen"}
            ],
        }
    ))
    fig.update_layout(height=150)
    return fig

def load_daily_performance(db_path):
    """Load daily performance data"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("""
            SELECT date, ending_balance, daily_pnl, daily_pnl_percent, 
                   trades_count, max_drawdown
            FROM daily_performance
            ORDER BY date DESC
            LIMIT 30
        """, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def load_recent_trades(db_path):
    """Load recent trades"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("""
            SELECT timestamp, symbol, side, entry_price, exit_price, 
                   position_size, leverage, pnl, status
            FROM prop_trades
            ORDER BY id DESC
            LIMIT 20
        """, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def display_prop_firm_dashboard():
    """Main dashboard display function"""
    st.title("💼 Prop Firm Evaluation Dashboard")
    st.subheader("$10,000 One-Step Evaluation - Breakout Prop Model")
    
    # Initialize manager
    manager = PropFirmManager()
    status = manager.get_status_report()
    
    # Check for daily reset
    manager.check_daily_reset()
    
    # Display evaluation status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if status['status']['evaluation_passed']:
            st.success("✅ EVALUATION PASSED!")
        elif status['status']['evaluation_failed']:
            st.error("❌ EVALUATION FAILED")
        else:
            st.info("📊 EVALUATION IN PROGRESS")
    
    with col2:
        st.metric("Current Balance", status['account']['current_balance'])
    
    with col3:
        st.metric("Total P&L", status['performance']['total_pnl'],
                 delta=status['performance']['total_pnl_percent'])
    
    # Risk Meters
    st.markdown("---")
    st.subheader("⚠️ Risk Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Daily Loss Meter
        daily_loss = abs(manager.status.daily_pnl)
        daily_loss_limit = manager.config.max_daily_loss
        fig = create_gauge_chart(daily_loss, daily_loss_limit, "Daily Loss")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Daily Loss: ${daily_loss:.2f} / ${daily_loss_limit:.2f}")
    
    with col2:
        # Drawdown Meter
        current_dd = manager.status.current_drawdown
        max_dd = manager.config.max_drawdown
        fig = create_gauge_chart(current_dd, max_dd, "Drawdown")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Drawdown: ${current_dd:.2f} / ${max_dd:.2f}")
    
    # Progress to Target
    st.markdown("---")
    st.subheader("🎯 Progress to Target")
    
    profit_achieved = manager.status.profit_achieved
    profit_target = manager.config.profit_target
    fig = create_progress_bar(profit_achieved, profit_target, 
                              f"Profit Progress: ${profit_achieved:.2f} / ${profit_target:.2f}")
    st.plotly_chart(fig, use_container_width=True)
    
    # Trading Status
    st.markdown("---")
    st.subheader("📈 Trading Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        trading_status = "🟢 ACTIVE" if status['status']['is_trading_allowed'] else "🔴 STOPPED"
        st.metric("Trading", trading_status)
    
    with col2:
        st.metric("Daily Trades", manager.status.daily_trades)
    
    with col3:
        st.metric("Peak Balance", status['account']['peak_balance'])
    
    with col4:
        reset_time = datetime.fromisoformat(manager.status.daily_reset_time)
        time_to_reset = reset_time - datetime.now(timezone.utc)
        hours = int(time_to_reset.total_seconds() // 3600)
        minutes = int((time_to_reset.total_seconds() % 3600) // 60)
        st.metric("Next Reset", f"{hours}h {minutes}m")
    
    # Performance Chart
    st.markdown("---")
    st.subheader("📊 Performance History")
    
    # Load and display daily performance
    daily_df = load_daily_performance(manager.db_path)
    
    if not daily_df.empty:
        # Balance chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_df['date'],
            y=daily_df['ending_balance'],
            mode='lines+markers',
            name='Balance',
            line=dict(color='blue', width=2)
        ))
        
        # Add profit target line
        fig.add_hline(y=11000, line_dash="dash", line_color="green",
                     annotation_text="Profit Target ($11,000)")
        
        # Add drawdown limit line
        fig.add_hline(y=9400, line_dash="dash", line_color="red",
                     annotation_text="Drawdown Limit ($9,400)")
        
        fig.update_layout(
            title="Account Balance History",
            xaxis_title="Date",
            yaxis_title="Balance ($)",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Daily P&L chart
        colors = ['green' if x >= 0 else 'red' for x in daily_df['daily_pnl']]
        fig = go.Figure(data=[
            go.Bar(x=daily_df['date'], y=daily_df['daily_pnl'],
                  marker_color=colors, name='Daily P&L')
        ])
        fig.update_layout(
            title="Daily P&L",
            xaxis_title="Date",
            yaxis_title="P&L ($)",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent Trades
    st.markdown("---")
    st.subheader("📝 Recent Trades")
    
    trades_df = load_recent_trades(manager.db_path)
    
    if not trades_df.empty:
        # Format the dataframe
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        trades_df['pnl'] = trades_df['pnl'].fillna(0)
        
        # Color code P&L
        def color_pnl(val):
            if pd.isna(val) or val == 0:
                return ''
            color = 'green' if val > 0 else 'red'
            return f'color: {color}'
        
        styled_df = trades_df.style.applymap(color_pnl, subset=['pnl'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No trades recorded yet")
    
    # Risk Warnings
    if manager._should_reduce_size():
        st.warning("⚠️ WARNING: Approaching risk limits - Consider reducing position sizes")
    
    if status['status']['daily_limit_reached']:
        st.error("🛑 DAILY LOSS LIMIT REACHED - Trading suspended until next reset")
    
    if status['status']['drawdown_limit_reached']:
        st.error("💔 MAXIMUM DRAWDOWN REACHED - Evaluation failed")
    
    # Manual Actions
    st.markdown("---")
    st.subheader("🔧 Manual Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Status"):
            st.rerun()
    
    with col2:
        if st.button("📊 Generate Report"):
            report = manager.get_status_report()
            st.json(report)
    
    with col3:
        if st.button("⚠️ Force Daily Reset"):
            if st.checkbox("Confirm reset"):
                manager.perform_daily_reset()
                st.success("Daily reset performed")
                st.rerun()
    
    # Info Box
    with st.expander("ℹ️ Evaluation Rules"):
        st.markdown("""
        ### $10,000 One-Step Evaluation Rules:
        - **Profit Target**: $1,000 (10%)
        - **Maximum Drawdown**: $600 (6%)
        - **Daily Loss Limit**: $500 (5%)
        - **Leverage**: 5x (BTC/ETH), 2x (Altcoins)
        - **Daily Reset**: 00:30 UTC
        - **Time Limit**: None
        - **Profit Split**: 80-90% after passing
        
        ### Risk Management:
        - Risk 1-2% per trade
        - Maximum 3 concurrent positions
        - Auto-stop at risk limits
        - Position size reduction at 75% of limits
        
        ### Success Tips:
        1. Focus on consistency over big wins
        2. Respect the daily loss limit
        3. Use proper position sizing
        4. Trade high-probability setups only
        5. Preserve capital near limits
        """)

def main():
    """Main function"""
    st.set_page_config(
        page_title="Prop Firm Dashboard",
        page_icon="💼",
        layout="wide"
    )
    
    display_prop_firm_dashboard()

if __name__ == "__main__":
    main()