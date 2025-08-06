#!/usr/bin/env python3
"""Find where the 23 trades are stored"""

import sqlite3
import os
import glob

def check_all_databases():
    """Check all database files for trades tables"""
    
    # Find all .db files
    db_files = glob.glob('**/*.db', recursive=True)
    
    for db_file in db_files:
        print(f"\n{'='*60}")
        print(f"Checking: {db_file}")
        print('='*60)
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]
            
            if tables:
                print(f"Tables: {tables}")
                
                # Check each table for trade-like content
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Look for tables with trade-like columns
                    if any(col in columns for col in ['symbol', 'side', 'entry', 'position_size', 'profit_loss']):
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"\n  {table}: {count} records")
                        print(f"  Columns: {columns}")
                        
                        if count > 0:
                            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                            records = cursor.fetchall()
                            for i, record in enumerate(records):
                                print(f"    Record {i+1}: {record[:6]}...")  # Show first 6 fields
            
            conn.close()
            
        except Exception as e:
            print(f"Error: {e}")

# Also check if there are any Python files that reference a different database
print("\n" + "="*60)
print("Checking Python files for database references:")
print("="*60)

import re

for py_file in glob.glob('**/*.py', recursive=True):
    if 'venv' in py_file or '__pycache__' in py_file:
        continue
    
    try:
        with open(py_file, 'r') as f:
            content = f.read()
            
        # Look for database file references
        db_refs = re.findall(r'["\']([^"\']+\.db)["\']', content)
        if db_refs and py_file not in ['check_databases.py', 'find_trades_table.py']:
            print(f"\n{py_file}:")
            for ref in set(db_refs):
                print(f"  - {ref}")
    except:
        pass

check_all_databases()