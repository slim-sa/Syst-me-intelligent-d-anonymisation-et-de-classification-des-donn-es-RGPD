import oracledb


oracledb.init_oracle_client(lib_dir=r"C:\oraclexe\app\oracle\product\11.2.0\server\bin")

connection = oracledb.connect(
    user="user1",
    password="123",
    dsn="localhost:1521/xe"
)
print("Connecté RGPD!")
cursor = connection.cursor()
