import sqlite3

DB_PATH = "stock.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ajouter des colonnes de permissions à la table utilisateurs
    permissions_cols = [
        ("can_manage_users", "BOOLEAN DEFAULT 0"),
        ("can_manage_articles", "BOOLEAN DEFAULT 0"),
        ("can_manage_stock_entries", "BOOLEAN DEFAULT 0"),
        ("can_validate_exits", "BOOLEAN DEFAULT 0"),
        ("can_view_reports", "BOOLEAN DEFAULT 0"),
        ("can_view_history", "BOOLEAN DEFAULT 0"),
    ]
    for col, col_type in permissions_cols:
        try:
            cursor.execute(f"ALTER TABLE utilisateurs ADD COLUMN {col} {col_type}")
            print(f"✅ Colonne {col} ajoutée.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ Colonne {col} existe déjà.")
            else:
                raise e

    # Créer la table des logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            date_log TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        )
    """)
    print("✅ Table logs créée.")

    # Mettre à jour l'admin existant pour lui donner toutes les permissions
    cursor.execute("""
        UPDATE utilisateurs SET
            can_manage_users = 1,
            can_manage_articles = 1,
            can_manage_stock_entries = 1,
            can_validate_exits = 1,
            can_view_reports = 1,
            can_view_history = 1
        WHERE role = 'admin'
    """)
    print("✅ Permissions de l'admin mises à jour.")

    conn.commit()
    conn.close()
    print("🎉 Migration terminée.")

if __name__ == "__main__":
    migrate()