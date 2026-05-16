import sqlite3

DB_PATH = "stock.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ajouter la colonne ticket
    try:
        cursor.execute("ALTER TABLE mouvements ADD COLUMN ticket TEXT")
        print("✅ Colonne 'ticket' ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ Colonne 'ticket' existe déjà.")
        else:
            raise e
    
    # Ajouter la colonne lot
    try:
        cursor.execute("ALTER TABLE mouvements ADD COLUMN lot TEXT")
        print("✅ Colonne 'lot' ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ Colonne 'lot' existe déjà.")
        else:
            raise e
    
    conn.commit()
    conn.close()
    print("🎉 Migration terminée.")

if __name__ == "__main__":
    migrate()