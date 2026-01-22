import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

host = os.getenv("PG_HOST")
port = os.getenv("PG_PORT", 5432)
db = os.getenv("PG_DB")
user = os.getenv("PG_USER")
pwd = os.getenv("PG_PASSWORD")

dsn = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"
print(f"Connecting with DSN: {dsn.replace(pwd, '***')}...")
engine = create_engine(dsn, connect_args={"connect_timeout": 5})
try:
    with engine.connect() as conn:
        print("Success!")
except Exception as e:
    print(f"Failed: {e}")
