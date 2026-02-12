#!/usr/bin/env python3
import sys, os
os.chdir('/home/spa/tobit-spa-ai/apps/api')
sys.path.insert(0, '/home/spa/tobit-spa-ai/apps/api')

from dotenv import load_dotenv
load_dotenv('/home/spa/tobit-spa-ai/apps/api/.env')

from sqlalchemy import create_engine, text

db_url = f'postgresql://{os.getenv("PG_USER")}:{os.getenv("PG_PASSWORD")}@{os.getenv("PG_HOST")}:{os.getenv("PG_PORT")}/{os.getenv("PG_DB")}'

engine = create_engine(db_url)

with engine.connect() as conn:
    # Check if table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'tb_metric_timeseries'
        )
    """)).first()
    exists = result[0] if result else False
    print(f'tb_metric_timeseries exists: {exists}')

    # If not, create it
    if not exists:
        print('Creating table...')
        conn.execute(text("""
            CREATE TABLE tb_metric_timeseries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id TEXT NOT NULL,
                service TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                value FLOAT NOT NULL,
                unit TEXT,
                tags JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        conn.commit()

        # Create indexes
        conn.execute(text("""
            CREATE INDEX idx_metric_timeseries_service_metric_time
            ON tb_metric_timeseries (service, metric_name, timestamp)
        """))
        conn.execute(text("""
            CREATE INDEX idx_metric_timeseries_tenant_time
            ON tb_metric_timeseries (tenant_id, timestamp)
        """))
        conn.commit()

        print('Table created successfully!')
    else:
        print('Table already exists')
