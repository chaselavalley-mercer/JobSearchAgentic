import sqlite3

conn = sqlite3.connect('.tmp/chase_lavalley/scraped_jobs.db')

print("=== TABLES ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(" ", t[0])

print("\n=== COLUMNS PER TABLE ===")
for t in tables:
    table_name = t[0]
    print(f"\n  [{table_name}]")
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    for col in cols:
        print(f"    {col[1]} ({col[2]})")

print("\n=== SAMPLE ROW (first table) ===")
if tables:
    first = tables[0][0]
    rows = conn.execute(f"SELECT * FROM {first} LIMIT 1").fetchall()
    if rows:
        for val in rows[0]:
            preview = str(val)[:80] + "..." if len(str(val)) > 80 else str(val)
            print(f"  {preview}")
    else:
        print("  (no rows)")

conn.close()