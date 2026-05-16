import sqlite3
import os

DB_PATH = "stock.db"

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._create_tables()
        self._create_default_admin()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                login TEXT UNIQUE NOT NULL,
                mot_de_passe TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'magasinier', 'technicien')) NOT NULL,
                actif BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                designation TEXT NOT NULL,
                quantite_stock INTEGER DEFAULT 0,
                prix_unitaire REAL,
                seuil_alerte INTEGER DEFAULT 0,
                photo TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_by INTEGER,
                deleted_at TIMESTAMP,
                FOREIGN KEY (deleted_by) REFERENCES utilisateurs(id)
            );

            CREATE TABLE IF NOT EXISTS mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                utilisateur_id INTEGER NOT NULL,
                technicien_id INTEGER,
                type_mouvement TEXT CHECK(type_mouvement IN ('entree_achat', 'entree_retour', 'sortie_affectation', 'sortie_consommation')) NOT NULL,
                quantite INTEGER NOT NULL,
                date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                commentaire TEXT,
                valide BOOLEAN DEFAULT 1,
                FOREIGN KEY (article_id) REFERENCES articles(id),
                FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                FOREIGN KEY (technicien_id) REFERENCES utilisateurs(id)
            );
        """)
        conn.commit()
        conn.close()

    def _create_default_admin(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM utilisateurs")
        if cursor.fetchone()[0] == 0:
            from auth import hash_password
            cursor.execute(
                "INSERT INTO utilisateurs (nom, prenom, login, mot_de_passe, role) VALUES (?,?,?,?,?)",
                ("Admin", "Super", "admin", hash_password("admin123"), "admin")
            )
            conn.commit()
        conn.close()

    def execute(self, query, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def fetchall(self, query, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def fetchone(self, query, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return row