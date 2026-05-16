import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.text import Text
from rich.layout import Layout
from rich import box
from database import Database
from auth import AuthManager, hash_password
from models import GestionStock

console = Console()

class CLIApp:
    def __init__(self):
        self.db = Database()
        self.auth = AuthManager(self.db)
        self.gestion = GestionStock(self.db, self.auth)

    def run(self):
        self.login()
        while True:
            if not self.auth.current_user:
                self.login()
                continue
            role = self.auth.current_user['role']
            if role == 'admin':
                self.menu_admin()
            elif role == 'magasinier':
                self.menu_magasinier()
            elif role == 'technicien':
                self.menu_technicien()
            else:
                console.print("[red]Rôle inconnu[/]")
                break

    def login(self):
        console.clear()
        console.print(Panel.fit("[bold cyan]SYSTÈME DE GESTION DE STOCK[/]", border_style="blue"))
        while True:
            console.print("\n[bold]Connexion[/]")
            login = Prompt.ask("Login")
            pwd = Prompt.ask("Mot de passe", password=True)
            user = self.auth.login(login, pwd)
            if user:
                console.print(f"\n[green]Bienvenue {user['prenom']} {user['nom']} ({user['role']})[/]")
                console.input("\nAppuyez sur Entrée pour continuer...")
                console.clear()
                break
            else:
                console.print("[red]Identifiants incorrects. Réessayez.[/]")

    def menu_admin(self):
        while True:
            console.print(Panel(f"[bold]Menu Administrateur - {self.auth.current_user['prenom']} {self.auth.current_user['nom']}[/]", style="blue"))
            console.print("1. [cyan]Gérer les articles[/]")
            console.print("2. [cyan]Entrées de stock[/]")
            console.print("3. [cyan]Sorties de stock[/]")
            console.print("4. [cyan]Historique des mouvements[/]")
            console.print("5. [cyan]Rapport stock actuel[/]")
            console.print("6. [cyan]Gérer les utilisateurs[/]")
            console.print("7. [yellow]Déconnexion[/]")
            console.print("0. [red]Quitter[/]")
            choix = Prompt.ask("Votre choix", choices=["1","2","3","4","5","6","7","0"])
            if choix == "1":
                self.gerer_articles()
            elif choix == "2":
                self.entree_stock()
            elif choix == "3":
                self.sortie_stock()
            elif choix == "4":
                self.historique()
            elif choix == "5":
                self.rapport_stock()
            elif choix == "6":
                self.gerer_utilisateurs()
            elif choix == "7":
                self.auth.logout()
                self.login()
                return
            elif choix == "0":
                sys.exit(0)

    def menu_magasinier(self):
        while True:
            console.print(Panel(f"[bold]Menu Magasinier - {self.auth.current_user['prenom']} {self.auth.current_user['nom']}[/]", style="green"))
            console.print("1. [cyan]Gérer les articles[/]")
            console.print("2. [cyan]Entrées de stock[/]")
            console.print("3. [cyan]Sorties de stock[/]")
            console.print("4. [cyan]Historique des mouvements[/]")
            console.print("5. [cyan]Rapport stock actuel[/]")
            console.print("6. [yellow]Déconnexion[/]")
            console.print("0. [red]Quitter[/]")
            choix = Prompt.ask("Votre choix", choices=["1","2","3","4","5","6","0"])
            if choix == "1":
                self.gerer_articles()
            elif choix == "2":
                self.entree_stock()
            elif choix == "3":
                self.sortie_stock()
            elif choix == "4":
                self.historique()
            elif choix == "5":
                self.rapport_stock()
            elif choix == "6":
                self.auth.logout()
                self.login()
                return
            elif choix == "0":
                sys.exit(0)

    def menu_technicien(self):
        while True:
            console.print(Panel(f"[bold]Menu Technicien - {self.auth.current_user['prenom']} {self.auth.current_user['nom']}[/]", style="magenta"))
            console.print("1. [cyan]Consulter le stock[/]")
            console.print("2. [cyan]Demander une sortie (consommation)[/]")
            console.print("3. [cyan]Mon historique[/]")
            console.print("4. [yellow]Déconnexion[/]")
            console.print("0. [red]Quitter[/]")
            choix = Prompt.ask("Votre choix", choices=["1","2","3","4","0"])
            if choix == "1":
                self.rapport_stock(readonly=True)
            elif choix == "2":
                self.demander_sortie_technicien()
            elif choix == "3":
                self.historique(technicien_id=self.auth.current_user['id'])
            elif choix == "4":
                self.auth.logout()
                self.login()
                return
            elif choix == "0":
                sys.exit(0)

    # Méthodes communes
    def gerer_articles(self):
        while True:
            console.clear()
            console.print("[bold underline]Gestion des articles[/]\n")
            table = Table(title="Liste des articles", box=box.SIMPLE_HEAVY)
            table.add_column("ID", style="dim")
            table.add_column("Référence")
            table.add_column("Désignation")
            table.add_column("Stock", justify="right")
            table.add_column("Prix HT", justify="right")
            table.add_column("Seuil", justify="right")
            articles = self.gestion.get_articles()
            for art in articles:
                table.add_row(str(art['id']), art['reference'], art['designation'], str(art['quantite_stock']), f"{art['prix_unitaire_ht']:.2f}", str(art['seuil_alerte']))
            console.print(table)
            console.print("\n[A]jouter  [M]odifier  [R]etour")
            action = Prompt.ask("Action", choices=["A","M","R"]).upper()
            if action == "A":
                self.ajouter_article()
            elif action == "M":
                self.modifier_article()
            elif action == "R":
                break

    def ajouter_article(self):
        console.print("\n[bold]Ajout d'un nouvel article[/]")
        ref = Prompt.ask("Référence")
        des = Prompt.ask("Désignation")
        prix = FloatPrompt.ask("Prix unitaire HT")
        qte = IntPrompt.ask("Quantité initiale", default=0)
        seuil = IntPrompt.ask("Seuil d'alerte", default=0)
        try:
            self.gestion.ajouter_article(ref, des, prix, qte, seuil)
            console.print("[green]Article ajouté avec succès ![/]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/]")
        console.input("Appuyez sur Entrée pour continuer...")

    def modifier_article(self):
        articles = self.gestion.get_articles()
        if not articles:
            console.print("[yellow]Aucun article à modifier[/]")
            console.input("Appuyez sur Entrée...")
            return
        ids = [str(a['id']) for a in articles]
        id_art = IntPrompt.ask("ID de l'article à modifier", choices=ids)
        art = self.gestion.get_article(id_art)
        console.print(f"Modification de : {art['reference']} - {art['designation']}")
        des = Prompt.ask("Nouvelle désignation (laisser vide pour ne pas changer)", default="")
        prix_str = Prompt.ask("Nouveau prix HT (laisser vide pour ne pas changer)", default="")
        seuil_str = Prompt.ask("Nouveau seuil (laisser vide pour ne pas changer)", default="")
        kwargs = {}
        if des:
            kwargs['designation'] = des
        if prix_str:
            kwargs['prix'] = float(prix_str)
        if seuil_str:
            kwargs['seuil'] = int(seuil_str)
        if kwargs:
            try:
                self.gestion.modifier_article(id_art, **kwargs)
                console.print("[green]Article modifié ![/]")
            except Exception as e:
                console.print(f"[red]Erreur : {e}[/]")
        else:
            console.print("[yellow]Aucune modification[/]")
        console.input("Appuyez sur Entrée...")

    def entree_stock(self):
        console.print("\n[bold]Entrée de stock[/]")
        articles = self.gestion.get_articles()
        if not articles:
            console.print("[yellow]Aucun article disponible[/]")
            return
        # Afficher liste simplifiée
        for art in articles:
            console.print(f"{art['id']}: {art['reference']} - {art['designation']} (stock: {art['quantite_stock']})")
        id_art = IntPrompt.ask("ID de l'article")
        qte = IntPrompt.ask("Quantité")
        type_entree = Prompt.ask("Type", choices=["entree_achat", "entree_retour"])
        commentaire = Prompt.ask("Commentaire (optionnel)", default="")
        try:
            self.gestion.entree_stock(id_art, qte, type_entree, commentaire)
            console.print("[green]Entrée enregistrée ![/]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/]")
        console.input("Appuyez sur Entrée...")

    def sortie_stock(self):
        console.print("\n[bold]Sortie de stock[/]")
        articles = self.gestion.get_articles()
        if not articles:
            console.print("[yellow]Aucun article[/]")
            return
        for art in articles:
            console.print(f"{art['id']}: {art['reference']} - {art['designation']} (stock: {art['quantite_stock']})")
        id_art = IntPrompt.ask("ID de l'article")
        techniciens = self.gestion.get_techniciens()
        if not techniciens:
            console.print("[yellow]Aucun technicien enregistré[/]")
            return
        console.print("Techniciens disponibles :")
        for t in techniciens:
            console.print(f"{t['id']}: {t['nom']} {t['prenom']}")
        tech_id = IntPrompt.ask("ID du technicien")
        qte = IntPrompt.ask("Quantité")
        type_sortie = Prompt.ask("Type", choices=["sortie_affectation", "sortie_consommation"])
        commentaire = Prompt.ask("Commentaire", default="")
        try:
            self.gestion.sortie_stock(id_art, tech_id, qte, type_sortie, commentaire)
            console.print("[green]Sortie enregistrée ![/]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/]")
        console.input("Appuyez sur Entrée...")

    def demander_sortie_technicien(self):
        console.print("\n[bold]Demande de sortie (consommation)[/]")
        articles = self.gestion.get_articles()
        for art in articles:
            console.print(f"{art['id']}: {art['reference']} - {art['designation']} (stock: {art['quantite_stock']})")
        id_art = IntPrompt.ask("ID de l'article")
        qte = IntPrompt.ask("Quantité")
        commentaire = Prompt.ask("Commentaire", default="")
        try:
            self.gestion.sortie_stock(id_art, self.auth.current_user['id'], qte, 'sortie_consommation', commentaire)
            console.print("[green]Sortie enregistrée ![/]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/]")
        console.input("Appuyez sur Entrée...")

    def historique(self, technicien_id=None):
        console.print("\n[bold]Historique des mouvements[/]")
        if technicien_id:
            mouvs = self.db.fetchall("""
                SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite, u.nom as user_nom, m.commentaire
                FROM mouvements m
                JOIN articles a ON m.article_id = a.id
                JOIN utilisateurs u ON m.utilisateur_id = u.id
                WHERE m.technicien_id = ?
                ORDER BY m.date_mouvement DESC
            """, (technicien_id,))
        else:
            mouvs = self.db.fetchall("""
                SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite, u.nom as user_nom, t.nom as tech_nom, m.commentaire
                FROM mouvements m
                JOIN articles a ON m.article_id = a.id
                JOIN utilisateurs u ON m.utilisateur_id = u.id
                LEFT JOIN utilisateurs t ON m.technicien_id = t.id
                ORDER BY m.date_mouvement DESC
            """)
        table = Table(title="Mouvements", box=box.SIMPLE)
        table.add_column("Date")
        table.add_column("Article")
        table.add_column("Type")
        table.add_column("Qté", justify="right")
        table.add_column("Utilisateur")
        table.add_column("Technicien")
        table.add_column("Commentaire")
        for m in mouvs:
            table.add_row(
                m['date_mouvement'], m['designation'], m['type_mouvement'], str(m['quantite']),
                m['user_nom'], m['tech_nom'] or "", m['commentaire'] or ""
            )
        console.print(table)
        console.input("Appuyez sur Entrée...")

    def rapport_stock(self, readonly=False):
        console.print("\n[bold underline]État du stock[/]")
        articles = self.gestion.get_articles()
        table = Table(title="Stock actuel", box=box.SIMPLE_HEAVY)
        table.add_column("Référence")
        table.add_column("Désignation")
        table.add_column("Stock", justify="right")
        table.add_column("Prix HT", justify="right")
        table.add_column("Valeur totale", justify="right")
        total = 0
        for art in articles:
            valeur = art['quantite_stock'] * art['prix_unitaire_ht']
            total += valeur
            table.add_row(art['reference'], art['designation'], str(art['quantite_stock']), f"{art['prix_unitaire_ht']:.2f}", f"{valeur:.2f}")
        table.add_row("", "", "", "[bold]TOTAL[/]", f"[bold]{total:.2f}[/]", style="bold")
        console.print(table)
        console.input("Appuyez sur Entrée...")

    def gerer_utilisateurs(self):
        while True:
            console.clear()
            console.print("[bold]Gestion des utilisateurs[/]\n")
            users = self.db.fetchall("SELECT id, nom, prenom, login, role, actif FROM utilisateurs")
            table = Table(title="Utilisateurs", box=box.SIMPLE)
            table.add_column("ID")
            table.add_column("Nom")
            table.add_column("Prénom")
            table.add_column("Login")
            table.add_column("Rôle")
            table.add_column("Actif")
            for u in users:
                table.add_row(str(u['id']), u['nom'], u['prenom'], u['login'], u['role'], "Oui" if u['actif'] else "Non")
            console.print(table)
            console.print("\n[A]jouter  [M]odifier  [R]etour")
            action = Prompt.ask("Action", choices=["A","M","R"]).upper()
            if action == "A":
                self.ajouter_utilisateur()
            elif action == "M":
                self.modifier_utilisateur()
            else:
                break

    def ajouter_utilisateur(self):
        console.print("\n[bold]Nouvel utilisateur[/]")
        nom = Prompt.ask("Nom")
        prenom = Prompt.ask("Prénom")
        login = Prompt.ask("Login")
        pwd = Prompt.ask("Mot de passe", password=True)
        role = Prompt.ask("Rôle", choices=["admin","magasinier","technicien"])
        actif = Confirm.ask("Actif ?", default=True)
        try:
            hashed = hash_password(pwd)
            self.db.execute(
                "INSERT INTO utilisateurs (nom, prenom, login, mot_de_passe, role, actif) VALUES (?,?,?,?,?,?)",
                (nom, prenom, login, hashed, role, 1 if actif else 0)
            )
            console.print("[green]Utilisateur créé[/]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/]")
        console.input("Appuyez sur Entrée...")

    def modifier_utilisateur(self):
        users = self.db.fetchall("SELECT id FROM utilisateurs")
        ids = [str(u['id']) for u in users]
        user_id = IntPrompt.ask("ID de l'utilisateur à modifier", choices=ids)
        user = self.db.fetchone("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        console.print(f"Modification de {user['prenom']} {user['nom']}")
        nom = Prompt.ask("Nom", default=user['nom'])
        prenom = Prompt.ask("Prénom", default=user['prenom'])
        pwd = Prompt.ask("Nouveau mot de passe (laisser vide pour ne pas changer)", password=True, default="")
        role = Prompt.ask("Rôle", choices=["admin","magasinier","technicien"], default=user['role'])
        actif = Confirm.ask("Actif ?", default=bool(user['actif']))
        if pwd:
            hashed = hash_password(pwd)
            self.db.execute(
                "UPDATE utilisateurs SET nom=?, prenom=?, mot_de_passe=?, role=?, actif=? WHERE id=?",
                (nom, prenom, hashed, role, 1 if actif else 0, user_id)
            )
        else:
            self.db.execute(
                "UPDATE utilisateurs SET nom=?, prenom=?, role=?, actif=? WHERE id=?",
                (nom, prenom, role, 1 if actif else 0, user_id)
            )
        console.print("[green]Utilisateur modifié[/]")
        console.input("Appuyez sur Entrée...")