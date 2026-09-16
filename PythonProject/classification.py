import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"]  = "1"

from cox import connection
from rag import retrieve_context, _init_rag
from cache import cache_get, cache_set
import requests
import json
from conx import connection_vault, cursor_vault

colonnes_critique = []
colonnes_eleve    = []
colonnes_moyenne  = []
colonnes_faible   = []

API_URL    = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral:7b"

QUESTIONS_RGPD = [
    {"id": "identity",
     "texte": "Cette colonne permet-elle d'identifier directement un client (nom, prénom, CIN, email, téléphone) ?",
     "article": "Art. 4",
     "poids": 45},
    {"id": "financial",
     "texte": "Cette colonne contient-elle des données financières sensibles (IBAN, numéro de carte, solde, montant, taux) ?",
     "article": "Art. 6",
     "poids": 40},
    {"id": "sensitive",
     "texte": "Cette colonne contient-elle des données de sécurité bancaire (code PIN, mot de passe, token, clé secrète) ?",
     "article": "Art. 32",
     "poids": 40},
    {"id": "location",
     "texte": "Cette colonne contient-elle une adresse postale ou une localisation précise du client ?",
     "article": "Art. 6",
     "poids": 20},
    {"id": "profiling",
     "texte": "Cette colonne est-elle utilisée pour scorer, profiler ou prendre des décisions automatiques sur un client ?",
     "article": "Art. 22",
     "poids": 20},
    {"id": "third_party",
     "texte": "Cette colonne est-elle transmise à des organismes externes (assurance, fisc, banques partenaires) ?",
     "article": "Art. 44",
     "poids": 10},
    {"id": "tracking",
     "texte": "Cette colonne permet-elle de retracer le comportement financier d'un client (historique transactions, habitudes) ?",
     "article": "Art. 6",
     "poids": 15},
]


def score_vers_niveau(score: int) -> str:
    if score >= 70: return "CRITIQUE"
    if score >= 40: return "ÉLEVÉ"
    if score >= 15: return "MODÉRÉ"
    return "FAIBLE"


def analyser_colonne(col: str, table: str, sample_values: list, context: str) -> dict:
    questions_text = "\n".join([
        f'{i+1}. [{q["article"]}] {q["texte"]}'
        for i, q in enumerate(QUESTIONS_RGPD)
    ])

    prompt = f"""Tu es un expert RGPD spécialisé en données bancaires.
Analyse UNIQUEMENT cette colonne, pas la table entière.

Table            : {table}
Colonne          : {col}
Valeurs exemples : {sample_values}

Contexte RGPD :
{context}

Réponds à chaque question par OUI ou NON.

QUESTIONS :
{questions_text}

Réponds UNIQUEMENT avec ce JSON valide (sans markdown, sans backticks) :
{{
  "reponses": {{
    "identity":    "OUI|NON",
    "financial":   "OUI|NON",
    "sensitive":   "OUI|NON",
    "location":    "OUI|NON",
    "profiling":   "OUI|NON",
    "third_party": "OUI|NON",
    "tracking":    "OUI|NON"
  }}
}}"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p":       0.1,
            "top_k":       10,
            "num_predict": 300,
        }
    }

    r = requests.post(API_URL, json=payload, timeout=120)
    r.raise_for_status()
    raw = r.json()["response"].strip()

    try:
        clean    = raw.replace("```json", "").replace("```", "").strip()
        reponses = json.loads(clean).get("reponses", {})
    except json.JSONDecodeError:
        reponses = {q["id"]: "NON" for q in QUESTIONS_RGPD}

    score  = sum(
        q["poids"]
        for q in QUESTIONS_RGPD
        if reponses.get(q["id"], "NON").upper() == "OUI"
    )
    score  = min(score, 100)
    niveau = score_vers_niveau(score)

    return {"table": table, "colonne": col, "score": score, "niveau": niveau}


def cache_check(col: str, table: str, sample_values: list, context: str) -> dict:
    cached = cache_get(table, col)
    if cached:
        print(f"  {col}: {cached['score']}/100 → {cached['niveau']} ✓ (cache)")
        return cached

    result = analyser_colonne(col, table, sample_values, context)
    cache_set(table, col, result["score"], result["niveau"])
    print(f"  {col}: {result['score']}/100 → {result['niveau']}")
    return result


def classification_colonnes():
    print("Initialisation RAG...")
    _init_rag()
    print("RAG prêt ✓\n")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM USER_TABLES
        ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        print(f"\n=== Table: {table} ===")

        cursor.execute("""
            SELECT COLUMN_NAME
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = :1
            ORDER BY COLUMN_ID
        """, [table])
        columns = [row[0] for row in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM {table} WHERE ROWNUM <= 10")
        rows = cursor.fetchall()

        for idx, col in enumerate(columns):
            context       = retrieve_context(col, table=table)
            sample_values = [str(r[idx]) for r in rows if r[idx] is not None][:5]

            try:
                result = cache_check(col, table, sample_values, context)
                score  = result["score"]
                niveau = result["niveau"]

                entry = {"table": table, "colonne": col, "score": score}
                if   niveau == "CRITIQUE": colonnes_critique.append(entry)
                elif niveau == "ÉLEVÉ":    colonnes_eleve.append(entry)
                elif niveau == "MODÉRÉ":   colonnes_moyenne.append(entry)
                else:                      colonnes_faible.append(entry)

            except Exception as e:
                print(f"   Erreur pour {col} : {e}")

    cursor.close()


if __name__ == "__main__":
    classification_colonnes()

    print("\n" + "="*50)
    print(" RÉSUMÉ CLASSIFICATION RGPD BANCAIRE")
    print("="*50)

    print(f"\n CRITIQUE : {len(colonnes_critique)} colonne(s)")
    for c in colonnes_critique:
        print(f"   → {c['table']}.{c['colonne']} (score: {c['score']})")

    print(f"\n  ÉLEVÉ    : {len(colonnes_eleve)} colonne(s)")
    for c in colonnes_eleve:
        print(f"   → {c['table']}.{c['colonne']} (score: {c['score']})")

    print(f"\n MODÉRÉ   : {len(colonnes_moyenne)} colonne(s)")
    for c in colonnes_moyenne:
        print(f"   → {c['table']}.{c['colonne']} (score: {c['score']})")

    print(f"\n  FAIBLE   : {len(colonnes_faible)} colonne(s)")
    for c in colonnes_faible:
        print(f"   → {c['table']}.{c['colonne']} (score: {c['score']})")