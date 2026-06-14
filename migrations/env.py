"""
migrations/env.py  (updated)
Wired to Flask-SQLAlchemy so `flask db migrate` auto-detects model changes.
"""

from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ── Make sure the project root is on sys.path ─────────────────────────────────
# Adjust the depth if your migrations/ folder is nested differently.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import every model so Alembic sees all tables ─────────────────────────────
# Import Flask app first so the db object is fully initialised before we
# access db.metadata.
from app import create_app                      # noqa: E402
from extensions import db                       # noqa: E402

# Import all models — Alembic needs them registered on db.metadata
from models.user   import User                  # noqa: E402, F401
from models.vote   import Vote, FlaggedActivity # noqa: E402, F401
from models.election import Election            # noqa: E402, F401
from models.audit  import AuditLog, SystemConfiguration  # noqa: E402, F401

# Create a minimal app context so db.metadata is populated
_app = create_app()
with _app.app_context():
    target_metadata = db.metadata


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        # Render column-level defaults so generated SQL is complete
        render_as_batch=False,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,        # detect column-type changes
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()