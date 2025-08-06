#!/usr/bin/env python3
"""
Market Conditions Dashboard - Volume and Volatility Analysis
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from market_analyzer import MarketAnalyzer

def show_market_conditions():
    """Display market conditions analysis"""
    st.title("🌊 Market Conditions Analysis")
    st.markdown("### Volume, Volatility & Trading Opportunities")
    st.markdown("---")
    
    # Initialize analyzer
    analyzer = MarketAnalyzer()
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh Analysis", type="primary"):
            with st.spinner("Analyzing market conditions..."):
                # Get symbols to analyze
                symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 
                          'MATICUSDT', 'AVAXUSDT', 'LINKUSDT']
                
                # Run analysis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                for symbol in symbols:
                    try:
                        loop.run_until_complete(analyzer.analyze_symbol(symbol))
                    except Exception as e:
                        st.error(f"Error analyzing {symbol}: {e}")
                
                loop.close()
                st.success("Analysis updated!")
                st.rerun()
    
    # Load latest market conditions
    try:
        conn = sqlite3.connect('trade_log.db')
        
        # Get latest analysis for all symbols
        query = '''
            SELECT DISTINCT m1.* 
            FROM market_conditions m1
            INNER JOIN (
                SELECT symbol, MAX(timestamp) as max_time
                FROM market_conditions
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY symbol
            ) m2 ON m1.symbol = m2.symbol AND m1.timestamp = m2.max_time
            ORDER BY m1.overall_score DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            st.warning("No recent market analysis available. Click 'Refresh Analysis' to start.")
            return
        
        # Market Overview
        st.header("📊 Market Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        avg_volatility = df['volatility_1h'].mean()
        high_volume_count = len(df[df['volume_ratio'] > 1.5])
        strong_signals = len(df[df['overall_score'] > 70])
        best_opportunity = df.iloc[0]['symbol'] if not df.empty else 'N/A'
        
        with col1:
            st.metric("Avg Volatility (1h)", f"{avg_volatility:.2f}%", 
                     "Good for trading" if 0.5 <= avg_volatility <= 2.0 else "Challenging")
        
        with col2:
            st.metric("High Volume Pairs", high_volume_count, 
                     f"Out of {len(df)} analyzed")
        
        with col3:
            st.metric("Strong Opportunities", strong_signals)
        
        with col4:
            st.metric("Best Opportunity", best_opportunity)
        
        # Trading Opportunities Table
        st.header("🎯 Trading Opportunities")
        
        # Prepare display data
        display_df = df[['symbol', 'overall_score', 'volume_ratio', 'volatility_1h', 
                        'volume_trend', 'trade_recommendation', 'position_size_multiplier']].copy()
        
        # Add visual indicators
        display_df['Score'] = display_df['overall_score'].apply(lambda x: f"{'🟢' if x >= 70 else '🟡' if x >= 40 else '🔴'} {x:.1f}")
        display_df['Volume'] = display_df.apply(lambda row: f"📊 {row['volume_ratio']:.2f}x {'📈' if row['volume_trend'] == 'increasing' else '📉' if row['volume_trend'] == 'decreasing' else '➡️'}", axis=1)
        display_df['Volatility'] = display_df['volatility_1h'].apply(lambda x: f"{'🎯' if 0.5 <= x <= 2.0 else '⚠️'} {x:.2f}%")
        display_df['Action'] = display_df['trade_recommendation'].apply(
            lambda x: '💚 Strong Buy' if x == 'strong_buy' else 
                     '✅ Buy' if x == 'buy' else 
                     '⚪ Neutral' if x == 'neutral' else 
                     '❌ Avoid'
        )
        display_df['Position Size'] = display_df['position_size_multiplier'].apply(lambda x: f"{x:.1f}x")
        
        # Show top opportunities
        st.dataframe(
            display_df[['symbol', 'Score', 'Volume', 'Volatility', 'Action', 'Position Size']],
            use_container_width=True,
            hide_index=True
        )
        
        # Detailed Analysis Tabs
        st.header("📈 Detailed Analysis")
        
        tabs = st.tabs(["Volume Analysis", "Volatility Patterns", "Score Breakdown", "Trading Adjustments"])
        
        with tabs[0]:
            # Volume Analysis
            st.subheader("📊 Volume Analysis")
            
            # Volume comparison chart
            fig_volume = go.Figure()
            
            # Sort by volume ratio
            volume_sorted = df.sort_values('volume_ratio', ascending=True)
            
            fig_volume.add_trace(go.Bar(
                x=volume_sorted['volume_ratio'],
                y=volume_sorted['symbol'],
                orientation='h',
                marker_color=['green' if x > 1.5 else 'yellow' if x > 1 else 'red' 
                             for x in volume_sorted['volume_ratio']],
                text=volume_sorted['volume_ratio'].apply(lambda x: f"{x:.2f}x"),
                textposition='outside'
            ))
            
            fig_volume.update_layout(
                title="Volume Ratio (Current vs Average)",
                xaxis_title="Volume Ratio",
                yaxis_title="Symbol",
                height=400,
                xaxis=dict(range=[0, max(3, volume_sorted['volume_ratio'].max() * 1.1)])
            )
            
            st.plotly_chart(fig_volume, use_container_width=True)
            
            # Volume trend
            col1, col2 = st.columns(2)
            
            with col1:
                trend_counts = df['volume_trend'].value_counts()
                fig_trend = go.Figure(data=[
                    go.Pie(labels=trend_counts.index, values=trend_counts.values,
                          marker_colors=['green', 'red', 'gray'])
                ])
                fig_trend.update_layout(title="Volume Trends")
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with col2:
                st.info("""
                **Volume Insights:**
                - 🟢 Ratio > 1.5x: Strong momentum
                - 🟡 Ratio 1-1.5x: Normal activity
                - 🔴 Ratio < 1x: Below average
                
                High volume indicates:
                - Stronger price movements
                - Better liquidity
                - More reliable signals
                """)
        
        with tabs[1]:
            # Volatility Patterns
            st.subheader("🌊 Volatility Patterns")
            
            # Volatility distribution
            fig_volatility = make_subplots(
                rows=1, cols=2,
                subplot_titles=("1-Hour Volatility", "Volatility vs Score")
            )
            
            # Bar chart of volatility
            vol_sorted = df.sort_values('volatility_1h', ascending=True)
            fig_volatility.add_trace(
                go.Bar(
                    x=vol_sorted['volatility_1h'],
                    y=vol_sorted['symbol'],
                    orientation='h',
                    marker_color=['green' if 0.5 <= x <= 2.0 else 'orange' if x < 0.5 else 'red' 
                                 for x in vol_sorted['volatility_1h']],
                    text=vol_sorted['volatility_1h'].apply(lambda x: f"{x:.2f}%"),
                    textposition='outside'
                ),
                row=1, col=1
            )
            
            # Scatter plot: volatility vs score
            fig_volatility.add_trace(
                go.Scatter(
                    x=df['volatility_1h'],
                    y=df['overall_score'],
                    mode='markers+text',
                    text=df['symbol'],
                    textposition='top center',
                    marker=dict(
                        size=df['volume_ratio'] * 10,
                        color=df['overall_score'],
                        colorscale='RdYlGn',
                        showscale=True
                    )
                ),
                row=1, col=2
            )
            
            fig_volatility.update_xaxes(title_text="Volatility %", row=1, col=1)
            fig_volatility.update_xaxes(title_text="Volatility %", row=1, col=2)
            fig_volatility.update_yaxes(title_text="Overall Score", row=1, col=2)
            
            fig_volatility.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_volatility, use_container_width=True)
            
            st.info("""
            **Optimal Volatility for Micro-Profits:**
            - 🟢 0.5-2.0%: Perfect for 0.75% targets
            - 🟡 < 0.5%: Too stable, smaller targets needed
            - 🔴 > 2.0%: High risk, wider stops required
            """)
        
        with tabs[2]:
            # Score Breakdown
            st.subheader("🎯 Score Breakdown")
            
            # Create radar chart for top symbols
            top_symbols = df.nlargest(6, 'overall_score')
            
            categories = ['Volume Score', 'Volatility Score', 'Momentum Score', 'Overall Score']
            
            fig_radar = go.Figure()
            
            for _, row in top_symbols.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[row['volume_score'], row['volatility_score'], 
                       row['momentum_score'], row['overall_score']],
                    theta=categories,
                    fill='toself',
                    name=row['symbol']
                ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="Market Condition Scores by Symbol"
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
            
            # Score distribution
            col1, col2 = st.columns(2)
            
            with col1:
                score_bins = pd.cut(df['overall_score'], bins=[0, 40, 60, 80, 100], 
                                  labels=['Poor', 'Fair', 'Good', 'Excellent'])
                score_dist = score_bins.value_counts()
                
                fig_dist = go.Figure(data=[
                    go.Bar(x=score_dist.index, y=score_dist.values,
                          marker_color=['red', 'yellow', 'lightgreen', 'green'])
                ])
                fig_dist.update_layout(title="Market Condition Distribution")
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                st.success(f"""
                **Current Market Status:**
                - {len(df[df['overall_score'] >= 70])} Excellent opportunities
                - {len(df[(df['overall_score'] >= 40) & (df['overall_score'] < 70)])} Fair conditions
                - {len(df[df['overall_score'] < 40])} Poor conditions
                
                Focus on symbols with scores > 70 for best results!
                """)
        
        with tabs[3]:
            # Trading Adjustments
            st.subheader("⚙️ Dynamic Trading Adjustments")
            
            adjustments_df = df[['symbol', 'position_size_multiplier', 
                               'recommended_tp_adjustment', 'recommended_sl_adjustment',
                               'volatility_1h', 'overall_score']].copy()
            
            # Add calculated values
            base_tp = 0.75  # Base target profit
            adjustments_df['Adjusted TP%'] = adjustments_df['recommended_tp_adjustment'].apply(lambda x: f"{base_tp * x:.2f}%")
            adjustments_df['Position Size'] = adjustments_df['position_size_multiplier'].apply(lambda x: f"{x:.1f}x")
            adjustments_df['Stop Adjust'] = adjustments_df['recommended_sl_adjustment'].apply(lambda x: f"{x:.1f}x")
            
            # Format for display
            display_adj = adjustments_df[['symbol', 'Position Size', 'Adjusted TP%', 
                                         'Stop Adjust', 'volatility_1h', 'overall_score']]
            display_adj.columns = ['Symbol', 'Position Size', 'Target Profit', 
                                  'Stop Loss Adj', 'Volatility', 'Score']
            
            st.dataframe(display_adj, use_container_width=True, hide_index=True)
            
            st.info("""
            **How Adjustments Work:**
            
            📊 **Position Size**: 
            - 2.0x in excellent conditions (score > 80)
            - 0.5x in poor conditions (score < 40)
            
            🎯 **Take Profit**: 
            - Tighter in low volatility
            - Wider in high volatility
            
            🛡️ **Stop Loss**: 
            - Adjusted based on volatility
            - Wider stops in volatile markets
            """)
        
        # Historical Performance
        st.header("📊 Historical Market Patterns")
        
        # Get volume history
        try:
            volume_history = pd.read_sql_query('''
                SELECT symbol, 
                       datetime(timestamp) as timestamp, 
                       CAST(volume_1h as REAL) as volume_1h, 
                       CAST(price as REAL) as price
                FROM volume_history
                WHERE datetime(timestamp) > datetime('now', '-24 hours')
                ORDER BY timestamp
            ''', conn)
        except Exception as e:
            st.warning(f"No volume history data available: {e}")
            volume_history = pd.DataFrame()
        
        if not volume_history.empty:
            # Convert timestamp to proper datetime and ensure numeric data
            try:
                volume_history['timestamp'] = pd.to_datetime(volume_history['timestamp'])
                volume_history['volume_1h'] = pd.to_numeric(volume_history['volume_1h'], errors='coerce')
                volume_history['price'] = pd.to_numeric(volume_history['price'], errors='coerce')
                
                # Remove any rows with NaN values
                volume_history = volume_history.dropna()
                
                if not volume_history.empty:
                    # Volume patterns over time
                    fig_history = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        subplot_titles=("Volume Patterns (24h)", "Price Movement")
                    )
                    
                    for symbol in volume_history['symbol'].unique()[:3]:  # Top 3 symbols
                        symbol_data = volume_history[volume_history['symbol'] == symbol]
                        
                        if len(symbol_data) > 0:
                            # Volume
                            fig_history.add_trace(
                                go.Scatter(
                                    x=symbol_data['timestamp'].tolist(),
                                    y=symbol_data['volume_1h'].tolist(),
                                    name=f"{symbol} Volume",
                                    mode='lines'
                                ),
                                row=1, col=1
                            )
                            
                            # Price
                            fig_history.add_trace(
                                go.Scatter(
                                    x=symbol_data['timestamp'].tolist(),
                                    y=symbol_data['price'].tolist(),
                                    name=f"{symbol} Price",
                                    mode='lines'
                                ),
                                row=2, col=1
                            )
                    
                    fig_history.update_layout(height=600)
                    st.plotly_chart(fig_history, use_container_width=True)
                else:
                    st.info("No valid historical data to display")
            except Exception as e:
                st.warning(f"Error creating historical charts: {e}")
        else:
            st.info("No historical market data available yet. Run the market analyzer multiple times to build history.")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading market data: {e}")
        st.info("Please ensure the market analyzer has been run at least once")

if __name__ == "__main__":
    show_market_conditions()