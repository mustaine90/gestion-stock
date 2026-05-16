from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from database import Database
from auth import AuthManager, hash_password
from models import GestionStock
from functools import wraps
import os
from werkzeug.utils import secure_filename
import io
import csv
from datetime import datetime, timedelta
import webbrowser
import threading
import time
import tempfile
import openpyxl

# --- Configuration de Tesseract OCR ---
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\a.moustaine\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Définir le dossier tessdata pour la langue française
os.environ['TESSDATA_PREFIX'] = r'C:\Users\a.moustaine\AppData\Local\Programs\Tesseract-OCR\tessdata'

# Forcer un dossier temporaire accessible en écriture (corrige l'erreur "Accès refusé")
os.environ['TEMP'] = tempfile.gettempdir()
os.environ['TMP'] = tempfile.gettempdir()

# ---------- Configuration ----------
app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_a_changer_en_production'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

TAUX_EUR_MAD = 10.9
CAPACITE_MAX_STOCK = 10000

def parse_bon_text(text):
    result = {'designation': '', 'quantite': ''}
    lines = text.splitlines()
    for line in lines:
        # Désignation / Description
        if not result['designation']:
            m = re.search(r'(?:désignation|designation|description|article)[.:]\s*(.*)', line, re.IGNORECASE)
            if m:
                result['designation'] = m.group(1).strip()
        # Quantité (peut être notée "Qté", "Quantité", "Qte", "QTY", etc.)
        if not result['quantite']:
            m = re.search(r'(?:qté|quantité|quantite|qte|qty)\s*[.:]\s*(\d+)', line, re.IGNORECASE)
            if m:
                result['quantite'] = int(m.group(1))
    return result

# ---------- Initialisation ----------
db = Database()
auth = AuthManager(db)
gestion = GestionStock(db, auth)

# ---------- Décorateurs ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        auth.current_user = db.fetchone("SELECT * FROM utilisateurs WHERE id = ?", (session['user_id'],))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not auth.has_permission(action):
                return "Accès interdit", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ---------- Routes générales ----------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = auth.login(login, password)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = f"{user['prenom']} {user['nom']}"
            session['user_role'] = user['role']
            session['can_view_financials'] = user.get('can_view_financials', 0)
            flash('Connexion réussie', 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Identifiants incorrects")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    auth.logout()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_articles': db.fetchone("SELECT COUNT(*) as count FROM articles")['count'],
        'valeur_stock': gestion.get_valeur_stock(),
        'mouvements_jour': db.fetchone("SELECT COUNT(*) as count FROM mouvements WHERE date(date_mouvement) = date('now')")['count'],
        'alertes_stock': db.fetchall("SELECT reference, designation, quantite_stock, seuil_alerte FROM articles WHERE quantite_stock <= seuil_alerte")
    }
    return render_template('dashboard.html', stats=stats, user_role=session['user_role'])

# ---------- API Graphiques ----------
# (conservez toutes vos routes API, je les laisse vides pour ne pas surcharger)
@app.route('/api/evolution_stock_cumule')
@login_required
def api_evolution_stock_cumule():
    periode = request.args.get('periode', '30')
    if periode == '7':
        date_condition = "date(date_mouvement) >= date('now', '-7 days')"
    elif periode == '30':
        date_condition = "date(date_mouvement) >= date('now', '-30 days')"
    elif periode == '365':
        date_condition = "date(date_mouvement) >= date('now', '-365 days')"
    else:
        date_condition = "1=1"

    data = db.fetchall(f"""
        SELECT date(date_mouvement) as jour,
               SUM(CASE WHEN type_mouvement LIKE 'entree%' THEN quantite ELSE -quantite END) as variation
        FROM mouvements
        WHERE {date_condition}
        GROUP BY jour
        ORDER BY jour
    """)

    if not data:
        return jsonify({'labels': [], 'stock_cumule': [], 'variations': []})

    stock_initial_query = db.fetchone(f"""
        SELECT (SELECT SUM(quantite_stock) FROM articles) -
               COALESCE((SELECT SUM(CASE WHEN type_mouvement LIKE 'entree%' THEN quantite ELSE -quantite END)
                         FROM mouvements
                         WHERE {date_condition}), 0) as stock_initial
    """)
    stock_initial = stock_initial_query['stock_initial'] if stock_initial_query['stock_initial'] else 0

    labels, stock_cumule, cumul = [], [], stock_initial
    for row in data:
        labels.append(row['jour'])
        cumul += row['variation']
        stock_cumule.append(cumul)

    return jsonify({
        'labels': labels,
        'stock_cumule': stock_cumule,
        'variations': [row['variation'] for row in data]
    })

