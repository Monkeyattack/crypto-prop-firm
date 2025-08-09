"""
Dashboard integration patch for adding prop firm components to existing dashboard
"""

import streamlit as st
import sys
from pathlib import Path

# Add the prop firm integration
parent_dir = Path(__file__).parent
sys.path.append(str(parent_dir))

from prop_firm_integration import PropFirmIntegration, render_prop_firm_status_banner, render_recent_prop_decisions, render_account_comparison

def add_prop_firm_tab():
    """Add prop firm tab to existing dashboard"""
    
    # This would be inserted into the main tab structure
    st.header("💼 Prop Firm Evaluation Dashboard")
    
    # Status overview
    st.subheader("📊 Account Status")
    render_prop_firm_status_banner()
    
    st.divider()
    
    # Recent decisions
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_recent_prop_decisions()
    
    with col2:
        st.subheader("⚡ Quick Stats")
        integration = PropFirmIntegration()
        daily_stats = integration.get_daily_stats()
        
        st.metric("Signals Processed Today", daily_stats['total_signals'])
        st.metric("Acceptance Rate", f"{daily_stats['acceptance_rate']:.1f}%")
        st.metric("Alerts Sent", daily_stats['alerts_sent'])
        
        # Risk gauge
        status = integration.get_prop_firm_status()
        daily_risk_pct = (status['daily_loss'] / 500) * 100
        
        st.subheader("🎯 Risk Management")
        st.progress(min(daily_risk_pct / 100, 1.0))
        st.caption(f"Daily Loss: ${status['daily_loss']:.0f} / $500 ({daily_risk_pct:.1f}%)")
    
    st.divider()
    
    # Account comparison
    render_account_comparison()

def add_prop_firm_banner_to_main():
    """Add prop firm status banner to main dashboard page"""
    
    # This would be inserted after the main title
    st.subheader("💼 Breakout Prop Firm Status")
    render_prop_firm_status_banner()
    
    # Add recent decisions section
    with st.expander("🤖 Recent Prop Firm Decisions", expanded=False):
        render_recent_prop_decisions()

# Test function to populate sample data
def initialize_sample_data():
    """Initialize sample data for testing"""
    try:
        from prop_firm_integration import populate_sample_decisions
        populate_sample_decisions()
        st.success("✅ Sample prop firm data initialized!")
    except Exception as e:
        st.error(f"❌ Error initializing sample data: {e}")

# Instructions for integration
INTEGRATION_INSTRUCTIONS = """
## Integration Instructions

To integrate prop firm components into your existing dashboard:

### 1. Add Import to app.py:
```python
# Add this import at the top of dashboard/app.py
sys.path.append('/root/crypto-paper-trading')
from prop_firm_integration import render_prop_firm_status_banner, render_recent_prop_decisions
```

### 2. Add Prop Firm Tab:
```python
# In the tab creation section, add:
tab1, tab2, tab3, tab_prop = st.tabs(["📈 Dashboard", "📊 Analysis", "⚙️ Settings", "💼 Prop Firm"])

with tab_prop:
    from dashboard_integration import add_prop_firm_tab
    add_prop_firm_tab()
```

### 3. Add Status Banner to Main Dashboard:
```python
# After the main title in the Dashboard tab:
with tab1:  # Dashboard tab
    st.title("Crypto Trading Dashboard")
    
    # Add prop firm banner
    from dashboard_integration import add_prop_firm_banner_to_main
    add_prop_firm_banner_to_main()
    
    # Continue with existing dashboard content...
```

### 4. Initialize Database:
Run once to set up prop firm tables:
```python
from prop_firm_integration import PropFirmIntegration
integration = PropFirmIntegration()
```
"""

if __name__ == "__main__":
    st.set_page_config(page_title="Prop Firm Integration Test", layout="wide")
    
    st.title("🧪 Prop Firm Dashboard Integration Test")
    
    # Test controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔧 Initialize Sample Data"):
            initialize_sample_data()
    
    with col2:
        if st.button("🧹 Clear All Data"):
            try:
                integration = PropFirmIntegration()
                with integration.db_path as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM prop_firm_decisions")
                    cursor.execute("DELETE FROM prop_firm_stats")
                    cursor.execute("UPDATE prop_firm_status SET daily_loss = 0, max_drawdown = 0, profit_made = 0")
                    conn.commit()
                st.success("✅ All prop firm data cleared!")
            except Exception as e:
                st.error(f"❌ Error clearing data: {e}")
    
    st.divider()
    
    # Test the prop firm tab
    add_prop_firm_tab()
    
    st.divider()
    
    # Integration instructions
    with st.expander("📋 Integration Instructions", expanded=False):
        st.markdown(INTEGRATION_INSTRUCTIONS)