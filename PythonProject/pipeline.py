# pipeline.py
from cox import cursor
from conx import cursor_vault
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


COLONNES_ANALYSTE = ["NOM", "PRENOM", "EMAIL"]

# ── Étape 1 : charger la vue Oracle selon le rôle ─────────────────────────
def charger_vue(id_user: str, role: str):
    cursor.execute("BEGIN DBMS_SESSION.SET_IDENTIFIER(:1); END;", [str(id_user)])

    if role.lower() == "conseiller":
        vue = "V_CONSEILLER_DASHBOARD"
    elif role.lower() == "analyste":
        vue = "V_ANALYSE_CLIENTS"
    else:
        raise ValueError(f"Rôle inconnu : {role}")

    cursor.execute(f"SELECT * FROM {vue}")
    colonnes = [desc[0] for desc in cursor.description]
    resultats = cursor.fetchall()
    return colonnes, resultats

# ── Étape 2 : désanonymiser selon le rôle ─────────────────────────────────
def desanonymiser_selon_role(anon, role: str, table: str,
                              colonnes: list, resultats: list) -> dict:
    pk_col = colonnes[0]
    role   = role.lower()

    if role == "conseiller":
        # Toutes les colonnes, ligne par ligne
        index = {}
        for row in resultats:
            pk_val  = str(row[0])
            pk_dict = {pk_col: pk_val}
            deanon  = anon.desanonymiser_ligne(table, pk_dict)
            pk_key  = f"{pk_col}={pk_val}"
            index[pk_key] = {k: v for k, v in deanon.items() if k != "pk"}
        return index

    elif role == "analyste":
        # Seulement les colonnes autorisées, toutes les lignes
        lignes = anon.desanonymiser_tableau(table, colonnes=COLONNES_ANALYSTE)
        index  = {}
        for item in lignes:
            pk_key = "|".join(f"{k}={v}" for k, v in item["pk"].items())
            index[pk_key] = item.get("colonnes", {})
        return index

    raise ValueError(f"Rôle inconnu : {role}")

# ── Étape 3 : fusionner et formater pour React ─────────────────────────────
def formater_payload(role: str, colonnes: list, resultats: list,
                     index_deanon: dict) -> dict:
    pk_col = colonnes[0]
    colonnes_visibles = set(COLONNES_ANALYSTE) if role.lower() == "analyste" else None

    columns_react = [
        {"key": col.lower(), "label": col.replace("_", " ").title()}
        for col in colonnes
    ]

    rows = []
    for row in resultats:
        row_dict = dict(zip(colonnes, row))
        pk_val   = str(row_dict[pk_col])
        pk_key   = f"{pk_col}={pk_val}"
        deanon   = index_deanon.get(pk_key, {})

        merged = {}
        for col in colonnes:
            col_lower = col.lower()

            if col in deanon:
                # Valeur déchiffrée disponible
                val = deanon[col]["originale"]
                merged[col_lower] = val.strftime("%d/%m/%Y") if isinstance(val, datetime) else val

            elif colonnes_visibles and col not in colonnes_visibles:
                # Analyste — colonne non autorisée → masquée
                merged[col_lower] = "***"

            else:
                # Valeur Oracle brute (non stockée dans vault)
                val = row_dict[col]
                merged[col_lower] = val.strftime("%d/%m/%Y") if isinstance(val, datetime) else val

        rows.append(merged)

    return {"columns": columns_react, "rows": rows}

# ── Point d'entrée principal ───────────────────────────────────────────────
def construire_payload(anon, id_user: str, role: str,
                       table: str, employee_info: dict) -> dict:
    colonnes, resultats = charger_vue(id_user, role)

    if not resultats:
        return {"columns": [], "rows": [], "employee": employee_info}

    index   = desanonymiser_selon_role(anon, role, table, colonnes, resultats)
    payload = formater_payload(role, colonnes, resultats, index)
    payload["employee"] = employee_info
    return payload