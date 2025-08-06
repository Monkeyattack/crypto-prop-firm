#!/usr/bin/env python3
"""
Settings Management Interface - Configure all trading parameters from the web
"""

import streamlit as st
import sqlite3
import json
from datetime import datetime
import pandas as pd

class SettingsManager:
    def __init__(self):
        self.db_path = 'trade_log.db'
        self.init_settings_table()
    
    def init_settings_table(self):
        """Initialize settings table in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                category TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default settings if not exist
        default_settings = [
            # Trading Control
            ('automated_trading_enabled', 'false', 'Enable/disable automated trading', 'trading_control'),
            ('signal_check_interval', '900', 'Signal check interval in seconds (900 = 15 min)', 'trading_control'),
            
            # Risk Management
            ('stop_loss_pct', '5.0', 'Default stop loss percentage', 'risk_management'),
            ('max_position_size', '100', 'Maximum position size in USD', 'risk_management'),
            ('max_daily_trades', '8', 'Maximum trades per day', 'risk_management'),
            ('max_open_positions', '5', 'Maximum concurrent open positions', 'risk_management'),
            
            # Take Profit Strategy
            ('take_profit_strategy', 'scaled', 'Strategy: fixed, scaled, or trailing', 'take_profit'),
            ('tp_level_1_pct', '5.0', 'First take profit level (%)', 'take_profit'),
            ('tp_level_1_size', '0.5', 'Size to exit at first level (0.5 = 50%)', 'take_profit'),
            ('tp_level_2_pct', '7.0', 'Second take profit level (%)', 'take_profit'),
            ('tp_level_2_size', '0.3', 'Size to exit at second level (0.3 = 30%)', 'take_profit'),
            ('tp_level_3_pct', '10.0', 'Third take profit level (%)', 'take_profit'),
            ('tp_level_3_size', '0.2', 'Size to exit at third level (0.2 = 20%)', 'take_profit'),
            
            # Trailing Take Profit
            ('trailing_enabled', 'true', 'Enable trailing take profit', 'trailing'),
            ('trailing_activation_pct', '4.5', 'Activate trailing after this profit %', 'trailing'),
            ('trailing_distance_pct', '1.5', 'Trail by this percentage', 'trailing'),
            ('trailing_min_profit_pct', '3.5', 'Minimum profit to secure', 'trailing'),
            
            # Symbol Filtering
            ('symbol_filtering_enabled', 'true', 'Enable symbol risk filtering', 'symbol_filter'),
            ('min_risk_reward_ratio', '1.5', 'Minimum risk/reward ratio', 'symbol_filter'),
            ('blacklisted_symbols', 'UNIUSDT,AVAXUSDT', 'Comma-separated blacklisted symbols', 'symbol_filter'),
            ('preferred_symbols', 'DOTUSDT,BTCUSDT,SOLUSDT,ADAUSDT', 'Comma-separated preferred symbols', 'symbol_filter')
        ]
        
        for key, value, desc, category in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO trading_settings (key, value, description, category)
                VALUES (?, ?, ?, ?)
            ''', (key, value, desc, category))
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str, default=None):
        """Get a single setting value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM trading_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    
    def update_setting(self, key: str, value: str, description: str = None):
        """Update a setting value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if description:
            cursor.execute('''
                INSERT OR REPLACE INTO trading_settings (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, value, description, datetime.now()))
        else:
            cursor.execute('''
                UPDATE trading_settings 
                SET value = ?, updated_at = ? 
                WHERE key = ?
            ''', (value, datetime.now(), key))
        
        conn.commit()
        conn.close()
    
    def get_all_settings(self):
        """Get all settings grouped by category"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT key, value, description, category, updated_at 
            FROM trading_settings 
            ORDER BY category, key
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Group by category
        settings_by_category = {}
        for category in df['category'].unique():
            if category:
                settings_by_category[category] = df[df['category'] == category].to_dict('records')
        
        return settings_by_category

