
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

db_setting_names = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
db_settings = {name: os.getenv(name) for name in db_setting_names}
configured_db_settings = {
    name: value for name, value in db_settings.items() if value is not None and value.strip()
}

if configured_db_settings:
    missing_settings = [
        name for name in db_setting_names if name not in configured_db_settings
    ]
    if missing_settings:
        raise RuntimeError(
            "Incomplete MySQL configuration; missing: " + ", ".join(missing_settings)
        )

    try:
        db_port = int(db_settings["DB_PORT"])
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be a valid port number.") from exc

    MYSQL_DATABASE_URL = URL.create(
        "mysql+pymysql",
        username=db_settings["DB_USER"],
        password=db_settings["DB_PASSWORD"],
        host=db_settings["DB_HOST"],
        port=db_port,
        database=db_settings["DB_NAME"],
        query={"charset": "utf8mb4"},
    )
    engine_connect_args = {"connect_timeout": 10}
    if db_settings["DB_HOST"].lower() not in {"localhost", "127.0.0.1", "::1"}:
        engine_connect_args.update(
    ssl_verify_cert=True,
    ssl_verify_identity=True
     )
else:
    mysql_url = os.getenv("MYSQL_URL")
    if not mysql_url:
        raise RuntimeError(
            "Configure DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME, "
            "or provide MYSQL_URL."
        )

    MYSQL_DATABASE_URL = make_url(mysql_url)
    if MYSQL_DATABASE_URL.drivername != "mysql+pymysql":
        raise RuntimeError("MYSQL_URL must use the mysql+pymysql SQLAlchemy driver.")
    engine_connect_args = {"connect_timeout": 10}


# SQLAlchemy base class
class Base(DeclarativeBase):
    pass


engine = create_engine(
    MYSQL_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    connect_args=engine_connect_args,
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
