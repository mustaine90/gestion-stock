import hashlib
import os
from datetime import datetime

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + key.hex()

def verify_password(password: str, hashed: str) -> bool:
    salt_hex, key_hex = hashed.split(':')
    salt = bytes.fromhex(salt_hex)
    key = bytes.fromhex(key_hex)
    new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return new_key == key

class AuthManager:
    def __init__(self, db):
        self.db = db
        self.current_user = None

    def login(self, login: str, password: str):
        user = self.db.fetchone(
            "SELECT * FROM utilisateurs WHERE login = ? AND actif = 1",
            (login,)
        )
        if user and verify_password(password, user['mot_de_passe']):
            self.current_user = dict(user)
            self._log_action(user['id'], "CONNEXION", f"Login réussi depuis {self._get_client_ip()}")
            return self.current_user
        return None

    def logout(self):
        if self.current_user:
            self._log_action(self.current_user['id'], "DECONNEXION", "Déconnexion")
        self.current_user = None

    def _log_action(self, user_id, action, details=""):
        ip = self._get_client_ip()
        self.db.execute(
            "INSERT INTO logs (utilisateur_id, action, details, ip_address) VALUES (?,?,?,?)",
            (user_id, action, details, ip)
        )

    def _get_client_ip(self):
        try:
            from flask import request
            return request.remote_addr
        except:
            return "127.0.0.1"

    def has_permission(self, permission: str) -> bool:
        user = self.current_user
        if not user:
            return False

        # Convertir en dict si c'est un sqlite3.Row (au cas où)
        if isinstance(user, dict):
            user_dict = user
        else:
            user_dict = dict(user)

        # Récupération sécurisée des champs
        role = user_dict.get('role', '')
        can_manage_users = user_dict.get('can_manage_users', 0)

        # Super admin (toutes les permissions)
        if role == 'admin' and can_manage_users == 1:
            return True

        # Permissions granulaires
        perm_map = {
            'gerer_utilisateurs': 'can_manage_users',
            'gerer_articles': 'can_manage_articles',
            'gerer_entrees': 'can_manage_stock_entries',
            'valider_sorties': 'can_validate_exits',
            'generer_rapports': 'can_view_reports',
            'voir_historique': 'can_view_history',
            'voir_finances': 'can_view_financials'
        }

        col = perm_map.get(permission)
        if col:
            # Si la colonne existe et vaut 1, on autorise
            if user_dict.get(col, 0) == 1:
                return True
            # Pour "voir_finances", on ne l'accorde que si la colonne est 1
            if permission == 'voir_finances':
                return False

        # Fallback sur les rôles (quand les colonnes de permissions ne sont pas définies ou à 0)
        if role == 'admin':
            return True
        elif role == 'magasinier':
            return permission in [
                'gerer_articles', 'gerer_entrees', 'valider_sorties',
                'generer_rapports', 'voir_historique'
            ]
        elif role == 'technicien':
            return permission in ['demander_sortie', 'voir_mon_historique']

        return False