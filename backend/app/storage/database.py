from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


REPO_ROOT = Path(__file__).resolve().parents[3]


def create_database_engine(database_url: str) -> Engine:
    resolved_url = _resolve_sqlite_url(database_url)
    if resolved_url.startswith("sqlite:///"):
        db_path = resolved_url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(resolved_url, connect_args=connect_args)


def _resolve_sqlite_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url
    db_path = database_url.removeprefix("sqlite:///")
    if not db_path or db_path == ":memory:":
        return database_url
    path = Path(db_path)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return f"sqlite:///{path.as_posix()}"


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    from app.storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
