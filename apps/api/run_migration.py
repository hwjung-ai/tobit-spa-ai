#!/usr/bin/env python3
"""Run alembic migration"""
import os
import sys

# Change to apps/api directory
os.chdir('/home/spa/tobit-spa-ai/apps/api')
sys.path.insert(0, '/home/spa/tobit-spa-ai/apps/api')

# Set up environment
from dotenv import load_dotenv
load_dotenv('/home/spa/tobit-spa-ai/apps/api/.env')

# Import and run alembic
from alembic.config import Config
from alembic import command

alembic_cfg = Config('/home/spa/tobit-spa-ai/apps/api/alembic.ini')
alembic_cfg.set_main_option('sqlalchemy.url', os.getenv(
    'DATABASE_URL',
    'postgresql://spa:WeMB1!@115.21.12.151:5432/spadb'
))

# Run upgrade
try:
    command.upgrade(alembic_cfg, 'head')
    print('Migration completed successfully')
except Exception as e:
    print(f'Migration failed: {e}')
    sys.exit(1)
