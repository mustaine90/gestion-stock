import sqlite3

DB_PATH = "stock.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # --- Table articles ---
    cols_articles = [
        ("photo", "TEXT"),
        ("bon_commande", "TEXT"),
        ("fournisseur", "TEXT"),
        ("lot", "TEXT"),
        ("unite", "TEXT DEFAULT 'unité'")
    ]
    for col_name, col_type in cols_articles:
        try:
            cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
            print(f"✅ Colonne 'articles.{col_name}' ajoutée.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ Colonne 'articles.{col_name}' existe déjà.")
            else:
                raise e

    # --- Table mouvements ---
    cols_mouvements = [
        ("ticket", "TEXT"),
        ("lot", "TEXT")
    ]
    for col_name, col_type in cols_mouvements:
        try:
            cursor.execute(f"ALTER TABLE mouvements ADD COLUMN {col_name} {col_type}")
            print(f"✅ Colonne 'mouvements.{col_name}' ajoutée.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ Colonne 'mouvements.{col_name}' existe déjà.")
            else:
                raise e

    conn.commit()
    conn.close()
    print("\n🎉 Migration terminée ! Toutes les colonnes sont prêtes.")

if __name__ == "__main__":
    migrate()