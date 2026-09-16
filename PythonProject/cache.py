from conx import connection_vault
def cache_get(table: str, col: str):
    cursor_vault = connection_vault.cursor()
    cursor_vault.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, SCORE, NIVEAU
        FROM RGPD_CLASSIFICATION_CACHE
        WHERE TABLE_NAME  = :1
        AND   COLUMN_NAME = :2 
    """, [table, col])
    row = cursor_vault.fetchone()
    cursor_vault.close()
    if row:
        return {"table": row[0], "colonne": row[1],
                "score": row[2], "niveau":  row[3]}
    return None
def cache_set(table: str, col: str, score: int, niveau: str):
    cursor = connection_vault.cursor()
    cursor.execute("""
        MERGE INTO RGPD_CLASSIFICATION_CACHE dst
        USING DUAL ON (dst.TABLE_NAME  = :1
                   AND dst.COLUMN_NAME = :2)
        WHEN MATCHED THEN UPDATE SET
            SCORE      = :3,
            NIVEAU     = :4,
            MODIFIE_LE = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN INSERT
            (TABLE_NAME, COLUMN_NAME, SCORE, NIVEAU)
        VALUES (:1, :2, :3, :4)
    """, [table, col, score, niveau])
    connection_vault.commit()
    cursor.close()