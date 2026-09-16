from flask import Flask, jsonify, request
from flask_cors import CORS
from pipeline import construire_payload
from conx import connection_vault
from cox import connection
import logging
import hashlib
from test import classification_colonnes
from proxy import get_cursor, AnonymisationUnifiee, DEGRES_CONFIG, _charger_matrice_acces

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

def cv():
    return connection_vault.cursor()

def co():
    return connection.cursor()

def normaliser_niveau(val: str) -> str:
    if not val:
        return val
    mapping = {
        "CRITIQUE": "CRITIQUE",
        "ÉLEVÉ":    "ÉLEVÉ",
        "ELEVE":    "ÉLEVÉ",
        "MODÉRÉ":   "MODÉRÉ",
        "MODERE":   "MODÉRÉ",
        "FAIBLE":   "FAIBLE",
    }
    return mapping.get(str(val).strip().upper(), val)

def verify_password_oracle(password_attempt, stored_hash):
    computed = hashlib.md5(
        password_attempt.encode('utf-8')
    ).hexdigest().upper()
    return computed == stored_hash.upper()

@app.route("/api/table")
def get_table():
    try:
        cur = cv()
        cur.execute("SELECT * FROM RGPD_CLASSIFICATION_CACHE")
        columns = [col[0] for col in cur.description]
        rows    = cur.fetchall()
        cur.close()
        return jsonify({"columns": columns, "rows": rows})
    except Exception as e:
        logger.error(f"Erreur get_table : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/scan-anonymise", methods=["POST"])
def anonymise():
    try:
        # ← ton vrai fichier
        resultats = classification_colonnes()

        if not resultats:
            return jsonify({
                "status":  "error",
                "message": "Aucun résultat retourné"
            }), 500

        logger.info(f"Scan terminé — {len(resultats)} colonnes traitées")
        return jsonify({
            "status":  "ok",
            "message": f"Scan terminé — {len(resultats)} colonnes traitées",
            "count":   len(resultats),
        })

    except Exception as e:
        logger.error(f"Erreur scan-anonymise : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/Login", methods=["POST"])
def login():
    data             = request.json
    login_id         = data.get("login")
    password_attempt = data.get("password")

    if not login_id or not password_attempt:
        return jsonify({"success": False, "error": "Données manquantes"}), 400

    try:

        import hashlib
        pwd_hash = hashlib.sha1(
            password_attempt.encode('utf-8')
        ).hexdigest().upper()

        cur = cv()
        cur.execute("""
            SELECT ROLE, ID_ACCES
            FROM   Vault_ACCES
            WHERE  LOGIN       = :1
              AND  MOT_DE_PASSE = :2
              AND  STATUT      = 'ACTIF'
        """, [login_id, pwd_hash])
        user = cur.fetchone()
        cur.close()

        if user:
            return jsonify({
                "success": True,
                "role":    user[0],
                "id_user": str(user[1]),
                "nom":     login_id,
                "login":   login_id,
            })

        return jsonify({
            "success": False,
            "message": "Identifiants incorrects"
        }), 401

    except Exception as e:
        logger.error(f"Erreur login : {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/clear-cache", methods=["POST"])
def clear_cache():

    try:
        cur = cv()
        cur.execute("SELECT COUNT(*) FROM RGPD_CLASSIFICATION_CACHE")
        count = cur.fetchone()[0]

        cur.execute("DELETE FROM RGPD_CLASSIFICATION_CACHE")
        cur.close()
        connection_vault.commit()

        logger.info(f"Cache RGPD vidé — {count} entrées supprimées")
        return jsonify({
            "status": "ok",
            "message": f"Cache vidé avec succès",
            "deleted": count,
        })

    except Exception as e:
        logger.error(f"Erreur clear_cache : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/reclassifier", methods=["POST"])
