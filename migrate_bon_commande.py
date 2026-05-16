import sqlite3

conn = sqlite3.connect('stock.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE mouvements ADD COLUMN bon_commande TEXT")
    print("✅ Colonne bon_commande ajoutée.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ La colonne bon_commande existe déjà.")
    else:
        raise e

conn.commit()
conn.close()