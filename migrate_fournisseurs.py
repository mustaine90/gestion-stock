import sqlite3

conn = sqlite3.connect('stock.db')
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        ice TEXT,
        telephone TEXT,
        email TEXT,
        site_web TEXT
    )
""")
conn.commit()
conn.close()
print("✅ Table fournisseurs créée.")