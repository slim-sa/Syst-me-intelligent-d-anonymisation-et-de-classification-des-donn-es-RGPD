from cox import connection, cursor as _cursor_base
from conx import connection_vault, cursor_vault
from key import load_or_create_key

import hashlib
import string
import numpy as np
import logging
import re
import secrets
from datetime import datetime
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

CLE = load_or_create_key()

DEGRES_CONFIG = {
    'DEGRE3': {
        'texte':     {'technique': 'FPE_PRESERVE_LENGTH',    'type_anon': 'fpe_preserve_length'},
        'date':      {'technique': 'DATE_ANNEE',             'generalisation': 'annee'},
        'numerique': {'technique': 'LAPLACIEN_s10pct',       'bruit': 'laplacien', 'sigma_pct': 10},
    },
    'DEGRE2': {
        'texte':     {'technique': 'TOKENISATION_STABLE',    'type_anon': 'tokeniser_simple'},
        'date':      {'technique': 'DATE_TRIMESTRE',         'generalisation': 'trimestre'},
        'numerique': {'technique': 'GAUSSIEN_s8pct',         'bruit': 'gaussien', 'sigma_pct': 8},
    },
    'DEGRE1': {
        'texte':     {'technique': 'MASQUAGE_PARTIEL_50pct', 'type_anon': 'masquer_partiel'},
        'date':      {'technique': 'DATE_MOIS',              'generalisation': 'mois'},
        'numerique': {'technique': 'UNIFORME_s5pct',         'bruit': 'uniforme', 'sigma_pct': 5},
    },
}

DEGRE_SANS_ANON = 'DEGRE0'