@app.route('/api/top_consommations')
@login_required
def api_top_consommations():
    data = db.fetchall("""
        SELECT a.designation, SUM(m.quantite) as total_sorti
        FROM mouvements m
        JOIN articles a ON m.article_id = a.id
        WHERE m.type_mouvement IN ('sortie_affectation', 'sortie_consommation')
        GROUP BY a.id
        ORDER BY total_sorti DESC
        LIMIT 5
    """)
    labels = [row['designation'] for row in data]
    valeurs = [row['total_sorti'] for row in data]
    return jsonify({'labels': labels, 'valeurs': valeurs})

@app.route('/api/stats_complementaires')
@login_required
def api_stats_complementaires():
    sorties_total = db.fetchone("SELECT SUM(quantite) as total FROM mouvements WHERE type_mouvement LIKE 'sortie%'")['total'] or 0
    stock_moyen = db.fetchone("SELECT AVG(quantite_stock) as moyenne FROM articles")['moyenne'] or 0
    taux_rotation = sorties_total / stock_moyen if stock_moyen > 0 else 0
    alertes = db.fetchone("SELECT COUNT(*) as count FROM articles WHERE quantite_stock <= seuil_alerte")['count']
    return jsonify({
        'taux_rotation': round(taux_rotation, 2),
        'alertes': alertes,
        'sorties_total': sorties_total
    })

@app.route('/api/niveau_stock_global')
@login_required
def api_niveau_stock_global():
    total = db.fetchone("SELECT SUM(quantite_stock) as total FROM articles")['total'] or 0
    pourcentage = min(100, round((total / CAPACITE_MAX_STOCK) * 100, 1)) if CAPACITE_MAX_STOCK > 0 else 0
    return jsonify({
        'total': total,
        'capacite': CAPACITE_MAX_STOCK,
        'pourcentage': pourcentage
    })

@app.route('/api/mouvements_par_type')
@login_required
def api_mouvements_par_type():
    data = db.fetchall("""
        SELECT type_mouvement, COUNT(*) as count
        FROM mouvements
        GROUP BY type_mouvement
        ORDER BY count DESC
    """)
    # Traduire les types pour l'affichage
    traductions = {
        'entree_achat': 'Achat',
        'entree_retour': 'Retour',
        'sortie_affectation': 'Affectation',
        'sortie_consommation': 'Consommation'
    }
    labels = [traductions.get(row['type_mouvement'], row['type_mouvement']) for row in data]
    valeurs = [row['count'] for row in data]
    return jsonify({'labels': labels, 'valeurs': valeurs})

@app.route('/api/recent_movements')
@login_required
def recent_movements():
    data = db.fetchall("""
        SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite
        FROM mouvements m
        JOIN articles a ON m.article_id = a.id
        ORDER BY m.date_mouvement DESC
        LIMIT 5
    """)
    return jsonify([dict(row) for row in data])

@app.route('/api/valorisation_stock')
@login_required
def api_valorisation_stock():
    # ... code existant ...
    return jsonify({'articles': []})

@app.route('/api/consommation_periode')
@login_required
def api_consommation_periode():
    # ... code existant ...
    return jsonify([])

@app.route('/api/repartition_stock')
@login_required
def api_repartition_stock():
    data = db.fetchall("""
        SELECT designation, (quantite_stock * COALESCE(prix_unitaire_ht, 0)) as valeur
        FROM articles
        ORDER BY valeur DESC
        LIMIT 5
    """)
    labels = [row['designation'] for row in data]
    valeurs = [row['valeur'] for row in data]
    return jsonify({'labels': labels, 'valeurs': valeurs})

