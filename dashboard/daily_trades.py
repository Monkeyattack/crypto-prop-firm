#!/usr/bin/env python3
"""
Daily Trades Dashboard - Simple view of today's trading activity
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def show_daily_trades():
    """Display today's trading activity"""
    st.title("📅 Today's Trading Activity")
    st.markdown(f"### {date.today().strftime('%A, %B %d, %Y')}")
    st.markdown("---")
    
    try:
        conn = sqlite3.connect('trade_log.db')
        
        # Get today's trades
        trades_query = '''
            SELECT id, symbol, side, entry, tp, sl, exit, result, pnl, timestamp
            FROM trades
            WHERE DATE(timestamp) = DATE('now', 'localtime')
            ORDER BY timestamp DESC
        '''
        trades_df = pd.read_sql_query(trades_query, conn)
        
        if trades_df.empty:
            st.info("No trades executed today")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_trades = len(trades_df)
        open_trades = len(trades_df[trades_df['result'] == 'open'])
        closed_trades = total_trades - open_trades
        
        # Calculate P&L
        closed_df = trades_df[trades_df['result'] != 'open']
        total_pnl = closed_df['pnl'].sum() if not closed_df.empty else 0
        avg_pnl = closed_df['pnl'].mean() if not closed_df.empty else 0
        
        with col1:
            st.metric("Total Trades", total_trades)
        
        with col2:
            st.metric("Open Positions", open_trades)
        
        with col3:
            st.metric("Closed Trades", closed_trades)
        
        with col4:
            if closed_trades > 0:
                st.metric("Total P&L", f"{total_pnl:.2f}%", f"Avg: {avg_pnl:.2f}%")
            else:
                st.metric("Total P&L", "0.00%", "No closes")
        
        # Position distribution
        st.subheader("📊 Position Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Symbol distribution
            symbol_counts = trades_df['symbol'].value_counts()
            fig_symbols = go.Figure(data=[
                go.Pie(labels=symbol_counts.index, values=symbol_counts.values, hole=0.3)
            ])
            fig_symbols.update_layout(title="Trades by Symbol", height=300)
            st.plotly_chart(fig_symbols, use_container_width=True)
        
        with col2:
            # Side distribution
            side_counts = trades_df['side'].value_counts()
            colors = ['#00cc88' if side.upper() in ['BUY', 'LONG'] else '#ff3366' for side in side_counts.index]
            fig_sides = go.Figure(data=[
                go.Bar(x=side_counts.index, y=side_counts.values, marker_color=colors)
            ])
            fig_sides.update_layout(title="Buy vs Sell", height=300)
            st.plotly_chart(fig_sides, use_container_width=True)
        
        # Open positions detail
        if open_trades > 0:
            st.subheader("🟢 Open Positions")
            
            open_df = trades_df[trades_df['result'] == 'open'].copy()
            
            # Add profit calculation placeholder
            open_df['target_profit'] = ((open_df['tp'] - open_df['entry']) / open_df['entry'] * 100).abs()
            open_df['risk'] = ((open_df['sl'] - open_df['entry']) / open_df['entry'] * 100).abs()
            
            # Format for display
            display_cols = ['symbol', 'side', 'entry', 'tp', 'sl', 'target_profit', 'risk', 'timestamp']
            display_df = open_df[display_cols].copy()
            
            # Format numbers
            display_df['entry'] = display_df['entry'].apply(lambda x: f"${x:,.2f}")
            display_df['tp'] = display_df['tp'].apply(lambda x: f"${x:,.2f}")
            display_df['sl'] = display_df['sl'].apply(lambda x: f"${x:,.2f}")
            display_df['target_profit'] = display_df['target_profit'].apply(lambda x: f"{x:.2f}%")
            display_df['risk'] = display_df['risk'].apply(lambda x: f"{x:.2f}%")
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%H:%M:%S')
            
            # Rename columns
            display_df.columns = ['Symbol', 'Side', 'Entry', 'Take Profit', 'Stop Loss', 'Target %', 'Risk %', 'Time']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Closed trades detail
        if closed_trades > 0:
            st.subheader("🔴 Closed Positions")
            
            closed_display = closed_df[['symbol', 'side', 'entry', 'exit', 'pnl', 'result', 'timestamp']].copy()
            closed_display['entry'] = closed_display['entry'].apply(lambda x: f"${x:,.2f}")
            closed_display['exit'] = closed_display['exit'].apply(lambda x: f"${x:,.2f}")
            closed_display['pnl'] = closed_display['pnl'].apply(lambda x: f"{x:.2f}%")
            closed_display['timestamp'] = pd.to_datetime(closed_display['timestamp']).dt.strftime('%H:%M:%S')
            
            closed_display.columns = ['Symbol', 'Side', 'Entry', 'Exit', 'P&L', 'Reason', 'Time']
            
            st.dataframe(closed_display, use_container_width=True, hide_index=True)
        
        # Trading statistics
        st.subheader("📈 Today's Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Get signal stats
            signal_query = '''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed
                FROM signal_log
                WHERE DATE(created_at) = DATE('now', 'localtime')
            '''
            signal_stats = pd.read_sql_query(signal_query, conn).iloc[0]
            
            st.info(f"""
            **Signal Processing**
            - Signals Received: {signal_stats['total']}
            - Signals Processed: {signal_stats['processed']}
            - Conversion Rate: {(signal_stats['processed']/signal_stats['total']*100 if signal_stats['total'] > 0 else 0):.1f}%
            """)
        
        with col2:
            # Get current settings
            settings_query = '''
                SELECT key, value FROM trading_settings
                WHERE key IN ('automated_trading_enabled', 'take_profit_strategy', 
                             'tp_level_1_pct', 'stop_loss_pct', 'max_exposure_pct')
            '''
            settings = pd.read_sql_query(settings_query, conn)
            settings_dict = dict(zip(settings['key'], settings['value']))
            
            st.success(f"""
            **Active Strategy**
            - Mode: {settings_dict.get('take_profit_strategy', 'Unknown').title()}
            - Target Profit: {settings_dict.get('tp_level_1_pct', 'N/A')}%
            - Stop Loss: {settings_dict.get('stop_loss_pct', 'N/A')}%
            - Max Exposure: {settings_dict.get('max_exposure_pct', 'N/A')}%
            """)
        
        # Timeline visualization
        if not trades_df.empty:
            st.subheader("⏰ Trading Timeline")
            
            # Create timeline chart
            fig_timeline = go.Figure()
            
            trades_df['hour'] = pd.to_datetime(trades_df['timestamp']).dt.hour
            hourly_counts = trades_df.groupby('hour').size()
            
            fig_timeline.add_trace(go.Bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                name='Trades per Hour'
            ))
            
            fig_timeline.update_layout(
                title="Trade Distribution by Hour",
                xaxis_title="Hour of Day",
                yaxis_title="Number of Trades",
                height=300
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading trades: {e}")
        st.info("Please ensure the database is properly configured")

if __name__ == "__main__":
    show_daily_trades()