def reclassify():
    data           = request.json
    table          = data.get("table")
    colonne        = data.get("colonne")
    nouveau_niveau = normaliser_niveau(data.get("niveau"))

    if not all([table, colonne, nouveau_niveau]):
        return jsonify({"error": "table, colonne et niveau requis"}), 400

    try:
        table   = table.upper()
        colonne = colonne.upper()

        cur = cv()
        cur.execute("""
            SELECT NIVEAU FROM RGPD_CLASSIFICATION_CACHE
            WHERE  TABLE_NAME  = :1
              AND  COLUMN_NAME = :2
        """, [table, colonne])
        row = cur.fetchone()
        cur.close()

        if not row:
            return jsonify({
                "status":  "error",
                "message": f"Aucune entrée dans le cache pour {table}.{colonne}"
            }), 404

        ancien_niveau = normaliser_niveau(row[0])

        if ancien_niveau == nouveau_niveau:
            return jsonify({
                "status":  "ok",
                "message": "Niveau identique, aucune modification",
                "ancien":  ancien_niveau,
                "nouveau": nouveau_niveau,
            })

        cur = cv()
        cur.execute("""
            UPDATE RGPD_CLASSIFICATION_CACHE
            SET    NIVEAU = :1
            WHERE  TABLE_NAME  = :2
              AND  COLUMN_NAME = :3
        """, [nouveau_niveau, table, colonne])
        cur.close()
        connection_vault.commit()

        logger.info(f"Reclassification {table}.{colonne} : {ancien_niveau} → {nouveau_niveau}")
        return jsonify({
            "status":  "ok",
            "ancien":  ancien_niveau,
            "nouveau": nouveau_niveau,
        })

    except Exception as e:
        logger.error(f"Erreur reclassifier : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/simulate-anonymisation", methods=["POST"])
