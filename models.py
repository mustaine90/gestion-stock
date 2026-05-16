class GestionStock:
    def __init__(self, db, auth):
        self.db = db
        self.auth = auth

    # ---------- Articles ----------
    def get_articles(self):
        return self.db.fetchall("""
            SELECT id, reference, designation, quantite_stock, prix_unitaire_ht,
                   seuil_alerte, photo, bon_commande, fournisseur, lot, unite
            FROM articles ORDER BY designation
        """)

    def get_article(self, article_id):
        return self.db.fetchone("SELECT * FROM articles WHERE id = ?", (article_id,))

    def ajouter_article(self, reference, designation, fournisseur=None, unite='unité', photo=None):
        if not self.auth.has_permission('gerer_articles'):
            raise PermissionError("Permission refusée")
        return self.db.execute(
            "INSERT INTO articles (reference, designation, fournisseur, unite, photo) VALUES (?,?,?,?,?)",
            (reference, designation, fournisseur, unite, photo)
        )

    def modifier_article(self, article_id, designation=None, prix=None, seuil=None):
        if not self.auth.has_permission('gerer_articles'):
            raise PermissionError("Permission refusée")
        updates = []
        params = []
        if designation is not None:
            updates.append("designation = ?")
            params.append(designation)
        if prix is not None:
            updates.append("prix_unitaire_ht = ?")
            params.append(prix)
        if seuil is not None:
            updates.append("seuil_alerte = ?")
            params.append(seuil)
        if updates:
            params.append(article_id)
            self.db.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ?", tuple(params))

    def supprimer_article(self, article_id):
        if not self.auth.has_permission('gerer_articles'):
            raise PermissionError("Permission refusée")
        mouvements = self.db.fetchone("SELECT COUNT(*) as count FROM mouvements WHERE article_id = ?", (article_id,))
        if mouvements and mouvements['count'] > 0:
            raise ValueError("Impossible de supprimer un article ayant des mouvements.")
        self.db.execute("DELETE FROM articles WHERE id = ?", (article_id,))

    # ---------- Mouvements ----------
    def entree_stock(self, article_id, quantite, type_entree, commentaire="",
                     prix_unitaire=None, bon_commande=None, lot=None, technicien_id=None):
        if not self.auth.has_permission('gerer_entrees'):
            raise PermissionError("Permission refusée")
        user_id = self.auth.current_user['id']
        self.db.execute(
            """INSERT INTO mouvements (article_id, utilisateur_id, technicien_id, type_mouvement, quantite,
               commentaire, prix_unitaire, bon_commande, lot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (article_id, user_id, technicien_id, type_entree, quantite, commentaire,
             prix_unitaire, bon_commande, lot)
        )
        self.db.execute("UPDATE articles SET quantite_stock = quantite_stock + ? WHERE id = ?",
                        (quantite, article_id))
        if prix_unitaire is not None:
            self.db.execute("UPDATE articles SET prix_unitaire_ht = ? WHERE id = ?",
                            (prix_unitaire, article_id))

    def sortie_stock(self, article_id, technicien_id, quantite, type_sortie,
                     commentaire="", ticket="", lot="", bon_commande=None):
        if type_sortie == 'sortie_affectation':
            if not self.auth.has_permission('valider_sorties'):
                raise PermissionError("Seul un magasinier ou admin peut affecter du matériel")
        elif type_sortie == 'sortie_consommation':
            if self.auth.current_user['role'] == 'technicien' and self.auth.current_user['id'] != technicien_id:
                raise PermissionError("Vous ne pouvez consommer que votre propre matériel")

        article = self.get_article(article_id)
        if article['quantite_stock'] < quantite:
            raise ValueError("Stock insuffisant")

        user_id = self.auth.current_user['id']
        self.db.execute(
            """INSERT INTO mouvements (article_id, utilisateur_id, technicien_id, type_mouvement,
               quantite, commentaire, ticket, lot, bon_commande)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (article_id, user_id, technicien_id, type_sortie, quantite, commentaire, ticket, lot, bon_commande)
        )
        self.db.execute("UPDATE articles SET quantite_stock = quantite_stock - ? WHERE id = ?",
                        (quantite, article_id))

    def get_mouvements_article(self, article_id):
        return self.db.fetchall(
            """SELECT m.*, u.nom as utilisateur_nom, tec.nom as technicien_nom 
               FROM mouvements m
               JOIN utilisateurs u ON m.utilisateur_id = u.id
               LEFT JOIN techniciens tec ON m.technicien_id = tec.id
               WHERE m.article_id = ? ORDER BY m.date_mouvement DESC""",
            (article_id,)
        )

    # ---------- Techniciens ----------
    def get_techniciens(self):
        return self.db.fetchall("SELECT id, nom, prenom, code FROM techniciens WHERE actif = 1 ORDER BY nom")

    def ajouter_technicien(self, nom, prenom, code=None):
        self.db.execute(
            "INSERT INTO techniciens (nom, prenom, code) VALUES (?,?,?)",
            (nom, prenom, code)
        )

    def supprimer_technicien(self, technicien_id):
        self.db.execute("DELETE FROM techniciens WHERE id = ?", (technicien_id,))

    # ---------- Fournisseurs ----------
    def get_fournisseurs(self):
        return self.db.fetchall("SELECT id, nom, ice, telephone, email, site_web FROM fournisseurs ORDER BY nom")

    def get_fournisseur(self, fournisseur_id):
        return self.db.fetchone("SELECT * FROM fournisseurs WHERE id = ?", (fournisseur_id,))

    def ajouter_fournisseur(self, nom, ice=None, telephone=None, email=None, site_web=None):
        self.db.execute(
            "INSERT INTO fournisseurs (nom, ice, telephone, email, site_web) VALUES (?,?,?,?,?)",
            (nom, ice, telephone, email, site_web)
        )
    def ajouter_fournisseur_si_inexistant(self, nom):
        """Crée le fournisseur s'il n'existe pas déjà, puis retourne son nom."""
        if not nom:
            return None
        exist = self.db.fetchone("SELECT id FROM fournisseurs WHERE nom = ?", (nom,))
        if not exist:
            self.db.execute("INSERT INTO fournisseurs (nom) VALUES (?)", (nom,))
        return nom
    
    def modifier_fournisseur(self, fournisseur_id, nom=None, ice=None, telephone=None, email=None, site_web=None):
        fields = []
        params = []
        if nom is not None:
            fields.append("nom = ?")
            params.append(nom)
        if ice is not None:
            fields.append("ice = ?")
            params.append(ice)
        if telephone is not None:
            fields.append("telephone = ?")
            params.append(telephone)
        if email is not None:
            fields.append("email = ?")
            params.append(email)
        if site_web is not None:
            fields.append("site_web = ?")
            params.append(site_web)
        if fields:
            params.append(fournisseur_id)
            self.db.execute(f"UPDATE fournisseurs SET {', '.join(fields)} WHERE id = ?", tuple(params))

    def supprimer_fournisseur(self, fournisseur_id):
        self.db.execute("DELETE FROM fournisseurs WHERE id = ?", (fournisseur_id,))

    # ---------- Valeur du stock ----------
    def get_valeur_stock(self):
        result = self.db.fetchone("SELECT SUM(quantite_stock * prix_unitaire_ht) as total FROM articles")
        return result['total'] if result['total'] else 0.0
    