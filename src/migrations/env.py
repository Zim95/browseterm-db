from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from src.models.all_models import Base  # Your models metadata

# Alembic Config
config = context.config
fileConfig(config.config_file_name)

# Point to models’ metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    '''
    Run the migrations offline.
    The configs are set from migrator.py.
    '''
    # Get the URL that was set by the Migrator class
    url = config.get_main_option("sqlalchemy.url")
    
    if not url:
        # Fallback: this shouldn't happen when using Migrator, but just in case
        raise ValueError("No database URL configured. Make sure to use the Migrator class.")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    '''
    Run the migrations online.
    The configs are set from migrator.py.
    '''
    # Get the URL that was set by the Migrator class
    url = config.get_main_option("sqlalchemy.url")
    
    if url:
        # Use the URL directly if it was set by Migrator
        from sqlalchemy import create_engine
        connectable = create_engine(url, poolclass=pool.NullPool)
    else:
        # Fallback to reading from alembic.ini
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
