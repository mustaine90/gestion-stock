import sqlite3

DB_PATH = "stock.db"

def fix_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Ajouter la colonne prix_unitaire_ht si elle n'existe pas
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN prix_unitaire_ht REAL")
        print("✅ Colonne 'prix_unitaire_ht' ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ La colonne 'prix_unitaire_ht' existe déjà.")
        else:
            raise e
    
    # 2. Vérifier si l'ancienne colonne 'prix_unitaire' existe et copier les valeurs
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'prix_unitaire' in columns:
        cursor.execute("UPDATE articles SET prix_unitaire_ht = prix_unitaire WHERE prix_unitaire_ht IS NULL")
        print("✅ Données copiées depuis 'prix_unitaire' vers 'prix_unitaire_ht'.")
    else:
        # Si aucune colonne prix n'existe, on initialise à 0 pour éviter les NULL
        cursor.execute("UPDATE articles SET prix_unitaire_ht = 0 WHERE prix_unitaire_ht IS NULL")
        print("⚠️ Aucune colonne 'prix_unitaire' trouvée, 'prix_unitaire_ht' initialisé à 0.")
    
    conn.commit()
    conn.close()
    print("🎉 Base de données corrigée avec succès !")

if __name__ == "__main__":
    fix_database()