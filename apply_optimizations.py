#!/usr/bin/env python3
"""
Apply Optimizations - Update trading system with optimized parameters
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizationApplier:
    def __init__(self):
        self.db_path = 'trading.db'
        self.config_file = 'optimized_strategy_config.json'
        
    def load_optimized_config(self) -> Dict[str, Any]:
        """Load optimized strategy configuration"""
        try:
            # First try from file
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            
            # Fallback to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT optimized_config FROM optimized_strategy_config 
                WHERE active = 1 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            
            logger.error("No optimized configuration found")
            return {}
            
        except Exception as e:
            logger.error(f"Error loading optimized config: {e}")
            return {}
    
    def update_signal_processor(self, config: Dict[str, Any]) -> bool:
        """Update signal_processor.py with optimized parameters"""
        try:
            # Read current signal processor
            with open('signal_processor.py', 'r') as f:
                content = f.read()
            
            # Extract optimization parameters
            risk_mgmt = config.get('risk_management', {})
            entry_criteria = config.get('entry_criteria', {})
            symbol_selection = config.get('symbol_selection', {})
            
            # Create new configuration section
            new_config_section = f'''
# OPTIMIZED TRADING PARAMETERS - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
OPTIMIZED_CONFIG = {{
    'stop_loss_pct': {risk_mgmt.get('stop_loss_pct', 5.0)},
    'take_profit_pct': {risk_mgmt.get('take_profit_pct', 10.0)},
    'risk_reward_ratio': {risk_mgmt.get('risk_reward_ratio', 2.0)},
    'max_position_size': {risk_mgmt.get('max_position_size', 100)},
    'max_daily_trades': {risk_mgmt.get('max_daily_trades', 10)},
    'preferred_symbols': {symbol_selection.get('top_symbols', [])},
    'min_win_rate_threshold': {symbol_selection.get('min_win_rate', 40)},
    'preferred_entry_hours': {entry_criteria.get('preferred_entry_hours', [])},
    'avoid_entry_hours': {entry_criteria.get('avoid_entry_hours', [])}
}}
'''
            
            # Find where to insert the configuration
            if 'OPTIMIZED_CONFIG' in content:
                # Replace existing configuration
                start_marker = '# OPTIMIZED TRADING PARAMETERS'
                end_marker = '}'
                
                start_idx = content.find(start_marker)
                if start_idx != -1:
                    # Find the end of the config block
                    brace_count = 0
                    end_idx = start_idx
                    in_config = False
                    
                    for i, char in enumerate(content[start_idx:], start_idx):
                        if char == '{':
                            in_config = True
                            brace_count += 1
                        elif char == '}' and in_config:
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    # Replace the configuration
                    content = content[:start_idx] + new_config_section + content[end_idx:]
                else:
                    # Add at the beginning of the file
                    content = new_config_section + '\n' + content
            else:
                # Add at the beginning of the file
                content = new_config_section + '\n' + content
            
            # Backup original file
            backup_filename = f'signal_processor_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
            with open(backup_filename, 'w') as f:
                with open('signal_processor.py', 'r') as original:
                    f.write(original.read())
            
            # Write updated file
            with open('signal_processor.py', 'w') as f:
                f.write(content)
            
            logger.info(f"Updated signal_processor.py with optimized parameters")
            logger.info(f"Backup saved as: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating signal processor: {e}")
            return False
    
    def update_trading_engine(self, config: Dict[str, Any]) -> bool:
        """Update trading_engine.py with optimized parameters"""
        try:
            # Read current trading engine
            with open('trading_engine.py', 'r') as f:
                content = f.read()
            
            risk_mgmt = config.get('risk_management', {})
            
            # Update risk management parameters
            updates = [
                (r'self\.default_stop_loss_pct = [\d.]+', f'self.default_stop_loss_pct = {risk_mgmt.get("stop_loss_pct", 5.0) / 100}'),
                (r'self\.default_take_profit_pct = [\d.]+', f'self.default_take_profit_pct = {risk_mgmt.get("take_profit_pct", 10.0) / 100}'),
                (r'self\.max_position_size = [\d.]+', f'self.max_position_size = {risk_mgmt.get("max_position_size", 100)}'),
                (r'self\.max_daily_trades = [\d]+', f'self.max_daily_trades = {risk_mgmt.get("max_daily_trades", 10)}')
            ]
            
            import re
            for pattern, replacement in updates:
                content = re.sub(pattern, replacement, content)
            
            # Backup and save
            backup_filename = f'trading_engine_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
            with open(backup_filename, 'w') as f:
                with open('trading_engine.py', 'r') as original:
                    f.write(original.read())
            
            with open('trading_engine.py', 'w') as f:
                f.write(content)
            
            logger.info(f"Updated trading_engine.py with optimized parameters")
            logger.info(f"Backup saved as: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trading engine: {e}")
            return False
    
    def create_symbol_filter(self, config: Dict[str, Any]) -> bool:
        """Create a symbol filter based on optimization results"""
        try:
            symbol_selection = config.get('symbol_selection', {})
            top_symbols = symbol_selection.get('top_symbols', [])
            
            filter_content = f'''#!/usr/bin/env python3
"""
Optimized Symbol Filter - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

