
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

mysql_url = os.getenv("MYSQL_URL")
if not mysql_url:
    raise RuntimeError("MYSQL_URL must be configured for the MySQL database.")

MYSQL_DATABASE_URL = make_url(mysql_url)
if MYSQL_DATABASE_URL.drivername != "mysql+pymysql":
    raise RuntimeError("MYSQL_URL must use the mysql+pymysql SQLAlchemy driver.")


# SQLAlchemy base class
class Base(DeclarativeBase):
    pass


engine = create_engine(
    MYSQL_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# Dependency for API routes
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
