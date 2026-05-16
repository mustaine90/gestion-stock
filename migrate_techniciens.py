import sqlite3

DB_PATH = "stock.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS techniciens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        code TEXT UNIQUE,
        actif BOOLEAN DEFAULT 1
    )
""")
conn.commit()
conn.close()
print("Table techniciens créée.")