from cryptography.fernet import Fernet
from datetime import datetime
import logging
from conx import connection_vault , cursor_vault

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

KEY_NAME = "CLE_RGPD"

def load_or_create_key():
    cursor_vault.execute("""
        SELECT CLE_CHIFFREE
        FROM RGPD_KEYS
        WHERE NOM_KEY = :1 AND STATUT = 'ACTIVE'
    """, [KEY_NAME])

    row = cursor_vault.fetchone()
    if row:
        key = row[0]
        if isinstance(key, str):
            key = key.encode('utf-8')
        logger.info("Clé existante utilisée depuis la base")
        return key

    key = Fernet.generate_key()  # bytes
    logger.info("Nouvelle clé générée")

    cursor_vault.execute("""
        INSERT INTO RGPD_KEYS (NOM_KEY, CLE_CHIFFREE, DATE_CREATION, STATUT)
        VALUES (:1, :2, :3, 'ACTIVE')
    """, [KEY_NAME, key.decode('utf-8'), datetime.now()])

    connection_vault.commit()
    logger.info("Clé sauvegardée dans RGPD_KEYS")
    return key



if __name__ == "__main__":
    CLE = load_or_create_key()
