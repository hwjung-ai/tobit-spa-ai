import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("PG_HOST")
port = os.getenv("PG_PORT", 5432)
db = os.getenv("PG_DB")
user = os.getenv("PG_USER")
pwd = os.getenv("PG_PASSWORD")

conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tb_execution_trace'")
            columns = [row[0] for row in cur.fetchall()]
            print(f"Columns in tb_execution_trace: {columns}")
            
            cur.execute("SELECT version_num FROM alembic_version")
            print(f"Alembic version in DB: {cur.fetchone()}")
except Exception as e:
    print(f"Error: {e}")
