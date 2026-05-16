import sqlite3
conn = sqlite3.connect('stock.db')
try:
    conn.execute("ALTER TABLE mouvements ADD COLUMN prix_unitaire REAL")
    conn.commit()
    print("✅ Colonne prix_unitaire ajoutée.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ Colonne déjà existante.")
    else:
        raise e
conn.close()