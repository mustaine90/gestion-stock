import sqlite3
conn = sqlite3.connect('stock.db')
conn.execute("UPDATE articles SET prix_unitaire_ht = 0 WHERE prix_unitaire_ht IS NULL")
conn.commit()
conn.close()
print("✅ Les prix manquants ont été mis à 0.")