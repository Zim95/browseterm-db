import os

# Postgres Engine Configuration
DB_POOL_SIZE = 10  # size of the connection pool
DB_MAX_OVERFLOW = 20  # maximum number of connections to allow beyond the pool size
DB_POOL_PRE_PING = True  # verify connections before use
DB_POOL_RECYCLE = 3600  # recycle connections every hour

# SQL Alchemy Configuration
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"  # enable SQL logging in development
