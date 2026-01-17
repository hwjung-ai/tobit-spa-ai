from sqlmodel import Session, create_engine, select, func
from app.modules.inspector.models import TbExecutionTrace
import os
from dotenv import load_dotenv

load_dotenv()
dsn = f"postgresql+psycopg://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DB')}"
engine = create_engine(dsn)

with Session(engine) as session:
    total_stmt = select(func.count()).select_from(TbExecutionTrace)
    result = session.exec(total_stmt)
    print(f"Result type: {type(result)}")
    print(f"Result dir: {[m for m in dir(result) if not m.startswith('_')]}")
    try:
        val = result.one()
        print(f"one(): {val}")
    except Exception as e:
        print(f"one() failed: {e}")
