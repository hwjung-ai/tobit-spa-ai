import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("PG_HOST")
port = os.getenv("PG_PORT", 5432)
db = os.getenv("PG_DB")
user = os.getenv("PG_USER")
pwd = os.getenv("PG_PASSWORD")

conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd} connect_timeout=5"
print(f"Connecting to {host}...")
try:
    with psycopg.connect(conn_str) as conn:
        print("Success!")
except Exception as e:
    print(f"Failed: {e}")
