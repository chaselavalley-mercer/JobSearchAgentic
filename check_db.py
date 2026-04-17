import sqlite3, os

path = ".users/chase_lavalley/jobs.db"
if os.path.exists(path):
    con = sqlite3.connect(path)
    tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("DB exists. Tables:", tables)
    for (table,) in tables:
        cols = con.execute(f"PRAGMA table_info({table})").fetchall()
        print(f"\n  {table} columns:")
        for col in cols:
            print(f"    {col[1]} ({col[2]})")
    con.close()
else:
    print("DB does not exist yet")