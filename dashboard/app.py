
import streamlit as st
import sys
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config import Config
from database import DatabaseManager, Trade
from auth import GoogleAuthManager
from live_trading import LiveTradingManager, LiveTradeConfig, TradingMode

# Initialize configuration and logging
Config.setup_logging()
Config.validate_config()

# Initialize database manager
db = DatabaseManager()

# Initialize authentication
auth = GoogleAuthManager()

# Initialize live trading manager
trading_mode = os.getenv('TRADING_MODE', 'paper')
live_config = LiveTradeConfig(
    mode=TradingMode(trading_mode),
    exchange=os.getenv('EXCHANGE', 'binance'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'),
    testnet=os.getenv('TESTNET', 'true').lower() == 'true',
    max_position_size_usd=float(os.getenv('MAX_POSITION_SIZE_USD', '25.0')),
    daily_loss_limit_usd=float(os.getenv('DAILY_LOSS_LIMIT_USD', '10.0')),
    max_daily_trades=int(os.getenv('MAX_DAILY_TRADES', '5')),
    min_account_balance=float(os.getenv('MIN_ACCOUNT_BALANCE', '500.0'))
)
live_trader = LiveTradingManager(live_config)

st.set_page_config(
    page_title="Crypto Paper Trading Dashboard",
    page_icon="📊",
    layout="wide"
)

# Import backtesting modules
try:
    from simple_backtesting_page import show_backtesting_analysis
    from signal_analysis import display_signal_analysis
    BACKTESTING_AVAILABLE = True
except ImportError:
    BACKTESTING_AVAILABLE = False

# Import signal monitoring
try:
    from signal_monitoring import show_signal_monitoring
    SIGNAL_MONITORING_AVAILABLE = True
except ImportError:
    SIGNAL_MONITORING_AVAILABLE = False

# Import prop firm dashboard
try:
    from prop_firm_dashboard import display_prop_firm_dashboard
    from prop_firm_integration import show_integrated_dashboard
    PROP_FIRM_AVAILABLE = True
except ImportError:
    PROP_FIRM_AVAILABLE = False

# Require authentication - DISABLED for development
# if not auth.require_auth():
#     st.stop()

st.title("📊 Crypto Paper Trading Dashboard")
st.sidebar.title("Navigation")

# Show user info and logout
auth.show_user_info()

# Trading mode indicator
trading_status = live_trader.get_trading_status()
mode_color = {
    "paper": "🟢",
    "testnet": "🟡", 
    "live": "🔴",
    "hybrid": "🟠"
}.get(trading_status["mode"], "⚪")

st.sidebar.markdown(f"### {mode_color} Trading Mode: **{trading_status['mode'].upper()}**")

if trading_status["mode"] != "paper":
    st.sidebar.markdown(f"**Exchange:** {trading_status['exchange']}")
    if trading_status.get("testnet"):
        st.sidebar.markdown("🧪 **TESTNET MODE**")
    
    # Daily limits
    st.sidebar.markdown("#### Daily Limits")
    st.sidebar.progress(trading_status["daily_trades"] / trading_status["daily_limit"])
    st.sidebar.markdown(f"Trades: {trading_status['daily_trades']}/{trading_status['daily_limit']}")
    
    pnl_color = "red" if trading_status["daily_pnl"] < 0 else "green"
    st.sidebar.markdown(f"P&L: <span style='color:{pnl_color}'>${trading_status['daily_pnl']:.2f}</span>", unsafe_allow_html=True)

# Emergency stop button
if trading_status["mode"] in ["live", "hybrid"]:
    if trading_status["emergency_stop"]:
        if st.sidebar.button("🟢 Resume Trading", type="primary"):
            live_trader.disable_emergency_stop()
            st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY STOP", type="secondary"):
            live_trader.enable_emergency_stop()
            st.rerun()

st.sidebar.markdown("---")

# Sidebar navigation
navigation_options = ["Dashboard", "Trade Management", "Performance Analysis", "💼 Prop Firm", "Live Trading", "Settings"]

if SIGNAL_MONITORING_AVAILABLE:
    navigation_options.insert(4, "📡 Signal Monitoring")

if BACKTESTING_AVAILABLE:
    navigation_options.extend(["📊 Backtesting Analysis", "🔍 Signal Analysis"])

page = st.sidebar.selectbox("Choose a page", navigation_options)

if page == "Dashboard":
    # Overall Statistics
    st.header("Portfolio Overview")
    
    # Add prop firm integration if available
    if PROP_FIRM_AVAILABLE:
        try:
            from prop_firm_integration import PropFirmDashboardIntegration
            prop_integration = PropFirmDashboardIntegration()
            prop_integration.show_prop_firm_status_banner()
            st.markdown("---")
        except Exception as e:
            st.warning(f"Prop firm integration unavailable: {e}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Get performance stats
    stats = db.get_performance_stats()
    current_capital = stats.get('current_capital', Config.INITIAL_CAPITAL)
    total_pnl = stats.get('total_pnl', 0)
    win_rate = stats.get('win_rate', 0)
    total_trades = stats.get('total_trades', 0)
    
    with col1:
        st.metric("Current Capital", f"${current_capital:.2f}", 
                 delta=f"${total_pnl:.2f}" if total_pnl != 0 else None)
    
    with col2:
        st.metric("Total Trades", total_trades)
    
    with col3:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col4:
        roi = ((current_capital - Config.INITIAL_CAPITAL) / Config.INITIAL_CAPITAL * 100)
        st.metric("ROI", f"{roi:.2f}%")
    
    # Capital Chart
    st.subheader("Capital History")
    capital_df = db.get_capital_df()
    if not capital_df.empty:
        fig = px.line(capital_df, x='timestamp', y='value', 
                     title='Portfolio Value Over Time')
        fig.update_layout(xaxis_title='Date', yaxis_title='Capital ($)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No capital history available yet.")
    
    # Capital by Symbol
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Capital by Symbol")
        symbol_df = db.get_capital_by_symbol_df()
        if not symbol_df.empty:
            st.dataframe(symbol_df[['symbol', 'value', 'timestamp']], 
                        use_container_width=True)
        else:
            st.info("No symbol-specific capital data available yet.")
    
    with col2:
        st.subheader("Open Positions")
        trades_df = db.get_trades_df()
        if not trades_df.empty:
            open_trades = trades_df[trades_df['result'] == 'open']
            if not open_trades.empty:
                st.dataframe(open_trades[['symbol', 'side', 'entry', 'tp', 'sl', 'timestamp']], 
                           use_container_width=True)
            else:
                st.info("No open positions.")
        else:
            st.info("No trades available yet.")
    
    # Add prop firm dashboard integration
    if PROP_FIRM_AVAILABLE:
        st.markdown("---")
        st.subheader("💼 Prop Firm Integration")
        
        try:
            prop_integration.show_recent_prop_decisions(limit=5)
        except Exception as e:
            st.error(f"Error loading prop firm data: {e}")

elif page == "Trade Management":
    st.header("Trade Management")
    
    # Add new trade form
    with st.expander("Add New Trade", expanded=False):
        with st.form("new_trade_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                symbol = st.text_input("Symbol", placeholder="BTCUSDT")
                side = st.selectbox("Side", ["Buy", "Sell"])
                entry = st.number_input("Entry Price", min_value=0.0, step=0.01)
            
            with col2:
                tp = st.number_input("Take Profit", min_value=0.0, step=0.01)
                sl = st.number_input("Stop Loss", min_value=0.0, step=0.01)
            
            submitted = st.form_submit_button("Add Trade")
            
            if submitted:
                if all([symbol, entry > 0, tp > 0, sl > 0]):
                    trade = Trade(
                        symbol=symbol.upper(),
                        side=side,
                        entry=entry,
                        tp=tp,
                        sl=sl
                    )
                    
                    errors = trade.validate()
                    if errors:
                        st.error(f"Validation errors: {', '.join(errors)}")
                    else:
                        if db.add_trade(trade):
                            st.success(f"Trade added: {symbol} {side} @ {entry}")
                            st.rerun()
                        else:
                            st.error("Failed to add trade. Check logs for details.")
                else:
                    st.error("Please fill in all required fields with positive values.")
    
    # Recent Trades
    st.subheader("Recent Trades")
    trades_df = db.get_trades_df(limit=20)
    if not trades_df.empty:
        # Add actions for open trades
        display_df = trades_df.copy()
        
        # Format timestamps
        if 'timestamp' in display_df.columns:
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(display_df, use_container_width=True)
        
        # Close trade section
        open_trades = trades_df[trades_df['result'] == 'open']
        if not open_trades.empty:
            st.subheader("Close Open Trade")
            with st.form("close_trade_form"):
                trade_options = {f"{row['symbol']} {row['side']} @ {row['entry']} (ID: {row['id']})": row['id'] 
                               for _, row in open_trades.iterrows()}
                selected_trade = st.selectbox("Select Trade to Close", list(trade_options.keys()))
                exit_price = st.number_input("Exit Price", min_value=0.0, step=0.01)
                result = st.selectbox("Close Reason", ["tp", "sl", "manual"])
                
                if st.form_submit_button("Close Trade"):
                    if exit_price > 0 and selected_trade:
                        trade_id = trade_options[selected_trade]
                        if db.close_trade(trade_id, exit_price, result):
                            st.success(f"Trade {trade_id} closed successfully")
                            st.rerun()
                        else:
                            st.error("Failed to close trade")
    else:
        st.info("No trades available yet.")

elif page == "Performance Analysis":
    st.header("Performance Analysis")
    
    # Performance metrics
    stats = db.get_performance_stats()
    
    if stats:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Trading Statistics")
            st.metric("Total Trades", stats.get('total_trades', 0))
            st.metric("Winning Trades", stats.get('winning_trades', 0))
            st.metric("Losing Trades", stats.get('losing_trades', 0))
            st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        
        with col2:
            st.subheader("Financial Metrics")
            st.metric("Total PnL", f"${stats.get('total_pnl', 0):.2f}")
            st.metric("Average PnL", f"${stats.get('avg_pnl', 0):.2f}")
            roi = ((stats.get('current_capital', Config.INITIAL_CAPITAL) - Config.INITIAL_CAPITAL) / Config.INITIAL_CAPITAL * 100)
            st.metric("ROI", f"{roi:.2f}%")
        
        # PnL Distribution
        trades_df = db.get_trades_df()
        if not trades_df.empty and 'pnl' in trades_df.columns:
            closed_trades = trades_df[trades_df['result'] != 'open']
            if not closed_trades.empty:
                st.subheader("PnL Distribution")
                fig = px.histogram(closed_trades, x='pnl', nbins=20, 
                                 title='Trade PnL Distribution')
                st.plotly_chart(fig, use_container_width=True)
                
                # Symbol performance
                if 'symbol' in closed_trades.columns:
                    st.subheader("Performance by Symbol")
                    symbol_pnl = closed_trades.groupby('symbol')['pnl'].sum().reset_index()
                    fig = px.bar(symbol_pnl, x='symbol', y='pnl', 
                               title='Total PnL by Symbol')
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for performance analysis yet.")

elif page == "Live Trading":
    st.header("🚀 Live Trading Management")
    
    # Current status
    trading_status = live_trader.get_trading_status()
    
    # Status overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        mode_emoji = {"paper": "🟢", "testnet": "🟡", "live": "🔴", "hybrid": "🟠"}.get(trading_status["mode"], "⚪")
        st.metric("Trading Mode", f"{mode_emoji} {trading_status['mode'].upper()}")
    
    with col2:
        st.metric("Daily Trades", f"{trading_status['daily_trades']}/{trading_status['daily_limit']}")
    
    with col3:
        pnl_delta = f"${trading_status['daily_pnl']:.2f}" if trading_status['daily_pnl'] != 0 else None
        st.metric("Daily P&L", f"${trading_status['daily_pnl']:.2f}", delta=pnl_delta)
    
    with col4:
        if trading_status.get("account_balance"):
            st.metric("Account Balance", f"${trading_status['account_balance']:.2f}")
        else:
            st.metric("Mode", "Paper Trading")
    
    # Trading mode configuration
    st.subheader("📊 Trading Mode Configuration")
    
    # Safety warning for live trading
    if trading_status["mode"] == "live":
        st.error("⚠️ **LIVE TRADING MODE** - You are trading with real money!")
    elif trading_status["mode"] == "testnet":
        st.warning("🧪 **TESTNET MODE** - Using exchange testnet with fake money")
    elif trading_status["mode"] == "hybrid":
        st.info("🔄 **HYBRID MODE** - Paper for new strategies, live for proven ones")
    else:
        st.success("📝 **PAPER TRADING** - Virtual money, no risk")
    
    # Mode transition guide
    with st.expander("📋 Trading Mode Transition Guide"):
        current_mode = trading_status["mode"]
        
        if current_mode == "paper":
            st.markdown("""
            ### 🎯 Ready for Next Step?
            
            **Before moving to testnet:**
            - ✅ Profitable for 30+ days
            - ✅ 60%+ win rate
            - ✅ Following risk management rules
            - ✅ 50+ completed trades
            
            **Next step:** Switch to `TRADING_MODE=testnet` in your .env file
            """)
        
        elif current_mode == "testnet":
            st.markdown("""
            ### 🧪 Testnet Phase
            
            **Test these features:**
            - ✅ API connection works
            - ✅ Orders execute correctly
            - ✅ Stop losses trigger
            - ✅ Take profits execute
            
            **Next step:** Switch to `TRADING_MODE=live` with small positions
            """)
        
        elif current_mode == "live":
            st.markdown("""
            ### 💰 Live Trading Active
            
            **Safety reminders:**
            - 🔴 Using real money
            - 📏 Keep positions small
            - 🛑 Use emergency stop if needed
            - 📊 Monitor performance closely
            
            **Scale up only if consistently profitable**
            """)
    
    # Risk management settings
    st.subheader("🛡️ Risk Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Position Limits")
        st.metric("Max Position Size", f"${live_config.max_position_size_usd:.2f}")
        st.metric("Daily Loss Limit", f"${live_config.daily_loss_limit_usd:.2f}")
        st.metric("Max Daily Trades", live_config.max_daily_trades)
    
    with col2:
        st.markdown("#### Exchange Settings")
        st.metric("Exchange", trading_status["exchange"])
        st.metric("Testnet", "Yes" if trading_status.get("testnet") else "No")
        if trading_status.get("account_balance"):
            st.metric("Min Balance", f"${live_config.min_account_balance:.2f}")
    
    # Performance comparison
    st.subheader("📈 Performance Tracking")
    
    if trading_status["mode"] != "paper":
        # Show both paper and live performance
        stats = db.get_performance_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Paper Trading Results")
            st.metric("Total Trades", stats.get('total_trades', 0))
            st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
            st.metric("Total P&L", f"${stats.get('total_pnl', 0):.2f}")
        
        with col2:
            st.markdown("#### Live Trading Results")
            st.metric("Daily P&L", f"${trading_status['daily_pnl']:.2f}")
            st.metric("Daily Trades", trading_status['daily_trades'])
            if trading_status.get("account_balance"):
                st.metric("Live Balance", f"${trading_status['account_balance']:.2f}")
    
    # Manual trade execution
    st.subheader("🎯 Manual Trade Execution")
    
    with st.form("manual_live_trade"):
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Symbol", placeholder="BTCUSDT")
            side = st.selectbox("Side", ["Buy", "Sell"])
            entry = st.number_input("Entry Price", min_value=0.0, step=0.01)
        
        with col2:
            tp = st.number_input("Take Profit", min_value=0.0, step=0.01)
            sl = st.number_input("Stop Loss", min_value=0.0, step=0.01)
        
        submitted = st.form_submit_button("Execute Trade")
        
        if submitted:
            if all([symbol, entry > 0, tp > 0, sl > 0]):
                signal_data = {
                    "symbol": symbol.upper(),
                    "side": side,
                    "entry": entry,
                    "tp": tp,
                    "sl": sl
                }
                
                # Execute through live trading manager
                result = live_trader.execute_trade(signal_data)
                
                if result["success"]:
                    mode = "LIVE" if trading_status["mode"] == "live" else trading_status["mode"].upper()
                    st.success(f"✅ {mode} Trade executed: {result.get('message', 'Trade successful')}")
                    st.rerun()
                else:
                    st.error(f"❌ Trade failed: {result.get('reason', 'Unknown error')}")
            else:
                st.error("Please fill in all fields with positive values")
    
    # Emergency controls
    if trading_status["mode"] in ["live", "hybrid"]:
        st.subheader("🚨 Emergency Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if trading_status["emergency_stop"]:
                st.error("🛑 **EMERGENCY STOP ACTIVE** - All trading halted")
                if st.button("🟢 Resume Trading", type="primary"):
                    live_trader.disable_emergency_stop()
                    st.success("Trading resumed")
                    st.rerun()
            else:
                if st.button("🛑 Emergency Stop All Trading", type="secondary"):
                    live_trader.enable_emergency_stop()
                    st.error("🛑 Emergency stop activated!")
                    st.rerun()
        
        with col2:
            st.markdown("#### Safety Features")
            st.markdown("- ✅ Daily loss limits")
            st.markdown("- ✅ Position size limits") 
            st.markdown("- ✅ Trade frequency limits")
            st.markdown("- ✅ Emergency stop")
            st.markdown("- ✅ Account balance monitoring")

elif page == "📡 Signal Monitoring":
    if SIGNAL_MONITORING_AVAILABLE:
        try:
            show_signal_monitoring()
        except Exception as e:
            st.error(f"Error loading signal monitoring: {e}")
            st.info("The signal monitoring system may need to be initialized first.")
    else:
        st.error("Signal monitoring module not available")

elif page == "📊 Backtesting Analysis":
    if BACKTESTING_AVAILABLE:
        try:
            # Run backtesting analysis
            show_backtesting_analysis()
        except Exception as e:
            st.error(f"Error loading backtesting dashboard: {e}")
            st.markdown("### Backtesting Dashboard Unavailable")
            st.info("The backtesting analysis dashboard requires additional setup. Please ensure all backtesting modules are properly installed.")
    else:
        st.error("Backtesting modules not available")

elif page == "🔍 Signal Analysis":
    if BACKTESTING_AVAILABLE:
        try:
            # Import and run signal analysis
            display_signal_analysis()
        except Exception as e:
            st.error(f"Error loading signal analysis: {e}")
            st.markdown("### Signal Analysis Unavailable")
            st.info("The signal analysis dashboard requires access to historical signal data.")
    else:
        st.error("Signal analysis modules not available")

elif page == "💼 Prop Firm":
    if PROP_FIRM_AVAILABLE:
        try:
            # Show integrated prop firm dashboard
            show_integrated_dashboard()
        except Exception as e:
            st.error(f"Error loading prop firm dashboard: {e}")
            st.markdown("### Prop Firm Dashboard Unavailable")
            st.info("The prop firm dashboard requires the PropFirmManager module and database setup.")
            
            # Fallback to original prop firm dashboard
            try:
                st.markdown("---")
                st.markdown("**Fallback: Original Prop Firm Dashboard**")
                display_prop_firm_dashboard()
            except:
                pass
    else:
        st.error("Prop firm modules not available")
        st.info("Please ensure prop_firm_dashboard.py and prop_firm_manager.py are properly installed.")

elif page == "Settings":
    st.header("Settings")
    
    st.subheader("Current Configuration")
    
    config_data = {
        "Database Path": Config.get_absolute_db_path(),
        "Initial Capital": f"${Config.INITIAL_CAPITAL:.2f}",
        "Default Risk %": f"{Config.DEFAULT_RISK_PERCENT}%",
        "Max Open Trades": Config.MAX_OPEN_TRADES,
        "Log Level": Config.LOG_LEVEL,
        "Log File": Config.LOG_FILE
    }
    
    for key, value in config_data.items():
        st.text(f"{key}: {value}")
    
    st.subheader("Database Management")
    
    if st.button("Backup Database"):
        try:
            import shutil
            backup_path = f"{Config.get_absolute_db_path()}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(Config.get_absolute_db_path(), backup_path)
            st.success(f"Database backed up to: {backup_path}")
        except Exception as e:
            st.error(f"Backup failed: {e}")
    
    st.warning("⚠️ Database operations are permanent. Always backup before making changes.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("Crypto Paper Trading Dashboard v2.0 - Enhanced with proper risk management and error handling.")