class OptimizedSymbolFilter:
    def __init__(self):
        self.approved_symbols = {top_symbols}
        self.min_win_rate = {symbol_selection.get('min_win_rate', 40)}
    
    def is_symbol_approved(self, symbol: str) -> bool:
        """Check if symbol is approved for trading"""
        return symbol.upper() in [s.upper() for s in self.approved_symbols]
    
    def get_approved_symbols(self) -> list:
        """Get list of approved symbols"""
        return self.approved_symbols
    
    def filter_signals(self, signals: list) -> list:
        """Filter signals to only include approved symbols"""
        return [
            signal for signal in signals 
            if self.is_symbol_approved(signal.get('symbol', ''))
        ]

# Create global instance
symbol_filter = OptimizedSymbolFilter()
'''
            
            with open('optimized_symbol_filter.py', 'w') as f:
                f.write(filter_content)
            
            logger.info("Created optimized symbol filter")
            return True
            
        except Exception as e:
            logger.error(f"Error creating symbol filter: {e}")
            return False
    
    def update_dashboard_config(self, config: Dict[str, Any]) -> bool:
        """Update dashboard with optimization results"""
        try:
            dashboard_config = {
                'optimization_applied': True,
                'optimization_date': datetime.now().isoformat(),
                'optimized_parameters': config,
                'performance_targets': config.get('performance_targets', {}),
                'risk_management': config.get('risk_management', {}),
                'display_optimizations': True
            }
            
            with open('dashboard_optimization_config.json', 'w') as f:
                json.dump(dashboard_config, f, indent=2)
            
            logger.info("Updated dashboard configuration")
            return True
            
        except Exception as e:
            logger.error(f"Error updating dashboard config: {e}")
            return False
    
    def create_monitoring_script(self, config: Dict[str, Any]) -> bool:
        """Create performance monitoring script"""
        try:
            monitoring_content = f'''#!/usr/bin/env python3
