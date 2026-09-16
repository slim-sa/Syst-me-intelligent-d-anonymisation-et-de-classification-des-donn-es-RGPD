import oracledb


oracledb.init_oracle_client(lib_dir=r"C:\oraclexe\app\oracle\product\11.2.0\server\bin")

connection_vault = oracledb.connect(
    user="RGPD_vault",
    password="vault123",
    dsn="localhost:1521/xe"
)
print("Connecté RGPD_vault!")
cursor_vault = connection_vault.cursor()