def display_settings_interface():
    """Display the settings management interface"""
    st.title("⚙️ Trading Settings Management")
    st.markdown("---")
    
    settings_manager = SettingsManager()
    
    # Get all settings
    all_settings = settings_manager.get_all_settings()
    
    # Trading Control Section
    st.header("🎮 Trading Control")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Automated trading toggle
        automated_trading = settings_manager.get_setting('automated_trading_enabled', 'false') == 'true'
        new_automated_trading = st.toggle("Automated Trading Enabled", value=automated_trading)
        
        if new_automated_trading != automated_trading:
            settings_manager.update_setting('automated_trading_enabled', str(new_automated_trading).lower())
            st.success("Automated trading setting updated!")
    
    with col2:
        # Signal check interval
        interval = int(settings_manager.get_setting('signal_check_interval', '900'))
        new_interval = st.selectbox(
            "Signal Check Interval",
            options=[300, 600, 900, 1800, 3600],
            format_func=lambda x: f"{x//60} minutes",
            index=[300, 600, 900, 1800, 3600].index(interval)
        )
        
        if new_interval != interval:
            settings_manager.update_setting('signal_check_interval', str(new_interval))
            st.success(f"Check interval updated to {new_interval//60} minutes!")
    
    # Risk Management Section
    st.header("🛡️ Risk Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stop_loss = float(settings_manager.get_setting('stop_loss_pct', '5.0'))
        new_stop_loss = st.number_input("Stop Loss %", min_value=1.0, max_value=20.0, value=stop_loss, step=0.5)
        
        if new_stop_loss != stop_loss:
            settings_manager.update_setting('stop_loss_pct', str(new_stop_loss))
            st.success("Stop loss updated!")
    
    with col2:
        max_position = float(settings_manager.get_setting('max_position_size', '100'))
        new_max_position = st.number_input("Max Position Size ($)", min_value=10.0, max_value=1000.0, value=max_position, step=10.0)
        
        if new_max_position != max_position:
            settings_manager.update_setting('max_position_size', str(new_max_position))
            st.success("Max position size updated!")
    
    with col3:
        max_daily = int(settings_manager.get_setting('max_daily_trades', '8'))
        new_max_daily = st.number_input("Max Daily Trades", min_value=1, max_value=50, value=max_daily)
        
        if new_max_daily != max_daily:
            settings_manager.update_setting('max_daily_trades', str(new_max_daily))
            st.success("Max daily trades updated!")
    
    # Take Profit Strategy Section
    st.header("📈 Take Profit Strategy")
    
    strategy = settings_manager.get_setting('take_profit_strategy', 'scaled')
    new_strategy = st.selectbox(
        "Take Profit Strategy",
        options=['fixed', 'scaled', 'trailing'],
        index=['fixed', 'scaled', 'trailing'].index(strategy)
    )
    
    if new_strategy != strategy:
        settings_manager.update_setting('take_profit_strategy', new_strategy)
        st.success("Take profit strategy updated!")
    
    # Scaled Exit Levels
    if new_strategy == 'scaled':
        st.subheader("Scaled Exit Levels")
        
        col1, col2, col3 = st.columns(3)
        
        # Level 1
        with col1:
            st.markdown("**Level 1**")
            tp1_pct = float(settings_manager.get_setting('tp_level_1_pct', '5.0'))
            tp1_size = float(settings_manager.get_setting('tp_level_1_size', '0.5'))
            
            new_tp1_pct = st.number_input("TP %", min_value=1.0, max_value=20.0, value=tp1_pct, step=0.5, key="tp1_pct")
            new_tp1_size = st.slider("Exit Size", min_value=0.1, max_value=1.0, value=tp1_size, step=0.1, key="tp1_size")
            
            if new_tp1_pct != tp1_pct:
                settings_manager.update_setting('tp_level_1_pct', str(new_tp1_pct))
            if new_tp1_size != tp1_size:
                settings_manager.update_setting('tp_level_1_size', str(new_tp1_size))
        
        # Level 2
        with col2:
            st.markdown("**Level 2**")
            tp2_pct = float(settings_manager.get_setting('tp_level_2_pct', '7.0'))
            tp2_size = float(settings_manager.get_setting('tp_level_2_size', '0.3'))
            
            new_tp2_pct = st.number_input("TP %", min_value=1.0, max_value=20.0, value=tp2_pct, step=0.5, key="tp2_pct")
            new_tp2_size = st.slider("Exit Size", min_value=0.1, max_value=1.0, value=tp2_size, step=0.1, key="tp2_size")
            
            if new_tp2_pct != tp2_pct:
                settings_manager.update_setting('tp_level_2_pct', str(new_tp2_pct))
            if new_tp2_size != tp2_size:
                settings_manager.update_setting('tp_level_2_size', str(new_tp2_size))
        
        # Level 3
        with col3:
            st.markdown("**Level 3**")
            tp3_pct = float(settings_manager.get_setting('tp_level_3_pct', '10.0'))
            tp3_size = float(settings_manager.get_setting('tp_level_3_size', '0.2'))
            
            new_tp3_pct = st.number_input("TP %", min_value=1.0, max_value=20.0, value=tp3_pct, step=0.5, key="tp3_pct")
            new_tp3_size = st.slider("Exit Size", min_value=0.1, max_value=1.0, value=tp3_size, step=0.1, key="tp3_size")
            
            if new_tp3_pct != tp3_pct:
                settings_manager.update_setting('tp_level_3_pct', str(new_tp3_pct))
            if new_tp3_size != tp3_size:
                settings_manager.update_setting('tp_level_3_size', str(new_tp3_size))
    
    # Trailing Take Profit Section
    st.header("📊 Trailing Take Profit")
    
    trailing_enabled = settings_manager.get_setting('trailing_enabled', 'true') == 'true'
    new_trailing_enabled = st.toggle("Enable Trailing Take Profit", value=trailing_enabled)
    
    if new_trailing_enabled != trailing_enabled:
        settings_manager.update_setting('trailing_enabled', str(new_trailing_enabled).lower())
        st.success("Trailing take profit setting updated!")
    
    if new_trailing_enabled:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            activation = float(settings_manager.get_setting('trailing_activation_pct', '4.5'))
            new_activation = st.number_input("Activation %", min_value=1.0, max_value=20.0, value=activation, step=0.5)
            
            if new_activation != activation:
                settings_manager.update_setting('trailing_activation_pct', str(new_activation))
        
        with col2:
            trail_distance = float(settings_manager.get_setting('trailing_distance_pct', '1.5'))
            new_trail_distance = st.number_input("Trail Distance %", min_value=0.5, max_value=5.0, value=trail_distance, step=0.5)
            
            if new_trail_distance != trail_distance:
                settings_manager.update_setting('trailing_distance_pct', str(new_trail_distance))
        
        with col3:
            min_profit = float(settings_manager.get_setting('trailing_min_profit_pct', '3.5'))
            new_min_profit = st.number_input("Min Profit %", min_value=1.0, max_value=10.0, value=min_profit, step=0.5)
            
            if new_min_profit != min_profit:
                settings_manager.update_setting('trailing_min_profit_pct', str(new_min_profit))
    
    # Symbol Filtering Section
    st.header("🎯 Symbol Filtering")
    
    symbol_filtering = settings_manager.get_setting('symbol_filtering_enabled', 'true') == 'true'
    new_symbol_filtering = st.toggle("Enable Symbol Filtering", value=symbol_filtering)
    
    if new_symbol_filtering != symbol_filtering:
        settings_manager.update_setting('symbol_filtering_enabled', str(new_symbol_filtering).lower())
        st.success("Symbol filtering setting updated!")
    
    if new_symbol_filtering:
        # Blacklisted symbols
        blacklisted = settings_manager.get_setting('blacklisted_symbols', '')
        new_blacklisted = st.text_area("Blacklisted Symbols (comma-separated)", value=blacklisted)
        
        if new_blacklisted != blacklisted:
            settings_manager.update_setting('blacklisted_symbols', new_blacklisted)
            st.success("Blacklisted symbols updated!")
        
        # Preferred symbols
        preferred = settings_manager.get_setting('preferred_symbols', '')
        new_preferred = st.text_area("Preferred Symbols (comma-separated)", value=preferred)
        
        if new_preferred != preferred:
            settings_manager.update_setting('preferred_symbols', new_preferred)
            st.success("Preferred symbols updated!")
    
    # Display all settings
    with st.expander("📋 View All Settings", expanded=False):
        st.subheader("Current Settings")
        
        for category, settings in all_settings.items():
            st.markdown(f"**{category.replace('_', ' ').title()}**")
            
            settings_df = pd.DataFrame(settings)
            if not settings_df.empty:
                display_df = settings_df[['key', 'value', 'description', 'updated_at']]
                st.dataframe(display_df, use_container_width=True)

if __name__ == "__main__":
    display_settings_interface()