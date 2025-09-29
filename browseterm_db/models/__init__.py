"""
Database configuration and SQLAlchemy setup for Browseterm DB
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase


Base: DeclarativeBase = declarative_base()

