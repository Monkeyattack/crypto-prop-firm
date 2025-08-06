#!/usr/bin/env python3
"""
Fix all dashboard files to use trade_log.db instead of trading.db
"""

import os
import re

def fix_db_paths():
    """Fix database paths in all dashboard files"""
    dashboard_dir = 'dashboard'
    files_fixed = []
    
    for filename in os.listdir(dashboard_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(dashboard_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace various database references
            original_content = content
            
            # Fix trading.db references
            content = content.replace("'trading.db'", "'trade_log.db'")
            content = content.replace('"trading.db"', '"trade_log.db"')
            content = content.replace("'/root/crypto-paper-trading/trading.db'", "'trade_log.db'")
            content = content.replace('"/root/crypto-paper-trading/trading.db"', '"trade_log.db"')
            
            # Fix relative path references
            content = content.replace("'../trade_log.db'", "'trade_log.db'")
            content = content.replace('"../trade_log.db"', '"trade_log.db"')
            
            # Fix default parameter values in constructors
            content = re.sub(r'db_path\s*=\s*["\']trading\.db["\']', "db_path='trade_log.db'", content)
            content = re.sub(r'self\.db_path\s*=\s*["\']trading\.db["\']', "self.db_path = 'trade_log.db'", content)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_fixed.append(filename)
                print(f"[FIXED] {filename}")
            else:
                print(f"  No changes needed in {filename}")
    
    print(f"\n[DONE] Fixed {len(files_fixed)} files:")
    for file in files_fixed:
        print(f"   - {file}")
    
    # Also check main directory
    print("\nChecking main directory files...")
    main_files = ['app.py', 'trading_engine.py', 'signal_processor.py', 'position_monitor.py']
    
    for filename in main_files:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            content = content.replace("'trading.db'", "'trade_log.db'")
            content = content.replace('"trading.db"', '"trade_log.db"')
            
            if content != original_content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[FIXED] {filename}")
                files_fixed.append(filename)

if __name__ == "__main__":
    fix_db_paths()