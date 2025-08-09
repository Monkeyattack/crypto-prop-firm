"""Check signal_log table structure and data"""

import sqlite3

conn = sqlite3.connect('trade_log.db')
cursor = conn.cursor()

# Get table info
cursor.execute("PRAGMA table_info(signal_log)")
columns = cursor.fetchall()
print("signal_log columns:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# Get a sample signal
cursor.execute("SELECT * FROM signal_log WHERE processed = 0 LIMIT 1")
row = cursor.fetchone()
if row:
    print("\nSample signal:")
    for i, col in enumerate(columns):
        print(f"  {col[1]}: {row[i]} (type: {type(row[i]).__name__})")
else:
    print("\nNo unprocessed signals found")

conn.close()