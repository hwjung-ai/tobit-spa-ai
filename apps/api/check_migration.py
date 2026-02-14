#!/usr/bin/env python3
"""Check current migration status"""
import sys

sys.path.insert(0, "/home/spa/tobit-spa-ai/apps/api")

from core.db import engine
from sqlmodel import Session, text

try:
    with Session(engine) as session:
        result = session.exec(text('SELECT version_num FROM alembic_version')).first()
        if result:
            print(f'Current migration: {result[0]}')
        else:
            print('No migrations applied yet')
except Exception as e:
    print(f'Error: {e}')