# ---------- Gestion des articles ----------
@app.route('/articles')
@login_required
@permission_required('gerer_articles')
def articles():
    articles = gestion.get_articles()
    return render_template('articles.html', articles=articles)
    
@app.route('/articles/importer', methods=['POST'])
@login_required
@permission_required('gerer_articles')
def importer_articles():
    if 'fichier_excel' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('articles'))

    file = request.files['fichier_excel']
    if file.filename == '':
        flash('Fichier vide', 'danger')
        return redirect(url_for('articles'))

    if not file.filename.lower().endswith('.xlsx'):
        flash('Format non supporté (utilisez .xlsx)', 'danger')
        return redirect(url_for('articles'))

    try:
        wb = openpyxl.load_workbook(file)
        sheet = wb.active
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        nb_importes = 0

        for row in rows:
            if not row or not row[0]:
                continue

            # 1. Extraction de toutes les colonnes dans l'ordre
            reference = str(row[0]).strip()
            designation = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            fournisseur = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            unite = str(row[3]).strip() if len(row) > 3 and row[3] else 'unité'
            quantite = int(row[4]) if len(row) > 4 and row[4] is not None else 0
            prix = float(row[5]) if len(row) > 5 and row[5] is not None else 0.0

            # 2. Créer le fournisseur s'il n'existe pas (après extraction de fournisseur)
            if fournisseur:
                gestion.ajouter_fournisseur_si_inexistant(fournisseur)

            # 3. Créer l'article
            article_id = gestion.ajouter_article(
                reference=reference,
                designation=designation,
                fournisseur=fournisseur,
                unite=unite
            )

            # 4. Mettre à jour le stock et le prix si l'article a bien été créé
            if article_id:
                if quantite > 0:
                    db.execute("UPDATE articles SET quantite_stock = ? WHERE id = ?", (quantite, article_id))
                if prix > 0:
                    db.execute("UPDATE articles SET prix_unitaire_ht = ? WHERE id = ?", (prix, article_id))
                nb_importes += 1

        flash(f'{nb_importes} articles importés avec succès.', 'success')
    except Exception as e:
        flash(f'Erreur lors de l’import : {str(e)}', 'danger')

    return redirect(url_for('articles'))

