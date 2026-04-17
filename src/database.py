"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_engine():
    """Create SQLAlchemy engine."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )


def get_session_factory():
    """Create session factory."""
    engine = get_engine()
    return sessionmaker(bind=engine)


def get_session():
    """Get a new database session (context manager)."""
    Session = get_session_factory()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
