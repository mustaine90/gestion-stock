import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import Database
from auth import AuthManager, hash_password
from models import GestionStock
from datetime import datetime

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion de Stock - Magasinier")
        self.geometry("900x600")
        self.db = Database()
        self.auth = AuthManager(self.db)
        self.gestion = GestionStock(self.db, self.auth)
        self.current_frame = None
        self.show_login()

    def show_login(self):
        self.clear_frame()
        self.current_frame = LoginFrame(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_main_menu(self):
        self.clear_frame()
        role = self.auth.current_user['role']
        if role == 'admin':
            self.current_frame = AdminFrame(self)
        elif role == 'magasinier':
            self.current_frame = MagasinierFrame(self)
        else:
            self.current_frame = TechnicienFrame(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

class LoginFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        ttk.Label(self, text="Connexion", font=('Arial', 18)).pack(pady=20)
        ttk.Label(self, text="Login:").pack()
        self.login_entry = ttk.Entry(self)
        self.login_entry.pack(pady=5)
        ttk.Label(self, text="Mot de passe:").pack()
        self.pwd_entry = ttk.Entry(self, show="*")
        self.pwd_entry.pack(pady=5)
        ttk.Button(self, text="Se connecter", command=self.do_login).pack(pady=10)
        self.login_entry.bind('<Return>', lambda e: self.do_login())
        self.pwd_entry.bind('<Return>', lambda e: self.do_login())

    def do_login(self):
        login = self.login_entry.get()
        pwd = self.pwd_entry.get()
        user = self.master.auth.login(login, pwd)
        if user:
            self.master.show_main_menu()
        else:
            messagebox.showerror("Erreur", "Identifiants incorrects")

class AdminFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text=f"Admin - {self.master.auth.current_user['prenom']} {self.master.auth.current_user['nom']}", font=('Arial', 14)).pack(pady=10)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Gérer les articles", command=self.gerer_articles).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(btn_frame, text="Entrées de stock", command=self.entree_stock).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(btn_frame, text="Sorties de stock", command=self.sortie_stock).grid(row=1, column=0, padx=10, pady=5)
        ttk.Button(btn_frame, text="Historique des mouvements", command=self.historique).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(btn_frame, text="Rapport stock actuel", command=self.rapport_stock).grid(row=2, column=0, padx=10, pady=5)
        ttk.Button(btn_frame, text="Gérer les utilisateurs", command=self.gerer_utilisateurs).grid(row=2, column=1, padx=10, pady=5)
        ttk.Button(self, text="Déconnexion", command=self.logout).pack(pady=10)

    def gerer_articles(self):
        ArticleManagementWindow(self.master)

    def entree_stock(self):
        MouvementWindow(self.master, type_mvt='entree')

    def sortie_stock(self):
        MouvementWindow(self.master, type_mvt='sortie')

    def historique(self):
        HistoriqueWindow(self.master)

    def rapport_stock(self):
        RapportStockWindow(self.master)

    def gerer_utilisateurs(self):
        UserManagementWindow(self.master)

    def logout(self):
        self.master.auth.logout()
        self.master.show_login()

class MagasinierFrame(AdminFrame):
    # Mêmes fonctionnalités que l'admin sauf gestion utilisateurs
    def create_widgets(self):
        ttk.Label(self, text=f"Magasinier - {self.master.auth.current_user['prenom']} {self.master.auth.current_user['nom']}", font=('Arial', 14)).pack(pady=10)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Gérer les articles", command=self.gerer_articles).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(btn_frame, text="Entrées de stock", command=self.entree_stock).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(btn_frame, text="Sorties de stock", command=self.sortie_stock).grid(row=1, column=0, padx=10, pady=5)
        ttk.Button(btn_frame, text="Historique des mouvements", command=self.historique).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(btn_frame, text="Rapport stock actuel", command=self.rapport_stock).grid(row=2, column=0, padx=10, pady=5)
        ttk.Button(self, text="Déconnexion", command=self.logout).pack(pady=10)

class TechnicienFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        ttk.Label(self, text=f"Technicien - {self.master.auth.current_user['prenom']} {self.master.auth.current_user['nom']}", font=('Arial', 14)).pack(pady=10)
        ttk.Button(self, text="Consulter le stock", command=self.consulter_stock).pack(pady=5)
        ttk.Button(self, text="Demander une sortie (consommation)", command=self.demander_sortie).pack(pady=5)
        ttk.Button(self, text="Mon historique", command=self.mon_historique).pack(pady=5)
        ttk.Button(self, text="Déconnexion", command=self.logout).pack(pady=20)

    def consulter_stock(self):
        RapportStockWindow(self.master, readonly=True)

    def demander_sortie(self):
        MouvementWindow(self.master, type_mvt='sortie_technicien', technicien_id=self.master.auth.current_user['id'])

    def mon_historique(self):
        HistoriqueWindow(self.master, technicien_id=self.master.auth.current_user['id'])

    def logout(self):
        self.master.auth.logout()
        self.master.show_login()

# ---------- Fenêtres secondaires ----------
class ArticleManagementWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Gestion des articles")
        self.geometry("700x400")
        self.tree = ttk.Treeview(self, columns=('ID', 'Référence', 'Désignation', 'Stock', 'Prix HT', 'Seuil'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Référence', text='Référence')
        self.tree.heading('Désignation', text='Désignation')
        self.tree.heading('Stock', text='Stock')
        self.tree.heading('Prix HT', text='Prix HT')
        self.tree.heading('Seuil', text='Seuil alerte')
        self.tree.column('ID', width=50)
        self.tree.pack(fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Ajouter", command=self.ajouter_article).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Modifier", command=self.modifier_article).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Rafraîchir", command=self.load_data).pack(side=tk.LEFT, padx=5)
        self.load_data()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        articles = self.master.gestion.get_articles()
        for art in articles:
            self.tree.insert('', tk.END, values=(art['id'], art['reference'], art['designation'], art['quantite_stock'], art['prix_unitaire_ht'], art['seuil_alerte']))

    def ajouter_article(self):
        dialog = ArticleDialog(self)
        self.wait_window(dialog)
        self.load_data()

    def modifier_article(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un article")
            return
        item = self.tree.item(selected[0])
        article_id = item['values'][0]
        dialog = ArticleDialog(self, article_id)
        self.wait_window(dialog)
        self.load_data()

class ArticleDialog(tk.Toplevel):
    def __init__(self, parent, article_id=None):
        super().__init__(parent)
        self.parent = parent
        self.article_id = article_id
        self.title("Modifier article" if article_id else "Nouvel article")
        self.geometry("300x250")
        ttk.Label(self, text="Référence:").pack(pady=5)
        self.ref_entry = ttk.Entry(self)
        self.ref_entry.pack()
        ttk.Label(self, text="Désignation:").pack(pady=5)
        self.des_entry = ttk.Entry(self)
        self.des_entry.pack()
        ttk.Label(self, text="Prix unitaire HT:").pack(pady=5)
        self.prix_entry = ttk.Entry(self)
        self.prix_entry.pack()
        ttk.Label(self, text="Quantité initiale:").pack(pady=5)
        self.qte_entry = ttk.Entry(self)
        self.qte_entry.pack()
        ttk.Label(self, text="Seuil d'alerte:").pack(pady=5)
        self.seuil_entry = ttk.Entry(self)
        self.seuil_entry.pack()
        if article_id:
            art = self.parent.master.gestion.get_article(article_id)
            self.ref_entry.insert(0, art['reference'])
            self.ref_entry.config(state='readonly')
            self.des_entry.insert(0, art['designation'])
            self.prix_entry.insert(0, str(art['prix_unitaire_ht']))
            self.qte_entry.insert(0, str(art['quantite_stock']))
            self.qte_entry.config(state='readonly')
            self.seuil_entry.insert(0, str(art['seuil_alerte']))
        ttk.Button(self, text="Enregistrer", command=self.save).pack(pady=20)

    def save(self):
        try:
            ref = self.ref_entry.get()
            des = self.des_entry.get()
            prix = float(self.prix_entry.get())
            seuil = int(self.seuil_entry.get())
            if not self.article_id:
                qte = int(self.qte_entry.get())
                self.parent.master.gestion.ajouter_article(ref, des, prix, qte, seuil)
            else:
                self.parent.master.gestion.modifier_article(self.article_id, des, prix, seuil)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

class MouvementWindow(tk.Toplevel):
    def __init__(self, master, type_mvt, technicien_id=None):
        super().__init__(master)
        self.master = master
        self.type_mvt = type_mvt
        self.technicien_id = technicien_id
        self.title("Entrée de stock" if type_mvt == 'entree' else "Sortie de stock")
        self.geometry("400x300")
        ttk.Label(self, text="Article:").pack(pady=5)
        self.article_combo = ttk.Combobox(self, state='readonly')
        self.article_combo.pack()
        articles = master.gestion.get_articles()
        self.articles_dict = {f"{a['reference']} - {a['designation']} (stock: {a['quantite_stock']})": a['id'] for a in articles}
        self.article_combo['values'] = list(self.articles_dict.keys())
        if type_mvt == 'entree':
            ttk.Label(self, text="Type d'entrée:").pack(pady=5)
            self.type_combo = ttk.Combobox(self, values=['entree_achat', 'entree_retour'], state='readonly')
            self.type_combo.pack()
        else:
            if technicien_id is None:
                ttk.Label(self, text="Technicien:").pack(pady=5)
                self.tech_combo = ttk.Combobox(self, state='readonly')
                techs = master.gestion.get_techniciens()
                self.tech_dict = {f"{t['nom']} {t['prenom']}": t['id'] for t in techs}
                self.tech_combo['values'] = list(self.tech_dict.keys())
                self.tech_combo.pack()
                ttk.Label(self, text="Type de sortie:").pack(pady=5)
                self.type_combo = ttk.Combobox(self, values=['sortie_affectation', 'sortie_consommation'], state='readonly')
                self.type_combo.pack()
            else:
                # Technicien qui demande sa propre consommation
                self.type_mvt_interne = 'sortie_consommation'
        ttk.Label(self, text="Quantité:").pack(pady=5)
        self.qte_entry = ttk.Entry(self)
        self.qte_entry.pack()
        ttk.Label(self, text="Commentaire:").pack(pady=5)
        self.comment_entry = ttk.Entry(self)
        self.comment_entry.pack()
        ttk.Button(self, text="Valider", command=self.valider).pack(pady=20)

    def valider(self):
        try:
            article_id = self.articles_dict[self.article_combo.get()]
            quantite = int(self.qte_entry.get())
            commentaire = self.comment_entry.get()
            if self.type_mvt == 'entree':
                type_op = self.type_combo.get()
                self.master.gestion.entree_stock(article_id, quantite, type_op, commentaire)
            else:
                if self.technicien_id is not None:
                    tech_id = self.technicien_id
                    type_op = 'sortie_consommation'
                else:
                    tech_id = self.tech_dict[self.tech_combo.get()]
                    type_op = self.type_combo.get()
                self.master.gestion.sortie_stock(article_id, tech_id, quantite, type_op, commentaire)
            messagebox.showinfo("Succès", "Mouvement enregistré")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

class HistoriqueWindow(tk.Toplevel):
    def __init__(self, master, technicien_id=None):
        super().__init__(master)
        self.master = master
        self.title("Historique des mouvements")
        self.geometry("900x400")
        columns = ('Date', 'Article', 'Type', 'Quantité', 'Utilisateur', 'Technicien', 'Commentaire')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.pack(fill=tk.BOTH, expand=True)
        # Charger les données
        if technicien_id:
            mouvs = master.db.fetchall("""
                SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite, u.nom as user_nom, '' as tech_nom, m.commentaire
                FROM mouvements m
                JOIN articles a ON m.article_id = a.id
                JOIN utilisateurs u ON m.utilisateur_id = u.id
                WHERE m.technicien_id = ?
                ORDER BY m.date_mouvement DESC
            """, (technicien_id,))
        else:
            mouvs = master.db.fetchall("""
                SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite, u.nom as user_nom, t.nom as tech_nom, m.commentaire
                FROM mouvements m
                JOIN articles a ON m.article_id = a.id
                JOIN utilisateurs u ON m.utilisateur_id = u.id
                LEFT JOIN utilisateurs t ON m.technicien_id = t.id
                ORDER BY m.date_mouvement DESC
            """)
        for m in mouvs:
            self.tree.insert('', tk.END, values=(m['date_mouvement'], m['designation'], m['type_mouvement'], m['quantite'], m['user_nom'], m['tech_nom'] or '', m['commentaire']))

class RapportStockWindow(tk.Toplevel):
    def __init__(self, master, readonly=False):
        super().__init__(master)
        self.master = master
        self.title("État du stock")
        self.geometry("800x400")
        self.tree = ttk.Treeview(self, columns=('Référence', 'Désignation', 'Stock', 'Prix HT', 'Valeur totale'), show='headings')
        self.tree.heading('Référence', text='Référence')
        self.tree.heading('Désignation', text='Désignation')
        self.tree.heading('Stock', text='Stock')
        self.tree.heading('Prix HT', text='Prix unitaire HT')
        self.tree.heading('Valeur totale', text='Valeur totale HT')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.load_data()
        total = self.master.gestion.get_valeur_stock()
        ttk.Label(self, text=f"Valeur totale du stock: {total:.2f} €").pack(pady=10)

    def load_data(self):
        articles = self.master.gestion.get_articles()
        for art in articles:
            valeur = art['quantite_stock'] * art['prix_unitaire_ht']
            self.tree.insert('', tk.END, values=(art['reference'], art['designation'], art['quantite_stock'], f"{art['prix_unitaire_ht']:.2f}", f"{valeur:.2f}"))

class UserManagementWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Gestion des utilisateurs")
        self.geometry("600x400")
        self.tree = ttk.Treeview(self, columns=('ID', 'Nom', 'Prénom', 'Login', 'Rôle', 'Actif'), show='headings')
        for col in ('ID', 'Nom', 'Prénom', 'Login', 'Rôle', 'Actif'):
            self.tree.heading(col, text=col)
        self.tree.column('ID', width=40)
        self.tree.pack(fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Ajouter", command=self.ajouter_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Modifier", command=self.modifier_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Rafraîchir", command=self.load_data).pack(side=tk.LEFT, padx=5)
        self.load_data()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        users = self.master.db.fetchall("SELECT id, nom, prenom, login, role, actif FROM utilisateurs")
        for u in users:
            self.tree.insert('', tk.END, values=(u['id'], u['nom'], u['prenom'], u['login'], u['role'], 'Oui' if u['actif'] else 'Non'))

    def ajouter_user(self):
        dialog = UserDialog(self)
        self.wait_window(dialog)
        self.load_data()

    def modifier_user(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un utilisateur")
            return
        item = self.tree.item(selected[0])
        user_id = item['values'][0]
        dialog = UserDialog(self, user_id)
        self.wait_window(dialog)
        self.load_data()

class UserDialog(tk.Toplevel):
    def __init__(self, parent, user_id=None):
        super().__init__(parent)
        self.parent = parent
        self.user_id = user_id
        self.title("Modifier utilisateur" if user_id else "Nouvel utilisateur")
        self.geometry("300x300")
        ttk.Label(self, text="Nom:").pack(pady=5)
        self.nom_entry = ttk.Entry(self)
        self.nom_entry.pack()
        ttk.Label(self, text="Prénom:").pack(pady=5)
        self.prenom_entry = ttk.Entry(self)
        self.prenom_entry.pack()
        ttk.Label(self, text="Login:").pack(pady=5)
        self.login_entry = ttk.Entry(self)
        self.login_entry.pack()
        ttk.Label(self, text="Mot de passe:").pack(pady=5)
        self.pwd_entry = ttk.Entry(self, show="*")
        self.pwd_entry.pack()
        ttk.Label(self, text="Rôle:").pack(pady=5)
        self.role_combo = ttk.Combobox(self, values=['admin', 'magasinier', 'technicien'], state='readonly')
        self.role_combo.pack()
        self.actif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Actif", variable=self.actif_var).pack(pady=5)
        if user_id:
            user = self.parent.master.db.fetchone("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
            self.nom_entry.insert(0, user['nom'])
            self.prenom_entry.insert(0, user['prenom'])
            self.login_entry.insert(0, user['login'])
            self.login_entry.config(state='readonly')
            self.role_combo.set(user['role'])
            self.actif_var.set(bool(user['actif']))
        ttk.Button(self, text="Enregistrer", command=self.save).pack(pady=20)

    def save(self):
        try:
            nom = self.nom_entry.get()
            prenom = self.prenom_entry.get()
            login = self.login_entry.get()
            pwd = self.pwd_entry.get()
            role = self.role_combo.get()
            actif = 1 if self.actif_var.get() else 0
            if not self.user_id:
                if not pwd:
                    messagebox.showerror("Erreur", "Mot de passe requis")
                    return
                hashed = hash_password(pwd)
                self.parent.master.db.execute(
                    "INSERT INTO utilisateurs (nom, prenom, login, mot_de_passe, role, actif) VALUES (?,?,?,?,?,?)",
                    (nom, prenom, login, hashed, role, actif)
                )
            else:
                if pwd:
                    hashed = hash_password(pwd)
                    self.parent.master.db.execute(
                        "UPDATE utilisateurs SET nom=?, prenom=?, mot_de_passe=?, role=?, actif=? WHERE id=?",
                        (nom, prenom, hashed, role, actif, self.user_id)
                    )
                else:
                    self.parent.master.db.execute(
                        "UPDATE utilisateurs SET nom=?, prenom=?, role=?, actif=? WHERE id=?",
                        (nom, prenom, role, actif, self.user_id)
                    )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))