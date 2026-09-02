"""Direct PostgreSQL schema and session helpers for all durable data."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

JSONField = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("dossier_id", "section_path", "stem", name="uq_document"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    section_path: Mapped[str] = mapped_column(Text, nullable=False)
    stem: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(Text, default="")
    ctd_path: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    filename: Mapped[str] = mapped_column(Text, default="")
    original_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    pages: Mapped[list[dict[str, Any]]] = mapped_column(JSONField, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONField, default=dict)
    generated_markdown: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    feedback_history: Mapped[list[dict[str, Any]]] = mapped_column(JSONField, default=list)
    translations: Mapped[dict[str, str]] = mapped_column(JSONField, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class FeatureRecord(Base):
    __tablename__ = "feature_records"
    __table_args__ = (UniqueConstraint("scope", "kind", "record_key", name="uq_feature_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    record_key: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
_pool_class = StaticPool if settings.DATABASE_URL in {"sqlite://", "sqlite:///:memory:"} else None
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, poolclass=_pool_class, future=True, pool_pre_ping=not settings.DATABASE_URL.startswith("sqlite"))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

@contextmanager
def session_scope():
    """Transactional scope: commit on clean exit, rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
