"""Signal Monitoring Dashboard Page"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def show_signal_monitoring():
    """Display signal monitoring status and pending signals"""
    
    st.header("📡 Signal Monitoring")
    
    try:
        # Check if monitoring is active
        conn = sqlite3.connect('trade_log.db')
        cursor = conn.cursor()
        
        # Get monitoring status
        try:
            cursor.execute("SELECT settings_json, updated_at FROM trading_settings WHERE id = 1")
            result = cursor.fetchone()
            
            if result:
                settings = json.loads(result[0]) if result[0] else {}
                last_update_time = datetime.fromisoformat(result[1].replace(' ', 'T')) if result[1] else datetime.now()
                time_since = datetime.now() - last_update_time
                
                # Check if last signal check is recent
                last_signal_check = settings.get('last_signal_check')
                if last_signal_check:
                    last_check_time = datetime.fromisoformat(last_signal_check)
                    check_time_since = datetime.now() - last_check_time
                    
                    if check_time_since.total_seconds() < 1800:  # 30 minutes
                        st.success("🟢 Signal Monitor is ACTIVE")
                    else:
                        st.warning(f"🟡 Signal Monitor may be inactive (last check: {check_time_since.total_seconds()/60:.0f} minutes ago)")
                else:
                    if time_since.total_seconds() < 300:  # 5 minutes
                        st.success("🟢 Signal Monitor is ACTIVE")
                    else:
                        st.warning(f"🟡 Signal Monitor may be inactive (last update: {time_since.total_seconds()/60:.0f} minutes ago)")
            else:
                st.error("🔴 Signal Monitor is NOT CONFIGURED")
        except Exception as e:
            st.error(f"🔴 Error checking monitor status: {str(e)}")
        
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        
        # Get signal statistics
        cursor.execute("SELECT COUNT(*) FROM signal_log")
        total_signals = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE processed = 1")
        processed_signals = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE trade_executed = 1")
        executed_signals = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM signal_log WHERE processed = 0")
        pending_signals = cursor.fetchone()[0] or 0
        
        with col1:
            st.metric("Total Signals", total_signals)
        
        with col2:
            st.metric("Processed", processed_signals)
        
        with col3:
            st.metric("Executed", executed_signals)
        
        with col4:
            st.metric("Pending", pending_signals)
        
        # Show today's signals
        st.subheader("📅 Today's Signals")
        
        today = datetime.now().date()
        query = """
            SELECT timestamp, symbol, side, entry_price, take_profit, stop_loss,
                   processed, trade_executed, channel
            FROM signal_log
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        """
        
        today_df = pd.read_sql_query(query, conn, params=(today,))
        
        if not today_df.empty:
            # Add status column
            today_df['status'] = today_df.apply(
                lambda x: '✅ Executed' if x['trade_executed'] else 
                         ('🔄 Processed' if x['processed'] else '⏳ Pending'),
                axis=1
            )
            
            # Format display
            display_df = today_df[['timestamp', 'symbol', 'side', 'entry_price', 
                                   'take_profit', 'stop_loss', 'status', 'channel']]
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No signals received today")
        
        # Show pending signals awaiting entry
        st.subheader("⏳ Signals Awaiting Entry")
        
        pending_query = """
            SELECT timestamp, symbol, side, entry_price, take_profit, stop_loss, channel
            FROM signal_log
            WHERE processed = 1 AND trade_executed = 0
            ORDER BY timestamp DESC
        """
        
        pending_df = pd.read_sql_query(pending_query, conn)
        
        if not pending_df.empty:
            st.dataframe(pending_df, use_container_width=True)
            
            # Show entry points being monitored
            st.info(f"📊 Monitoring {len(pending_df)} signals for entry conditions")
        else:
            st.info("No signals waiting for entry")
        
        # Show signal history chart
        st.subheader("📈 Signal History (Last 7 Days)")
        
        history_query = """
            SELECT DATE(timestamp) as date, 
                   COUNT(*) as total,
                   SUM(CASE WHEN trade_executed = 1 THEN 1 ELSE 0 END) as executed
            FROM signal_log
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        
        history_df = pd.read_sql_query(history_query, conn)
        
        if not history_df.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=history_df['date'],
                y=history_df['total'],
                name='Total Signals',
                marker_color='lightblue'
            ))
            
            fig.add_trace(go.Bar(
                x=history_df['date'],
                y=history_df['executed'],
                name='Executed',
                marker_color='green'
            ))
            
            fig.update_layout(
                title='Daily Signal Activity',
                xaxis_title='Date',
                yaxis_title='Count',
                barmode='overlay'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Show execution rate by symbol
        st.subheader("🎯 Execution Rate by Symbol")
        
        symbol_stats_query = """
            SELECT symbol,
                   COUNT(*) as total_signals,
                   SUM(CASE WHEN trade_executed = 1 THEN 1 ELSE 0 END) as executed,
                   ROUND(100.0 * SUM(CASE WHEN trade_executed = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as execution_rate
            FROM signal_log
            WHERE processed = 1
            GROUP BY symbol
            ORDER BY total_signals DESC
        """
        
        symbol_df = pd.read_sql_query(symbol_stats_query, conn)
        
        if not symbol_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=symbol_df['symbol'],
                    values=symbol_df['total_signals'],
                    title='Signal Distribution'
                )])
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                fig_bar = go.Figure(data=[go.Bar(
                    x=symbol_df['symbol'],
                    y=symbol_df['execution_rate'],
                    text=symbol_df['execution_rate'].astype(str) + '%',
                    textposition='auto',
                    marker_color='green'
                )])
                fig_bar.update_layout(
                    title='Execution Rate %',
                    yaxis_title='Percentage',
                    yaxis_range=[0, 100]
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        conn.close()
        
        # Add control buttons
        st.subheader("🎮 Signal Monitor Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Start Signal Monitor", type="primary"):
                st.info("To start the signal monitor, run: python automated_signal_monitor.py")
        
        with col2:
            if st.button("🔄 Refresh Status"):
                st.rerun()
        
        with col3:
            if st.button("📊 View Settings"):
                st.info("Check the Settings page to configure signal monitoring parameters")
                
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        st.info("The signal monitoring system may need to be initialized first.")
    except Exception as e:
        st.error(f"Error loading signal monitoring: {str(e)}")
        st.info("Please check the system configuration.")