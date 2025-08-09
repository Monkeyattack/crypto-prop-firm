"""
Check database schema
"""

import sqlite3

print("Checking trade_log.db schema...")

try:
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(signal_log)")
    columns = cursor.fetchall()
    
    print("\nSignal_log table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Show sample data
    cursor.execute("SELECT * FROM signal_log LIMIT 3")
    rows = cursor.fetchall()
    
    print(f"\nSample data ({len(rows)} rows):")
    if rows:
        for i, row in enumerate(rows):
            print(f"  Row {i+1}: {row}")
    else:
        print("  No data found")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
