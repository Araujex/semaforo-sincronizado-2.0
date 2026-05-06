from dotenv import load_dotenv
import mysql.connector
import os

load_dotenv()

print("Variáveis carregadas:")
print(f"  HOST:     {os.getenv('MYSQL_HOST')}")
print(f"  PORT:     {os.getenv('MYSQL_PORT')}")
print(f"  DATABASE: {os.getenv('MYSQL_DATABASE')}")
print(f"  USER:     {os.getenv('MYSQL_USER')}")
print(f"  PASSWORD: {'***' if os.getenv('MYSQL_PASSWORD') else 'VAZIO'}")

print("\nTentando conectar...")
try:
    conn = mysql.connector.connect(
        host                = os.getenv("MYSQL_HOST"),
        port                = int(os.getenv("MYSQL_PORT")),
        database            = os.getenv("MYSQL_DATABASE"),
        user                = os.getenv("MYSQL_USER"),
        password            = os.getenv("MYSQL_PASSWORD"),
        ssl_disabled        = False,
        ssl_verify_cert     = False,
        ssl_verify_identity = False,
        connection_timeout  = 30,
        use_pure            = True,
    )
    print("✔ Conexão OK!")
    conn.close()
except Exception as e:
    print(f"✗ Erro: {e}")