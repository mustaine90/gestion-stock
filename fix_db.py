import sqlite3

conn = sqlite3.connect('stock.db')
cursor = conn.cursor()

# Ajouter la colonne si elle n'existe pas
try:
    cursor.execute("ALTER TABLE articles ADD COLUMN prix_unitaire_ht REAL")
    print("Colonne prix_unitaire_ht ajoutée.")
except sqlite3.OperationalError:
    print("La colonne prix_unitaire_ht existe déjà.")

# Copier les valeurs depuis prix_unitaire si elles sont NULL
cursor.execute("UPDATE articles SET prix_unitaire_ht = prix_unitaire WHERE prix_unitaire_ht IS NULL")
conn.commit()
conn.close()
print("Mise à jour terminée.")