def simulate_anonymisation():
    try:
        data = request.json
        role = data.get("role")

        if not role:
            return jsonify({"status": "error", "message": "role requis"}), 400

        # 1. Charger la matrice d'accès pour ce rôle

        matrice = _charger_matrice_acces(role.upper())

        # 2. Récupérer les colonnes classifiées
        cur = cv()
        cur.execute("SELECT TABLE_NAME, COLUMN_NAME, NIVEAU FROM RGPD_CLASSIFICATION_CACHE")
        colonnes = cur.fetchall()
        cur.close()

        if not colonnes:
            return jsonify({
                "status":  "error",
                "message": "Aucune classification trouvée, lancez un scan d'abord"
            }), 400

        # 3. Pour chaque colonne, récupérer une valeur et anonymiser
        anon    = AnonymisationUnifiee()
        preview = []
        cur     = co()

        for table, colonne, niveau in colonnes[:20]:
            # normaliser le niveau
            _norm = {
                'ELEVE': 'ÉLEVÉ', 'ÉLEVÉ': 'ÉLEVÉ',
                'MODERE': 'MODÉRÉ', 'MODÉRÉ': 'MODÉRÉ',
                'CRITIQUE': 'CRITIQUE', 'FAIBLE': 'FAIBLE',
            }
            niveau_norm = _norm.get(niveau.upper(), niveau.upper())
            degre       = matrice.get(niveau_norm, "DEGRE0")

            try:
                cur.execute(f"SELECT {colonne} FROM {table} WHERE ROWNUM = 1")
                result           = cur.fetchone()
                valeur_originale = str(result[0]) if result and result[0] else "NULL"

                # appliquer anonymisation selon le degré
                if degre == "DEGRE0" or degre not in DEGRES_CONFIG:
                    valeur_anonymisee = valeur_originale  # pas d'anonymisation
                else:
                    config = DEGRES_CONFIG[degre]
                    # détecter le type de la valeur
                    import re
                    from datetime import datetime
                    if re.match(r'^\d{4}-\d{2}-\d{2}', valeur_originale):
                        date_obj          = anon._to_datetime(valeur_originale)
                        mode              = config['date']['generalisation']
                        valeur_anonymisee = anon._generaliser_date(date_obj, mode).strftime('%Y-%m-%d')
                    elif re.match(r'^\d+(\.\d+)?$', valeur_originale):
                        cfg               = config['numerique']
                        valeur_anonymisee = str(anon._appliquer_bruit(float(valeur_originale), cfg['sigma_pct'], cfg['bruit']))
                    else:
                        cfg               = config['texte']
                        func              = getattr(anon, cfg['type_anon'])
                        valeur_anonymisee = func(valeur_originale)

                preview.append({
                    "table":     table,
                    "colonne":   colonne,
                    "niveau":    niveau_norm,
                    "degre":     degre,
                    "original":  valeur_originale,
                    "anonymise": str(valeur_anonymisee),
                })

            except Exception as e:
                logger.warning(f"Erreur simulation {table}.{colonne} : {e}")
                continue

        cur.close()

        return jsonify({
            "status":  "ok",
            "role":    role,
            "preview": preview,
        })

    except Exception as e:
        logger.error(f"Erreur simulate_anonymisation : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    data    = request.json
    id_user = data.get("id_user")
    role    = data.get("role")
    login   = data.get("login")
    nom     = data.get("nom")
    table   = data.get("table", "CLIENTS")

    if not id_user or not role:
        return jsonify({"error": "id_user et role requis"}), 400

    try:
        anon = AnonymisationUnifiee()
        employee_info = {
            "name":   nom or login or id_user,
            "role":   role.capitalize(),
            "id":     id_user,
            "avatar": (nom or login or "?")[0].upper(),
        }
        payload = construire_payload(anon, id_user, role, table, employee_info)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erreur dashboard : {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@app.route("/api/access-matrix")
def get_access_matrix():
    try:
        cur = cv()
        cur.execute("SELECT * FROM ACCESS_MATRIX")
        col_names = [col[0].upper() for col in cur.description]
        rows_raw  = cur.fetchall()
        cur.close()

        logger.info(f"Colonnes ACCESS_MATRIX : {col_names}")

        # Mapping dynamique : vrai nom colonne Oracle → clé normalisée
        col_map = {}
        for col in col_names:
            n = normaliser_niveau(col)
            # normaliser_niveau retourne "ÉLEVÉ"/"MODÉRÉ" — on veut ELEVE/MODERE
            reverse = {
                "CRITIQUE": "CRITIQUE",
                "ÉLEVÉ":    "ELEVE",
                "MODÉRÉ":   "MODERE",
                "FAIBLE":   "FAIBLE",
            }
            col_map[col] = reverse.get(n, col)

        result = []
        for r in rows_raw:
            row_dict = {"role": r[0]}
            for i, col in enumerate(col_names[1:], 1):
                key = col_map.get(col, col)
                row_dict[key] = r[i]
            result.append(row_dict)

        logger.info(f"Matrice construite : {result}")
        return jsonify({"rows": result})

    except Exception as e:
        logger.error(f"Erreur get_access_matrix : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/access-matrix/update", methods=["POST"])
def update_access_matrix():
    try:
        d      = request.json
        niveau = d.get("niveau", "").strip().upper()
        degre  = d.get("degre")
        role   = d.get("role")

        logger.info(f"Update matrice → role={role}, niveau={niveau}, degre={degre}")

        if not all([niveau, degre, role]):
            return jsonify({
                "status":  "error",
                "message": "niveau, degre et role requis"
            }), 400

        # Récupérer les vraies colonnes Oracle
        cur = cv()
        cur.execute("SELECT * FROM ACCESS_MATRIX WHERE ROWNUM = 1")
        col_names = [col[0].upper() for col in cur.description]
        cur.close()
        logger.info(f"Colonnes Oracle : {col_names}")

        # Trouver la colonne Oracle correspondant au niveau envoyé
        col_found = None
        for col in col_names:
            col_norm   = normaliser_niveau(col)
            niveau_norm = normaliser_niveau(niveau)
            # Comparer après normalisation vers ELEVE/MODERE
            reverse = {
                "ÉLEVÉ":  "ELEVE",
                "MODÉRÉ": "MODERE",
            }
            c = reverse.get(col_norm, col_norm)
            n = reverse.get(niveau_norm, niveau_norm)
            if c == n:
                col_found = col
                break

        if not col_found:
            logger.error(f"Colonne introuvable pour '{niveau}' — disponibles : {col_names}")
            return jsonify({
                "status":  "error",
                "message": f"Niveau '{niveau}' introuvable — colonnes Oracle : {col_names}",
            }), 400

        cur = cv()
        cur.execute(
            f'UPDATE ACCESS_MATRIX SET "{col_found}"=:1 WHERE ROLE=:2',
            (degre, role)
        )
        rows_affected = cur.rowcount
        cur.close()
        connection_vault.commit()

        logger.info(f"OK : {role} / {col_found} → {degre} ({rows_affected} ligne(s))")

        if rows_affected == 0:
            return jsonify({
                "status":  "warn",
                "message": f"Rôle '{role}' introuvable dans ACCESS_MATRIX",
            })

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"Erreur update_access_matrix : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/LoginAdmin", methods=["POST"])
def login_admin():
    data             = request.json
    login_id         = data.get("login")
    password_attempt = data.get("password")

    if not login_id or not password_attempt:
        return jsonify({"success": False, "error": "Données manquantes"}), 400

    try:
        cur = cv()
        cur.execute("""
            SELECT ID_ADMIN, NOM, PRENOM, LOGIN, MOT_DE_PASSE
            FROM   ADMIN
            WHERE  LOGIN  = :1
              AND  STATUT = 'ACTIF'
        """, [login_id])
        user = cur.fetchone()
        cur.close()

        # ← comparaison texte clair au lieu de SHA1
        if user and password_attempt == user[4]:
            return jsonify({
                "success":  True,
                "role":     "Admin",
                "id_user":  str(user[0]),
                "nom":      user[1],
                "prenom":   user[2],
                "login":    user[3],
            })
        return jsonify({
            "success": False,
            "message": "Identifiants incorrects"
        }), 401

    except Exception as e:
        logger.error(f"Erreur login_admin : {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ── Get Matrix alternative ────────────────────────────────────────────────
@app.route('/api/get-matrix', methods=['GET'])
def get_matrix():
    try:
        cur = cv()
        cur.execute("SELECT * FROM ACCESS_MATRIX")
        col_names = [col[0].upper() for col in cur.description]
        rows_raw  = cur.fetchall()
        cur.close()

        result = []
        for r in rows_raw:
            row_dict = {}
            for i, col in enumerate(col_names):
                row_dict[col] = r[i]
            result.append(row_dict)

        return jsonify({"status": "ok", "matrix": result})
    except Exception as e:
        logger.error(f"Erreur get_matrix : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/test-proxy", methods=["GET"])
def test_proxy():

    try:
        login = request.args.get("login", "analyste")
        cursor = get_cursor(login)


        cursor.execute("SELECT COUNT(*) FROM CLIENTS")
        total_clients = cursor.fetchone()[0]


        cursor.execute("SELECT COUNT(*) FROM COMPTES")
        total_comptes = cursor.fetchone()[0]


        cursor.execute("SELECT SUM(SOLDE) FROM COMPTES")
        row_sum = cursor.fetchone()
        balance_raw = row_sum[0] if row_sum and row_sum[0] else 0
        balance_sum = f"{round(float(balance_raw)):,} DT".replace(",", " ")


        cursor.execute("SELECT COUNT(*) FROM CREDITS")
        total_credits = cursor.fetchone()[0]


        cursor.execute("""
            SELECT
                C.ID_CLIENT,
                C.NOM,
                C.PRENOM,
                C.DATE_NAISSANCE,
                CO.NUMERO_COMPTE,
                CO.TYPE_COMPTE,
                CO.SOLDE,
                CO.DATE_OUVERTURE
            FROM CLIENTS C
            JOIN COMPTES CO ON C.ID_CLIENT = CO.ID_CLIENT
            ORDER BY C.ID_CLIENT
        """)
        cols1 = [d[0] for d in cursor.description]
        rows1 = [[str(v) if v is not None else "—" for v in r] for r in cursor.fetchall()]


        cursor.execute("""
            SELECT
                CR.ID_CREDIT,
                CR.TYPE_CREDIT,
                CR.MONTANT_CREDIT,
                CR.TAUX_INTERET,
                CR.DUREE_MOIS,
                CR.DATE_DEBUT
            FROM CREDITS CR
            ORDER BY CR.ID_CREDIT
        """)
        cols2 = [d[0] for d in cursor.description]
        rows2 = [[str(v) if v is not None else "—" for v in r] for r in cursor.fetchall()]


        cursor.execute("""
            SELECT
                CB.ID_CARTE,
                CB.TYPE_CARTE,
                CB.DATE_EXPIRATION,
                CO.TYPE_COMPTE
            FROM CARTES_BANCAIRES CB
            JOIN COMPTES CO ON CB.ID_COMPTE = CO.ID_COMPTE
            ORDER BY CB.ID_CARTE
        """)
        cols3 = [d[0] for d in cursor.description]
        rows3 = [[str(v) if v is not None else "—" for v in r] for r in cursor.fetchall()]

        return jsonify({
            "success":          True,
            "total_anonymized": total_clients,
            "critical_count":   total_comptes,
            "balance_sum":      balance_sum,
            "total_credits":    total_credits,
            "columns":          cols1,
            "rows":             rows1,
            "columns2":         cols2,
            "rows2":            rows2,
            "columns3":         cols3,
            "rows3":            rows3,
        })

    except PermissionError as e:
        logger.warning(f"[PROXY] Accès refusé : {e}")
        return jsonify({"success": False, "message": str(e)}), 403

    except Exception as e:
        logger.error(f"[PROXY] Erreur : {e}")
        return jsonify({"success": False, "message": str(e)}), 500




@app.route("/api/clients-conseiller", methods=["GET"])
def clients_conseiller():
    try:
        id_acces = request.args.get("id_acces")
        if not id_acces:
            return jsonify({"success": False, "message": "id_acces requis"}), 400


        cur_vault = cv()
        cur_vault.execute("""
            SELECT ID_CLIENT
            FROM AFFECTATION_CONSEILLER
            WHERE ID_ACCES = :1
        """, [id_acces])
        affectations = cur_vault.fetchall()
        cur_vault.close()

        if not affectations:
            return jsonify({
                "success": True,
                "clients": [],
                "message": "Aucun client affecté"
            })

        ids_clients  = [str(r[0]) for r in affectations]
        placeholders = ",".join([f":{i+1}" for i in range(len(ids_clients))])


        cur_main = co()
        cur_main.execute(f"""
            SELECT C.ID_CLIENT, C.NOM, C.PRENOM,
                   C.DATE_NAISSANCE, C.TELEPHONE, C.ADRESSE,
                   CO.NUMERO_COMPTE, CO.TYPE_COMPTE,
                   CO.SOLDE, CO.DATE_OUVERTURE
            FROM CLIENTS C
            LEFT JOIN COMPTES CO ON C.ID_CLIENT = CO.ID_CLIENT
            WHERE C.ID_CLIENT IN ({placeholders})
            ORDER BY C.NOM
        """, ids_clients)

        cols = [d[0] for d in cur_main.description]
        rows = cur_main.fetchall()
        cur_main.close()

        clients = []
        for r in rows:
            row_dict = {}
            for i, col in enumerate(cols):
                val = r[i]
                row_dict[col] = str(val) if val is not None else "—"
            clients.append(row_dict)

        return jsonify({
            "success": True,
            "count":   len(clients),
            "clients": clients,
        })

    except Exception as e:
        logger.error(f"Erreur clients_conseiller : {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/client-details", methods=["GET"])
def client_details():
    try:
        id_client = request.args.get("id")
        if not id_client:
            return jsonify({"success": False, "message": "id requis"}), 400

        cur = co()

        cur.execute("""
            SELECT CO.NUMERO_COMPTE, CO.TYPE_COMPTE,
                   CO.SOLDE, CO.DATE_OUVERTURE
            FROM COMPTES CO
            WHERE CO.ID_CLIENT = :1
        """, [id_client])
        cols_comptes = [d[0] for d in cur.description]
        rows_comptes = [[str(v) if v is not None else "—" for v in r]
                        for r in cur.fetchall()]


        cur.execute("""
            SELECT CR.TYPE_CREDIT, CR.MONTANT_CREDIT,
                   CR.TAUX_INTERET, CR.DUREE_MOIS, CR.DATE_DEBUT
            FROM CREDITS CR
            WHERE CR.ID_CLIENT = :1
        """, [id_client])
        cols_credits = [d[0] for d in cur.description]
        rows_credits = [[str(v) if v is not None else "—" for v in r]
                        for r in cur.fetchall()]

        cur.execute("""
            SELECT CB.TYPE_CARTE, CB.DATE_EXPIRATION
            FROM CARTES_BANCAIRES CB
            JOIN COMPTES CO ON CB.ID_COMPTE = CO.ID_COMPTE
            WHERE CO.ID_CLIENT = :1
        """, [id_client])
        cols_cartes = [d[0] for d in cur.description]
        rows_cartes = [[str(v) if v is not None else "—" for v in r]
                       for r in cur.fetchall()]

        cur.execute("""
            SELECT T.ID_TRANSACTION,
                   T.DATE_TRANSACTION,
                   T.TYPE_TRANSACTION,
                   T.MONTANT_TRANSACTION,
                   CO.NUMERO_COMPTE
            FROM TRANSACTIONS T
            JOIN COMPTES CO ON T.ID_COMPTE = CO.ID_COMPTE
            WHERE CO.ID_CLIENT = :1
            ORDER BY T.DATE_TRANSACTION DESC
        """, [id_client])
        cols_tx = [d[0] for d in cur.description]
        rows_tx = [[str(v) if v is not None else "—" for v in r]
                   for r in cur.fetchall()]

        cur.close()

        return jsonify({
            "success":       True,
            "cols_comptes":  cols_comptes,
            "rows_comptes":  rows_comptes,
            "cols_credits":  cols_credits,
            "rows_credits":  rows_credits,
            "cols_cartes":   cols_cartes,
            "rows_cartes":   rows_cartes,
            "cols_tx":       cols_tx,
            "rows_tx":       rows_tx,
        })

    except Exception as e:
        logger.error(f"Erreur client_details : {e}")
        return jsonify({"success": False, "message": str(e)}), 500


MOTS_INTERDITS = {
    "DROP", "DELETE", "TRUNCATE", "INSERT",
    "UPDATE", "ALTER", "CREATE", "GRANT",
    "REVOKE", "EXEC", "EXECUTE",
}

@app.route("/api/sql-execute", methods=["POST", "OPTIONS"])
def sql_execute():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    sql = (data.get("sql") or "").strip()
    login = (data.get("login") or "").strip()
    if not login:
        return jsonify({"status": "error", "message": "Login requis"}), 400
    role = (data.get("role") or "").strip().upper()

    if not sql:
        return jsonify({"status": "error", "message": "Requête vide"}), 400

    sql_upper = sql.upper()

    for mot in MOTS_INTERDITS:
        if mot in sql_upper:
            return jsonify({
                "status": "error",
                "message": f"Opération interdite : '{mot}' non autorisé en mode évaluation.",
            }), 403

    if not sql_upper.lstrip().startswith("SELECT"):
        return jsonify({
            "status": "error",
            "message": "Seules les requêtes SELECT sont autorisées.",
        }), 403

    if not role:
        try:
            cur_v = cv()
            cur_v.execute(
                "SELECT ROLE FROM Vault_ACCES WHERE LOGIN = :1 AND STATUT = 'ACTIF'",
                [login]
            )
            row_r = cur_v.fetchone()
            cur_v.close()
            role = row_r[0].strip().upper() if row_r else login.upper()
        except Exception as e:
            logger.warning(f"[SQL] Impossible de résoudre le rôle pour {login} : {e}")
            role = login.upper()

    logger.info(f"[SQL] login={login} role={role} — {sql[:80]}")

    try:
        cursor = get_cursor(login)
    except Exception as e:
        logger.error(f"[SQL] get_cursor({login}) : {e}")
        return jsonify({
            "status": "error",
            "message": f"Connexion DB impossible : {e}",
        }), 500


    try:
        cursor.execute(sql)

        if not cursor.description:
            return jsonify({
                "status": "ok",
                "columns": [],
                "rows": [],
                "count": 0,
                "role": role,
                "anon_info": [],
                "message": "Requête exécutée — aucune colonne retournée.",
            })

        columns = [col[0] for col in cursor.description]
        raw = cursor.fetchmany(200)
        rows = [
            [str(v) if v is not None else "NULL" for v in row]
            for row in raw
        ]

        try:
            matrice = _charger_matrice_acces(role)
        except Exception as e:
            logger.warning(f"[SQL] Matrice introuvable pour rôle={role} : {e}")
            matrice = {}

        _norm_map = {
            "ELEVE": "ÉLEVÉ", "ÉLEVÉ": "ÉLEVÉ",
            "MODERE": "MODÉRÉ", "MODÉRÉ": "MODÉRÉ",
            "CRITIQUE": "CRITIQUE",
            "FAIBLE": "FAIBLE",
        }
        anon_info = []
        try:
            cur_v = cv()
            for col_name in columns:
                cur_v.execute("""
                    SELECT TABLE_NAME, NIVEAU
                    FROM   RGPD_CLASSIFICATION_CACHE
                    WHERE  COLUMN_NAME = :1
                    AND    ROWNUM = 1
                """, [col_name.upper()])
                res = cur_v.fetchone()

                if res:
                    niveau_norm = _norm_map.get(res[1].strip().upper(), res[1].strip())
                    degre = matrice.get(niveau_norm, "DEGRE0")
                    anon_info.append({
                        "colonne": col_name,
                        "table": res[0],
                        "niveau": niveau_norm,
                        "degre": degre,
                        "anonymise": degre != "DEGRE0",
                    })
                else:
                    anon_info.append({
                        "colonne": col_name,
                        "table": "—",
                        "niveau": "Non classifié",
                        "degre": "—",
                        "anonymise": False,
                    })
            cur_v.close()
        except Exception as e:
            logger.warning(f"[SQL] Erreur chargement anon_info : {e}")
            anon_info = []

        logger.info(f"[SQL] {login} ({role}) — {len(rows)} lignes retournées")

        return jsonify({
            "status": "ok",
            "columns": columns,
            "rows": rows,
            "count": len(rows),
            "role": role,
            "anon_info": anon_info,
        })

    except Exception as e:
        logger.warning(f"[SQL] Erreur exécution ({login}) : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
if __name__ == "__main__":
    app.run(port=5000, debug=True)