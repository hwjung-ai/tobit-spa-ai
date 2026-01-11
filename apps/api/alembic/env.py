from __future__ import annotations

from logging.config import fileConfig

import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.config import get_settings
from models.chat import ChatMessage, ChatThread
from models.document import Document, DocumentChunk
from app.modules.api_manager.models import ApiExecLog, TbApiDef
from app.modules.ui_creator.models import TbUiDef
from sqlmodel import SQLModel

config = context.config

if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except KeyError:
        pass

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
