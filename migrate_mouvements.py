import sqlite3

DB_PATH = "stock.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for col, col_type in [("prix_unitaire", "REAL"), ("bon_commande", "TEXT")]:
    try:
        cursor.execute(f"ALTER TABLE mouvements ADD COLUMN {col} {col_type}")
        print(f"✅ Colonne {col} ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"ℹ️ Colonne {col} existe déjà.")
        else:
            raise e

conn.commit()
conn.close()
print("🎉 Migration mouvements terminée.")