class AnonymisationUnifiee:

    def __init__(self):
        self.cipher = Fernet(CLE)
        self._token_cache = {}

    def _chiffrer(self, valeur: str) -> str:
        return self.cipher.encrypt(str(valeur).encode()).decode()

    def _dechiffrer(self, valeur_chiffree) -> str:
        if hasattr(valeur_chiffree, 'read'):
            valeur_chiffree = valeur_chiffree.read()
        return self.cipher.decrypt(str(valeur_chiffree).encode()).decode()

    def tokeniser_simple(self, texte: str) -> str:
        if not texte or texte.strip() == '':
            return texte
        if texte not in self._token_cache:
            combined = f"{texte}:{CLE.decode()[:8]}"
            token = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16].upper()
            self._token_cache[texte] = f"TOKEN_{token}"
        return self._token_cache[texte]

    def fpe_preserve_length(self, texte: str) -> str:
        if not texte or texte.strip() == '':
            return texte
        resultat = []
        for char in texte:
            if char.isalpha():
                resultat.append(
                    secrets.choice(string.ascii_uppercase if char.isupper()
                                   else string.ascii_lowercase)
                )
            elif char.isdigit():
                resultat.append(secrets.choice(string.digits))
            else:
                resultat.append(char)
        return ''.join(resultat)

    def masquer_partiel(self, texte: str, ratio: float = 0.5) -> str:
        if not texte or texte.strip() == '':
            return texte
        longueur   = len(texte)
        nb_masques = max(1, int(longueur * ratio))
        positions  = set(secrets.choice(range(longueur)) for _ in range(nb_masques))
        return ''.join(
            '*' if i in positions and c not in (' ', '\t', '\n') else c
            for i, c in enumerate(texte)
        )

    def _to_datetime(self, valeur) -> datetime:
        if valeur is None:
            return None
        if isinstance(valeur, datetime):
            return valeur
        formats = [
            '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(valeur).strip(), fmt)
            except ValueError:
                continue
        raise ValueError(f"Format de date non reconnu : {valeur}")

    def _generaliser_date(self, valeur_date: datetime, mode: str) -> datetime:
        if valeur_date is None:
            return None
        if mode == 'annee':
            return datetime(valeur_date.year, 1, 1)
        elif mode == 'trimestre':
            mois_debut = ((valeur_date.month - 1) // 3) * 3 + 1
            return datetime(valeur_date.year, mois_debut, 1)
        elif mode == 'mois':
            return datetime(valeur_date.year, valeur_date.month, 1)
        raise ValueError(f"Mode de généralisation inconnu : {mode}")

    def _appliquer_bruit(self, valeur: float, sigma_pct: int, type_bruit: str) -> float:
        if valeur is None or valeur == 0:
            return valeur
        echelle = abs(valeur) * sigma_pct / 100
        if type_bruit == 'gaussien':
            bruit = np.random.normal(0, echelle)
        elif type_bruit == 'laplacien':
            bruit = np.random.laplace(0, echelle)
        elif type_bruit == 'uniforme':
            bruit = np.random.uniform(-echelle, echelle)
        else:
            raise ValueError(f"Type de bruit inconnu : {type_bruit}")
        return max(round(valeur + bruit, 2), 0)

    def _get_cle_primaire(self, table: str) -> list[str]:
        from cox import cursor
        cursor.execute("""
            SELECT ucc.COLUMN_NAME
            FROM USER_CONS_COLUMNS ucc
            JOIN USER_CONSTRAINTS  uc
              ON ucc.CONSTRAINT_NAME = uc.CONSTRAINT_NAME
            WHERE uc.TABLE_NAME      = :1
              AND uc.CONSTRAINT_TYPE = 'P'
            ORDER BY ucc.POSITION
        """, [table.upper()])
        cols = [row[0] for row in cursor.fetchall()]
        if not cols:
            raise ValueError(
                f"Table '{table}' n'a pas de clé primaire — "
                f"anonymisation impossible sans PK."
            )
        return cols

    def _construire_where_pk(self, pk_cols: list[str]) -> str:
        return " AND ".join(f"{col} = :{i+1}" for i, col in enumerate(pk_cols))

    def _pk_vers_str(self, pk_cols: list[str], valeurs_pk: tuple) -> str:
        return "|".join(f"{col}={val}" for col, val in zip(pk_cols, valeurs_pk))

    def _detecter_type_donnee(self, table: str, colonne: str) -> str:
        from cox import cursor
        cursor.execute("""
            SELECT DATA_TYPE
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME  = :1
              AND COLUMN_NAME = :2
        """, [table.upper(), colonne.upper()])
        row = cursor.fetchone()
        if not row:
            return None
        t = row[0]
        if t in ('VARCHAR2', 'VARCHAR', 'CHAR', 'NVARCHAR2', 'NCHAR', 'CLOB', 'NCLOB'):
            return 'texte'
        elif 'DATE' in t or 'TIMESTAMP' in t:
            return 'date'
        elif t in ('NUMBER', 'FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE', 'INTEGER', 'DECIMAL'):
            return 'numerique'
        return None

    def _est_fk(self, table: str, colonne: str) -> bool:
        from cox import cursor
        cursor.execute("""
            SELECT COUNT(*)
            FROM USER_CONS_COLUMNS ucc
            JOIN USER_CONSTRAINTS  uc
              ON ucc.CONSTRAINT_NAME = uc.CONSTRAINT_NAME
            WHERE uc.TABLE_NAME      = :1
              AND ucc.COLUMN_NAME    = :2
              AND uc.CONSTRAINT_TYPE = 'R'
        """, [table.upper(), colonne.upper()])
        row = cursor.fetchone()
        return row[0] > 0 if row else False

    def _est_pk(self, table: str, colonne: str) -> bool:
        from cox import cursor
        cursor.execute("""
            SELECT COUNT(*)
            FROM USER_CONS_COLUMNS ucc
            JOIN USER_CONSTRAINTS  uc
              ON ucc.CONSTRAINT_NAME = uc.CONSTRAINT_NAME
            WHERE uc.TABLE_NAME      = :1
              AND ucc.COLUMN_NAME    = :2
              AND uc.CONSTRAINT_TYPE = 'P'
        """, [table.upper(), colonne.upper()])
        row = cursor.fetchone()
        return row[0] > 0 if row else False




def _charger_role(login: str) -> str:

    cur = connection_vault.cursor()
    cur.execute("""
        SELECT ROLE
        FROM VAULT_ACCES
        WHERE LOGIN  = :1
          AND STATUT = 'ACTIF'
          AND (DATE_FIN IS NULL OR DATE_FIN >= SYSDATE)
    """, [login])
    row = cur.fetchone()
    cur.close()

    if not row:
        raise PermissionError(
            f"Utilisateur '{login}' introuvable, inactif ou accès expiré."
        )
    role = row[0]
    logger.info(f"[ACCESS] login='{login}' → rôle='{role}'")
    return role


def _charger_matrice_acces(role: str) -> dict:
    cur = connection_vault.cursor()
    cur.execute("""
        SELECT CRITIQUE, "ÉLEVÉ", "MODÉRÉ", FAIBLE
        FROM ACCESS_MATRIX
        WHERE ROLE = :1
    """, [role.upper()])
    row = cur.fetchone()
    cur.close()

    if not row:
        raise PermissionError(
            f"Aucune entrée dans ACCESS_MATRIX pour le rôle '{role}'."
        )
    matrice = {
        'CRITIQUE': row[0],
        'ÉLEVÉ':    row[1],
        'MODÉRÉ':   row[2],
        'FAIBLE':   row[3],
    }
    logger.info(f"[ACCESS] Matrice pour '{role}' : {matrice}")
    return matrice



def _charger_colonnes_sensibles() -> dict:

    cur = connection_vault.cursor()
    cur.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, NIVEAU
        FROM RGPD_CLASSIFICATION_CACHE
    """)
    rows = cur.fetchall()
    cur.close()

    mapping = {}
    _normaliser = {
        'ELEVE':    'ÉLEVÉ',
        'ELEVÉ':    'ÉLEVÉ',
        'ÉLEVÉ':    'ÉLEVÉ',
        'MODERE':   'MODÉRÉ',
        'MODERÉ':   'MODÉRÉ',
        'MODÉRÉ':   'MODÉRÉ',
        'CRITIQUE': 'CRITIQUE',
        'FAIBLE':   'FAIBLE',
    }
    for table, colonne, niveau in rows:
        niveau_norm = _normaliser.get(niveau.upper(), niveau.upper())
        mapping[f"{table.upper()}.{colonne.upper()}"] = niveau_norm
    return mapping



def _extraire_tables(sql: str) -> list[str]:
    sql_upper = sql.upper()
    tables = []
    for m in re.finditer(r'\bFROM\s+([A-Z_][A-Z0-9_$#]*)', sql_upper):
        tables.append(m.group(1))
    for m in re.finditer(r'\bJOIN\s+([A-Z_][A-Z0-9_$#]*)', sql_upper):
        tables.append(m.group(1))
    return list(set(tables))


class CurseurAnonymisant:

    def __init__(self, curseur_reel, login: str):
        self._cur            = curseur_reel
        self._anon           = AnonymisationUnifiee()
        self._login          = login
        self._role           = _charger_role(login)
        self._matrice        = _charger_matrice_acces(self._role)
        self._cols_sensibles = _charger_colonnes_sensibles()
        self._last_tables    = []
        self._token_cache    = {}
        self._anon._token_cache = self._token_cache

    def __getattr__(self, name):
        return getattr(self._cur, name)

    def execute(self, sql: str, params=None):
        self._last_tables = _extraire_tables(sql)
        logger.info(f"[PROXY] execute → tables détectées : {self._last_tables}")
        if params:
            return self._cur.execute(sql, params)
        return self._cur.execute(sql)

    def executemany(self, sql: str, data):
        return self._cur.executemany(sql, data)

    @property
    def description(self):
        return self._cur.description

    def fetchall(self):
        rows = self._cur.fetchall()
        return self._anonymiser_rows(rows)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return self._anonymiser_rows([row])[0]

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size else self._cur.fetchmany()
        return self._anonymiser_rows(rows)

    def _anonymiser_rows(self, rows: list) -> list:
        if not rows or not self._cur.description:
            return rows

        col_names = [d[0].upper() for d in self._cur.description]
        plan = {}

        for idx, col in enumerate(col_names):
            est_pk = any(self._anon._est_pk(t, col) for t in self._last_tables)
            est_fk = any(self._anon._est_fk(t, col) for t in self._last_tables)
            if est_pk:
                logger.info(f"  SKIP PK → '{col}'")
                continue
            if est_fk:
                logger.info(f"  SKIP FK → '{col}'")
                continue

            niveau = None
            for table in self._last_tables:
                cle = f"{table}.{col}"
                if cle in self._cols_sensibles:
                    niveau = self._cols_sensibles[cle]
                    break

            if niveau is None:
                for cle, niv in self._cols_sensibles.items():
                    if cle.split('.')[1] == col:
                        niveau = niv
                        break

            if niveau is None:
                logger.info(f"  SKIP non-classifié → '{col}'")
                continue

            degre = self._matrice.get(niveau)
            if degre is None:
                logger.warning(
                    f"  Niveau '{niveau}' absent de la matrice pour le rôle "
                    f"'{self._role}' → '{col}' retournée telle quelle"
                )
                continue

            if degre == DEGRE_SANS_ANON or degre not in DEGRES_CONFIG:
                logger.info(
                    f"  SKIP {degre} ({niveau}) → '{col}' retournée telle quelle"
                )
                continue

            plan[idx] = (niveau, degre, DEGRES_CONFIG[degre])
            logger.info(
                f"  ANON '{col}' | sensibilité={niveau} | degré={degre} "
                f"| rôle={self._role}"
            )

        if not plan:
            return rows

        result = []
        for row in rows:
            row = list(row)
            for idx, (niveau, degre, config) in plan.items():
                valeur = row[idx]
                if valeur is None:
                    continue
                row[idx] = self._appliquer_anon(valeur, config)
            result.append(tuple(row))
        return result

    def _appliquer_anon(self, valeur, config: dict):
        if isinstance(valeur, datetime):
            try:
                date_obj = self._anon._to_datetime(valeur)
                mode     = config['date']['generalisation']
                return self._anon._generaliser_date(date_obj, mode)
            except Exception as e:
                logger.warning(f"  Erreur anonymisation date : {e}")
                return valeur

        if isinstance(valeur, (int, float)):
            cfg = config['numerique']
            return self._anon._appliquer_bruit(float(valeur), cfg['sigma_pct'], cfg['bruit'])

        texte = str(valeur)
        if re.match(r'^\d{4}-\d{2}-\d{2}', texte) or re.match(r'^\d{2}/\d{2}/\d{4}', texte):
            try:
                date_obj = self._anon._to_datetime(texte)
                mode     = config['date']['generalisation']
                return self._anon._generaliser_date(date_obj, mode).strftime('%Y-%m-%d')
            except Exception:
                pass

        cfg  = config['texte']
        func = getattr(self._anon, cfg['type_anon'])
        return func(texte)




def get_cursor(login: str) -> CurseurAnonymisant:

    return CurseurAnonymisant(_cursor_base, login)


# ─── Exemple d'utilisation ────────────────────────────────────────────────────

if __name__ == "__main__":

    cursor = get_cursor("strabelsi")

    print("=== Requête simple ===")
    cursor.execute("SELECT NOM, DATE_NAISSANCE FROM CLIENTS")
    rows = cursor.fetchall()
    for r in rows:
        print(r)

    print("\n=== Jointure CLIENTS + COMPTES ===")
    cursor.execute("""
        SELECT C.NOM, CO.SOLDE, CO.TYPE_COMPTE
        FROM CLIENTS C
        JOIN COMPTES CO ON C.ID_CLIENT = CO.ID_CLIENT
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(r)