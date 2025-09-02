import os

# sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine


# Postgres Engine Configuration
DB_POOL_SIZE = 10  # size of the connection pool
DB_MAX_OVERFLOW = 20  # maximum number of connections to allow beyond the pool size
DB_POOL_PRE_PING = True  # verify connections before use
DB_POOL_RECYCLE = 3600  # recycle connections every hour

# SQL Alchemy Configuration
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"  # enable SQL logging in development

# Migrations Directory
MIGRATIONS_DIR = "src/migrations"


# Database Configuration
class DBConfig:
    '''
    DBConfig class. Gives you the engine, session, and base.
    '''
    def __init__(self, username: str, password: str, host: str, port: int, database: str) -> None:
        '''
        Initialize the DBConfig class.
        Creates the engine, session, and base.
        Args:
            username: str - The username of the database.
            password: str - The password of the database.
            host: str - The host of the database.
            port: int - The port of the database.
            database: str - The name of the database.
        '''
        self.username: str = username
        self.password: str = password
        self.host: str = host
        self.port: int = port
        self.database: str = database

        # derived attributes
        self.database_url: str = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}".format(
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )
        self.engine: Engine = create_engine(
            self.database_url,
            echo=SQL_ECHO,  # Enable SQL logging in development
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_pre_ping=DB_POOL_PRE_PING,
            pool_recycle=DB_POOL_RECYCLE,
        )
        self.session: Session = sessionmaker(
            autocommit=False,  # do not autocommit
            autoflush=False,  # do not autoflush: Autoflush is used to automatically flush the session when changes are made.
            bind=self.engine,
        )

    def get_db_url(self) -> str:
        '''
        Get the database URL.
        '''
        return self.database_url

    def get_db_session(self) -> Session:
        '''
        Get a database session.
        '''
        return self.session()
