import os
import oracledb
from dotenv import load_dotenv


load_dotenv()


oracledb.init_oracle_client(
    lib_dir=os.getenv("ORACLE_LIB_DIR")
)


connection = oracledb.connect(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dsn=os.getenv("DB_DSN")
)

print("Connecté RGPD!")

cursor = connection.cursor()