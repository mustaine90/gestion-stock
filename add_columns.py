import sqlite3

conn = sqlite3.connect('stock.db')
cursor = conn.cursor()

# Liste des colonnes à ajouter avec leur type et valeur par défaut
new_columns = [
    ("photo", "TEXT"),
    ("deleted", "BOOLEAN DEFAULT 0"),
    ("deleted_by", "INTEGER"),
    ("deleted_at", "TIMESTAMP")
]

for col_name, col_type in new_columns:
    try:
        cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
        print(f"Colonne '{col_name}' ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Colonne '{col_name}' existe déjà.")
        else:
            raise e

conn.commit()
conn.close()
print("Mise à jour de la base terminée.")