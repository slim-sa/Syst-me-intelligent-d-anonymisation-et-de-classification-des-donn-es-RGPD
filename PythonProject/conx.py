import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

oracledb.init_oracle_client(
    lib_dir=os.getenv("ORACLE_LIB_DIR")
)

connection_vault = oracledb.connect(
    user=os.getenv("VAULT_DB_USER"),
    password=os.getenv("VAULT_DB_PASSWORD"),
    dsn=os.getenv("VAULT_DB_DSN")
)

print("Connecté RGPD_vault!")

cursor_vault = connection_vault.cursor()