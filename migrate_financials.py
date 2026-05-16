import sqlite3

conn = sqlite3.connect("stock.db")
cursor = conn.cursor()

# Ajouter la colonne (ignore l'erreur si elle existe déjà)
try:
    cursor.execute("ALTER TABLE utilisateurs ADD COLUMN can_view_financials BOOLEAN DEFAULT 0")
    print("✅ Colonne 'can_view_financials' ajoutée.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ La colonne existe déjà.")
    else:
        raise e

# Donner la permission à l'admin
cursor.execute("UPDATE utilisateurs SET can_view_financials = 1 WHERE role = 'admin'")
conn.commit()
conn.close()
print("✅ Permission accordée à l'admin.")