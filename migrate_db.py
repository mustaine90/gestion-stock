import sqlite3

conn = sqlite3.connect('stock.db')
cursor = conn.cursor()

# Vérifier si la colonne prix_unitaire existe déjà
cursor.execute("PRAGMA table_info(articles)")
columns = [col[1] for col in cursor.fetchall()]

if 'prix_unitaire_ht' in columns and 'prix_unitaire' not in columns:
    print("Migration : renommage de prix_unitaire_ht en prix_unitaire...")
    cursor.execute("ALTER TABLE articles RENAME COLUMN prix_unitaire_ht TO prix_unitaire")
    conn.commit()
    print("Migration terminée.")
else:
    print("Aucune migration nécessaire.")

conn.close()