@app.route('/articles/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('gerer_articles')
def nouvel_article():
    fournisseurs = gestion.get_fournisseurs()
    extracted = {}

    if request.method == 'POST':
        # --- Si un bon de livraison est uploadé, on fait l'OCR et on pré‑remplit ---
        if 'bon_livraison' in request.files and request.files['bon_livraison'].filename != '':
            file = request.files['bon_livraison']
            if allowed_file(file.filename):
                # Sauvegarde du fichier
                ext = file.filename.rsplit('.', 1)[1].lower()
                bon_filename = secure_filename(f"bon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], bon_filename)
                file.save(filepath)

                # Tenter l'OCR
                try:
                    from PIL import Image
                    img = Image.open(filepath)
                    text = pytesseract.image_to_string(img, lang='fra')
                    lines = text.splitlines()
                    for line in lines:
                        ll = line.lower()
                        if 'ref' in ll and not extracted.get('reference'):
                            parts = line.split()
                            if parts:
                                extracted['reference'] = parts[-1]
                        if 'designation' in ll and not extracted.get('designation'):
                            extracted['designation'] = line.replace('designation', '').replace(':', '').strip()
                        if 'fournisseur' in ll and not extracted.get('fournisseur'):
                            extracted['fournisseur'] = line.replace('fournisseur', '').replace(':', '').strip()
                    if extracted:
                        flash("Bon analysé. Vérifiez les champs avant d'enregistrer.", 'success')
                    else:
                        flash("Aucune information n'a été extraite automatiquement. Remplissez manuellement.", 'warning')
                except Exception as e:
                    flash(f"Erreur OCR : {e}. Remplissez manuellement.", 'danger')

                # On réaffiche le formulaire avec les données extraites (sans enregistrer)
                return render_template('article_form.html', fournisseurs=fournisseurs, extracted=extracted)

        # --- Sinon, enregistrement définitif ---
        ref = request.form.get('reference', '')
        des = request.form.get('designation', '')
        fournisseur = request.form.get('fournisseur', '')
        unite = request.form.get('unite', 'unité')
        photo_filename = None

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{ref}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_filename = filename

        gestion.ajouter_article(ref, des, fournisseur=fournisseur, unite=unite, photo=photo_filename)
        flash('Article ajouté avec succès', 'success')
        return redirect(url_for('articles'))

    # Méthode GET
    return render_template('article_form.html', fournisseurs=fournisseurs, extracted={})
    

@app.route('/articles/supprimer/<int:article_id>', methods=['POST'])
@login_required
@permission_required('gerer_articles')
def supprimer_article(article_id):
    mouvements = db.fetchone("SELECT COUNT(*) as count FROM mouvements WHERE article_id = ?", (article_id,))
    if mouvements and mouvements['count'] > 0:
        flash("Impossible de supprimer un article ayant des mouvements.", "danger")
        return redirect(url_for('articles'))
    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    flash("Article supprimé avec succès.", "success")
    return redirect(url_for('articles'))

# ---------- Mouvements ----------
@app.route('/mouvements')
@login_required
def mouvements():
    articles_list = gestion.get_articles()
    techniciens = gestion.get_techniciens()
    return render_template('mouvements_form.html', articles=articles_list, techniciens=techniciens, user_role=session['user_role'])

@app.route('/mouvements/entree', methods=['POST'])
@login_required
@permission_required('gerer_entrees')
def entree():
    article_id = int(request.form['article_id'])
    quantite = int(request.form['quantite'])
    type_entree = request.form['type_entree']
    commentaire = request.form.get('commentaire', '')
    prix_unitaire = request.form.get('prix_unitaire', type=float, default=None)
    bon_commande = request.form.get('bon_commande', '')
    lot = request.form.get('lot', '')
    technicien_id = request.form.get('technicien_id', type=int, default=None)
    # Bon de livraison optionnel
    if 'bon_livraison' in request.files:
        file = request.files['bon_livraison']
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            bon_filename = secure_filename(f"bon_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{article_id}.{ext}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], bon_filename)
            file.save(filepath)
    gestion.entree_stock(article_id, quantite, type_entree, commentaire, prix_unitaire=prix_unitaire, bon_commande=bon_commande, lot=lot, technicien_id=technicien_id)
    flash('Entrée enregistrée', 'success')
    return redirect(url_for('mouvements'))

@app.route('/mouvements/sortie', methods=['POST'])
@login_required
def sortie():
    article_id = int(request.form['article_id'])
    quantite = int(request.form['quantite'])
    commentaire = request.form.get('commentaire', '')
    ticket = request.form.get('ticket', '')
    lot = request.form.get('lot', '')
    if session['user_role'] == 'technicien':
        type_sortie = 'sortie_consommation'
        tech_id = session['user_id']
    else:
        tech_id = int(request.form['technicien_id'])
        type_sortie = request.form['type_sortie']
    try:
        gestion.sortie_stock(article_id, tech_id, quantite, type_sortie, commentaire, ticket, lot)
        flash('Sortie enregistrée', 'success')
    except Exception as e:
        flash(str(e), 'danger')
        return str(e), 400
    return redirect(url_for('mouvements'))

# ---------- Historique ----------
@app.route('/mouvements/historique')
@login_required
def historique_mouvements():
    filtre_article = request.args.get('article_id', type=int)
    filtre_technicien = request.args.get('technicien_id', type=int)
    filtre_ticket = request.args.get('ticket', '').strip()
    filtre_lot = request.args.get('lot', '').strip()
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')

    query = """
        SELECT m.date_mouvement, a.designation, m.type_mouvement, m.quantite,
               u.nom as user_nom, tec.nom as tech_nom, m.commentaire, m.ticket, m.lot
        FROM mouvements m
        JOIN articles a ON m.article_id = a.id
        JOIN utilisateurs u ON m.utilisateur_id = u.id
        LEFT JOIN techniciens tec ON m.technicien_id = tec.id
        WHERE 1=1
    """
    params = []
    if session['user_role'] == 'technicien':
        query += " AND m.technicien_id = ?"
        params.append(session['user_id'])
    else:
        if filtre_technicien:
            query += " AND m.technicien_id = ?"
            params.append(filtre_technicien)

    if filtre_article:
        query += " AND m.article_id = ?"
        params.append(filtre_article)
    if filtre_ticket:
        query += " AND m.ticket LIKE ?"
        params.append(f"%{filtre_ticket}%")
    if filtre_lot:
        query += " AND m.lot LIKE ?"
        params.append(f"%{filtre_lot}%")
    if date_debut:
        query += " AND date(m.date_mouvement) >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND date(m.date_mouvement) <= ?"
        params.append(date_fin)

    query += " ORDER BY m.date_mouvement DESC"
    data = db.fetchall(query, params)
    articles_list = gestion.get_articles()
    techniciens = gestion.get_techniciens()
    return render_template('mouvements_historique.html', mouvements=data, articles=articles_list, techniciens=techniciens, user_role=session['user_role'],
                           filtres={'article_id': filtre_article, 'technicien_id': filtre_technicien, 'ticket': filtre_ticket, 'lot': filtre_lot, 'date_debut': date_debut, 'date_fin': date_fin})

# ---------- Rapports ----------
@app.route('/rapports')
@login_required
def rapports():
    if session['user_role'] == 'technicien':
        return redirect(url_for('dashboard'))

    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')
    if not date_debut:
        date_debut = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = datetime.now().strftime('%Y-%m-%d')

    recherche_valo = request.args.get('recherche_valo', '').strip()
    tri_valo = request.args.get('tri_valo', 'designation')
    ordre_valo = request.args.get('ordre_valo', 'asc')

    # Valorisation
    valorisation_query = """
        SELECT id, reference, designation, quantite_stock, prix_unitaire_ht,
               (quantite_stock * COALESCE(prix_unitaire_ht, 0)) as valeur_eur,
               (quantite_stock * COALESCE(prix_unitaire_ht, 0) * ?) as valeur_mad
        FROM articles
        WHERE 1=1
    """
    params_valo = [TAUX_EUR_MAD]
    if recherche_valo:
        valorisation_query += " AND (reference LIKE ? OR designation LIKE ?)"
        params_valo.extend([f'%{recherche_valo}%', f'%{recherche_valo}%'])

    colonnes_valo = {'designation': 'designation', 'qte_stock': 'quantite_stock', 'valeur': 'valeur_eur'}
    col_tri = colonnes_valo.get(tri_valo, 'designation')
    ordre_sql = 'ASC' if ordre_valo == 'asc' else 'DESC'
    valorisation_query += f" ORDER BY {col_tri} {ordre_sql}"
    valorisation = db.fetchall(valorisation_query, params_valo)

    total_eur = sum(v['valeur_eur'] for v in valorisation) if valorisation else 0
    total_mad = total_eur * TAUX_EUR_MAD

    # Consommation
    recherche_conso = request.args.get('recherche_conso', '').strip()
    tri_conso = request.args.get('tri_conso', 'total_sortie')
    ordre_conso = request.args.get('ordre_conso', 'desc')

    consommation_query = """
        SELECT a.reference, a.designation, COALESCE(a.prix_unitaire_ht, 0) as prix_unitaire_ht,
               COALESCE(SUM(m.quantite), 0) as total_sortie,
               COALESCE(SUM(m.quantite * COALESCE(a.prix_unitaire_ht, 0)), 0) as cout_eur,
               COALESCE(SUM(m.quantite * COALESCE(a.prix_unitaire_ht, 0) * ?), 0) as cout_mad
        FROM articles a
        LEFT JOIN mouvements m ON m.article_id = a.id
            AND m.type_mouvement IN ('sortie_affectation', 'sortie_consommation')
            AND date(m.date_mouvement) BETWEEN ? AND ?
        WHERE 1=1
    """
    params_conso = [TAUX_EUR_MAD, date_debut, date_fin]
    if recherche_conso:
        consommation_query += " AND (a.reference LIKE ? OR a.designation LIKE ?)"
        params_conso.extend([f'%{recherche_conso}%', f'%{recherche_conso}%'])

    consommation_query += " GROUP BY a.id HAVING total_sortie > 0"
    colonnes_conso = {'designation': 'a.designation', 'total_sortie': 'total_sortie', 'cout_eur': 'cout_eur'}
    col_tri_conso = colonnes_conso.get(tri_conso, 'total_sortie')
    ordre_sql_conso = 'ASC' if ordre_conso == 'asc' else 'DESC'
    consommation_query += f" ORDER BY {col_tri_conso} {ordre_sql_conso}"
    consommation = db.fetchall(consommation_query, params_conso)

    total_sorties_qte = sum(c['total_sortie'] for c in consommation)
    total_sorties_eur = sum(c['cout_eur'] for c in consommation)
    total_sorties_mad = total_sorties_eur * TAUX_EUR_MAD

    return render_template('rapports.html',
                           valorisation=valorisation,
                           total_eur=total_eur,
                           total_mad=total_mad,
                           consommation=consommation,
                           date_debut=date_debut,
                           date_fin=date_fin,
                           total_sorties_qte=total_sorties_qte,
                           total_sorties_eur=total_sorties_eur,
                           total_sorties_mad=total_sorties_mad,
                           TAUX_EUR_MAD=TAUX_EUR_MAD,
                           recherche_valo=recherche_valo,
                           tri_valo=tri_valo,
                           ordre_valo=ordre_valo,
                           recherche_conso=recherche_conso,
                           tri_conso=tri_conso,
                           ordre_conso=ordre_conso)

# ---------- Rapports ----------
@app.route('/rapports/balance', methods=['GET', 'POST'])
@login_required
def rapport_balance():
    if session['user_role'] == 'technicien':
        return redirect(url_for('dashboard'))

    mois_selected = None
    annee_selected = None
    data = []
    total_initial = 0
    total_entrees = 0
    total_sorties = 0
    total_final = 0
    nom_mois = ""

    if request.method == 'POST':
        mois_selected = int(request.form.get('mois'))
        annee_selected = int(request.form.get('annee'))
        nom_mois = datetime(annee_selected, mois_selected, 1).strftime('%B %Y').upper()

        articles = db.fetchall("SELECT id, reference, designation FROM articles ORDER BY designation")

        for art in articles:
            article_id = art['id']
            debut_mois = f"{annee_selected}-{mois_selected:02d}-01"
            fin_mois = f"{annee_selected}-{mois_selected:02d}-31"

            entrees_mois = db.fetchone("""
                SELECT COALESCE(SUM(quantite), 0) as total
                FROM mouvements
                WHERE article_id = ? AND type_mouvement LIKE 'entree%'
                  AND date(date_mouvement) >= ? AND date(date_mouvement) <= ?
            """, (article_id, debut_mois, fin_mois))['total']

            sorties_mois = db.fetchone("""
                SELECT COALESCE(SUM(quantite), 0) as total
                FROM mouvements
                WHERE article_id = ? AND type_mouvement LIKE 'sortie%'
                  AND date(date_mouvement) >= ? AND date(date_mouvement) <= ?
            """, (article_id, debut_mois, fin_mois))['total']

            stock_actuel = db.fetchone("SELECT quantite_stock FROM articles WHERE id=?", (article_id,))['quantite_stock']
            stock_initial = stock_actuel - (entrees_mois - sorties_mois)

            total_stock = stock_initial + entrees_mois
            stock_final = total_stock - sorties_mois

            data.append({
                'designation': art['designation'],
                'reference': art['reference'],
                'stock_initial': stock_initial,
                'entrees': entrees_mois,
                'total_stock': total_stock,
                'sorties': sorties_mois,
                'stock_final': stock_final
            })

            total_initial += stock_initial
            total_entrees += entrees_mois
            total_sorties += sorties_mois
            total_final += stock_final

        total_final = total_initial + total_entrees - total_sorties

        if request.form.get('export') == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Produit', 'Reference', 'Stock initial', 'Entrée', 'Total de stock', 'Sortie', 'Stock final'])
            for row in data:
                writer.writerow([row['designation'], row['reference'], row['stock_initial'], row['entrees'], row['total_stock'], row['sorties'], row['stock_final']])
            writer.writerow(['', '', total_initial, total_entrees, '', total_sorties, total_final])
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename=balance_stock_{mois_selected}_{annee_selected}.csv"
            response.headers["Content-type"] = "text/csv; charset=utf-8"
            return response

    # Récupération des années disponibles
    annees_dispo = db.fetchall("SELECT DISTINCT strftime('%Y', date_mouvement) as annee FROM mouvements ORDER BY annee DESC")
    annees = [int(a['annee']) for a in annees_dispo if a['annee']]
    if not annees:
        annees = [datetime.now().year]

    mois_dispo = [(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
                  (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
                  (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')]

    return render_template('rapport_balance.html',
                         mois_selected=mois_selected,
                         annee_selected=annee_selected,
                         nom_mois=nom_mois,
                         data=data,
                         total_initial=total_initial,
                         total_entrees=total_entrees,
                         total_sorties=total_sorties,
                         total_final=total_final,
                         annees=annees,
                         mois_list=mois_dispo,
                         logo_url='https://tse3.mm.bing.net/th/id/OIP.sFqIAPTEKc0PQG4YCPG_VwAAAA?w=400&h=198&rs=1&pid=ImgDetMain')

# ---------- Utilisateurs ----------
@app.route('/utilisateurs')
@login_required
@permission_required('gerer_utilisateurs')
def utilisateurs():
    users = db.fetchall("SELECT id, nom, prenom, login, role, actif FROM utilisateurs ORDER BY nom")
    return render_template('utilisateurs.html', users=users)

@app.route('/utilisateurs/ajouter', methods=['POST'])
@login_required
@permission_required('gerer_utilisateurs')
def ajouter_utilisateur():
    nom = request.form['nom']
    prenom = request.form['prenom']
    login = request.form['login']
    password = request.form['password']
    role = request.form['role']
    actif = 1 if request.form.get('actif') else 0
    try:
        db.execute("INSERT INTO utilisateurs (nom, prenom, login, mot_de_passe, role, actif) VALUES (?,?,?,?,?,?)",
                   (nom, prenom, login, hash_password(password), role, actif))
        flash('Utilisateur ajouté', 'success')
    except:
        flash('Erreur (login déjà existant ?)', 'danger')
    return redirect(url_for('utilisateurs'))

@app.route('/utilisateurs/modifier/<int:user_id>', methods=['POST'])
@login_required
@permission_required('gerer_utilisateurs')
def modifier_utilisateur(user_id):
    perms = {
        'can_manage_users': 1 if request.form.get('can_manage_users') else 0,
        'can_manage_articles': 1 if request.form.get('can_manage_articles') else 0,
        'can_manage_stock_entries': 1 if request.form.get('can_manage_stock_entries') else 0,
        'can_validate_exits': 1 if request.form.get('can_validate_exits') else 0,
        'can_view_reports': 1 if request.form.get('can_view_reports') else 0,
        'can_view_history': 1 if request.form.get('can_view_history') else 0,
    }
    actif = 1 if request.form.get('actif') else 0
    role = request.form.get('role')
    password = request.form.get('password')
    updates = ["actif = ?", "role = ?"]
    params = [actif, role]
    for k, v in perms.items():
        updates.append(f"{k} = ?")
        params.append(v)
    if password:
        updates.append("mot_de_passe = ?")
        params.append(hash_password(password))
    params.append(user_id)
    db.execute(f"UPDATE utilisateurs SET {', '.join(updates)} WHERE id = ?", tuple(params))
    flash('Utilisateur mis à jour', 'success')
    return redirect(url_for('utilisateurs'))

@app.route('/utilisateurs/supprimer/<int:user_id>', methods=['POST'])
@login_required
@permission_required('gerer_utilisateurs')
def supprimer_utilisateur(user_id):
    if user_id == session['user_id']:
        flash("Vous ne pouvez pas vous supprimer", "danger")
    else:
        db.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
        flash('Utilisateur supprimé', 'success')
    return redirect(url_for('utilisateurs'))

# ---------- Techniciens ----------
@app.route('/techniciens')
@login_required
@permission_required('gerer_utilisateurs')
def techniciens():
    techs = gestion.get_techniciens()
    return render_template('techniciens.html', techniciens=techs)

@app.route('/techniciens/ajouter', methods=['POST'])
@login_required
@permission_required('gerer_utilisateurs')
def ajouter_technicien_route():
    gestion.ajouter_technicien(request.form['nom'], request.form['prenom'], request.form.get('code', ''))
    flash('Technicien ajouté', 'success')
    return redirect(url_for('techniciens'))

@app.route('/techniciens/supprimer/<int:tech_id>', methods=['POST'])
@login_required
@permission_required('gerer_utilisateurs')
def supprimer_technicien_route(tech_id):
    gestion.supprimer_technicien(tech_id)
    flash('Technicien supprimé', 'success')
    return redirect(url_for('techniciens'))

# ---------- Fournisseurs ----------
@app.route('/fournisseurs')
@login_required
@permission_required('gerer_articles')
def fournisseurs():
    liste = gestion.get_fournisseurs()
    return render_template('fournisseurs.html', fournisseurs=liste)

@app.route('/fournisseurs/ajouter', methods=['POST'])
@login_required
@permission_required('gerer_articles')
def ajouter_fournisseur():
    gestion.ajouter_fournisseur(request.form['nom'], request.form.get('ice', ''), request.form.get('telephone', ''),
                                request.form.get('email', ''), request.form.get('site_web', ''))
    flash('Fournisseur ajouté', 'success')
    return redirect(url_for('fournisseurs'))

@app.route('/fournisseurs/modifier/<int:fournisseur_id>', methods=['POST'])
@login_required
@permission_required('gerer_articles')
def modifier_fournisseur(fournisseur_id):
    gestion.modifier_fournisseur(fournisseur_id, nom=request.form.get('nom'), ice=request.form.get('ice'),
                                 telephone=request.form.get('telephone'), email=request.form.get('email'),
                                 site_web=request.form.get('site_web'))
    flash('Fournisseur modifié', 'success')
    return redirect(url_for('fournisseurs'))

@app.route('/fournisseurs/supprimer/<int:fournisseur_id>', methods=['POST'])
@login_required
@permission_required('gerer_articles')
def supprimer_fournisseur(fournisseur_id):
    gestion.supprimer_fournisseur(fournisseur_id)
    flash('Fournisseur supprimé', 'success')
    return redirect(url_for('fournisseurs'))

# ---------- Logs ----------
@app.route('/logs')
@login_required
@permission_required('gerer_utilisateurs')
def logs():
    user_id = request.args.get('user_id', type=int)
    query = "SELECT l.*, u.nom, u.prenom, u.login FROM logs l JOIN utilisateurs u ON l.utilisateur_id = u.id"
    params = []
    if user_id:
        query += " WHERE l.utilisateur_id = ?"
        params.append(user_id)
    query += " ORDER BY l.date_log DESC LIMIT 500"
    logs_data = db.fetchall(query, params)
    users = db.fetchall("SELECT id, nom, prenom, login FROM utilisateurs ORDER BY nom")
    return render_template('logs.html', logs=logs_data, users=users, filtre_user_id=user_id)

# ---------- Démarrage ----------
def ouvrir_navigateur():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    threading.Thread(target=ouvrir_navigateur, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)