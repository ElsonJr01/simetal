"""Engine e sessão SQLAlchemy. Em serverless (Vercel) usa NullPool com Postgres."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import ClauseElement, create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.config import get_settings

log = logging.getLogger("simetal.db")


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        eng = create_engine(url, **kwargs)

        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite só respeita chaves estrangeiras com este PRAGMA
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return eng
    return create_engine(url, poolclass=NullPool, pool_pre_ping=True)


engine = make_engine(get_settings().sqlalchemy_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def sync_missing_columns(eng: Engine) -> list[str]:
    """Adiciona colunas novas a tabelas já existentes (ALTER TABLE ... ADD COLUMN).

    Rede de segurança para desenvolvimento e testes, quando um banco antigo é reaproveitado.
    Em produção, use Alembic. Só trata colunas simples (nulas ou com valor padrão).
    """
    added: list[str] = []
    insp = inspect(eng)
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col.type.compile(dialect=eng.dialect)}'
                if col.server_default is not None:
                    arg = col.server_default.arg
                    ddl += " DEFAULT " + (str(arg.compile(dialect=eng.dialect)) if isinstance(arg, ClauseElement) else str(arg))
                elif not col.nullable:
                    log.warning("Coluna %s.%s é obrigatória e sem padrão; rode as migrações.", table.name, col.name)
                    continue
                conn.execute(text(ddl))
                added.append(f"{table.name}.{col.name}")
    if added:
        log.warning("Colunas adicionadas automaticamente: %s", ", ".join(added))
    return added


def init_db() -> None:
    """Cria tabelas e colunas novas (desenvolvimento/testes). Em produção use Alembic."""
    from app import models  # noqa: F401  (registra os modelos)

    Base.metadata.create_all(engine)
    sync_missing_columns(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