"""
Performance Monitoring - Track optimization effectiveness
Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json

class PerformanceMonitor:
    def __init__(self):
        self.db_path = 'trading.db'
        self.optimization_config = {json.dumps(config, indent=8)}
    
    def check_performance_vs_targets(self):
        """Check current performance against optimization targets"""
        targets = self.optimization_config.get('performance_targets', {{}})
        
        # Get recent trades (last 30 days)
        conn = sqlite3.connect(self.db_path)
        recent_trades = pd.read_sql_query('''
            SELECT * FROM trades 
            WHERE created_at >= datetime('now', '-30 days')
        ''', conn)
        conn.close()
        
        if recent_trades.empty:
            return "No recent trades to analyze"
        
        # Calculate current metrics
        win_rate = (recent_trades['profit_loss'] > 0).mean() * 100
        total_pnl = recent_trades['profit_loss'].sum()
        
        # Compare to targets
        target_win_rate = targets.get('expected_win_rate', 50)
        
        report = []
        report.append(f"Performance vs Targets (Last 30 days):")
        report.append(f"Current Win Rate: {{win_rate:.1f}}% (Target: {{target_win_rate:.1f}}%)")
        report.append(f"Total P&L: {{total_pnl:.2f}}%")
        
        if win_rate >= target_win_rate:
            report.append("✅ Win rate target achieved")
        else:
            report.append("❌ Win rate below target")
        
        return "\\n".join(report)
    
    def suggest_reoptimization(self):
        """Check if reoptimization is needed"""
        # Simple logic: reoptimize if performance has degraded significantly
        current_performance = self.check_performance_vs_targets()
        
        # You could add more sophisticated logic here
        return "Consider reoptimization if performance consistently below targets for 2+ weeks"

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    print(monitor.check_performance_vs_targets())
    print()
    print(monitor.suggest_reoptimization())
'''
            
            with open('performance_monitor.py', 'w') as f:
                f.write(monitoring_content)
            
            logger.info("Created performance monitoring script")
            return True
            
        except Exception as e:
            logger.error(f"Error creating monitoring script: {e}")
            return False
    
    def apply_all_optimizations(self) -> bool:
        """Apply all optimizations to the trading system"""
        logger.info("Applying optimizations to trading system...")
        
        # Load configuration
        config = self.load_optimized_config()
        if not config:
            logger.error("No optimization configuration found")
            return False
        
        success_count = 0
        total_updates = 5
        
        # Apply updates
        if self.update_signal_processor(config):
            success_count += 1
        
        if self.update_trading_engine(config):
            success_count += 1
        
        if self.create_symbol_filter(config):
            success_count += 1
        
        if self.update_dashboard_config(config):
            success_count += 1
        
        if self.create_monitoring_script(config):
            success_count += 1
        
        success_rate = (success_count / total_updates) * 100
        
        logger.info(f"Applied {success_count}/{total_updates} optimizations ({success_rate:.0f}% success)")
        
        return success_count == total_updates

def main():
    """Main function to apply optimizations"""
    applier = OptimizationApplier()
    
    print("=== Applying Strategy Optimizations ===")
    print("This will update your trading system with optimized parameters")
    
    # Load and display configuration
    config = applier.load_optimized_config()
    
    if not config:
        print("❌ No optimization configuration found")
        print("Please run strategy_optimizer.py first")
        return
    
    print(f"✅ Found optimization configuration from {config.get('generated_at', 'unknown')}")
    
    # Display key parameters
    risk_mgmt = config.get('risk_management', {})
    print(f"\\nKey Optimized Parameters:")
    print(f"  Stop Loss: {risk_mgmt.get('stop_loss_pct', 'N/A')}%")
    print(f"  Take Profit: {risk_mgmt.get('take_profit_pct', 'N/A')}%")
    print(f"  Risk/Reward: {risk_mgmt.get('risk_reward_ratio', 'N/A')}")
    
    # Confirm application
    confirm = input("\\nApply these optimizations? (y/N): ").strip().lower()
    
    if confirm == 'y':
        success = applier.apply_all_optimizations()
        
        if success:
            print("\\n✅ All optimizations applied successfully!")
            print("\\nNext steps:")
            print("1. Review updated files for accuracy")
            print("2. Restart trading services")
            print("3. Monitor performance with performance_monitor.py")
            print("4. Consider reoptimization in 2-4 weeks")
        else:
            print("\\n⚠️  Some optimizations failed - check logs")
    else:
        print("Optimization application cancelled")

if __name__ == "__main__":
    main()