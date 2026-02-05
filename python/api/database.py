"""
Database Connection Module

Provides PostgreSQL database connection and session management.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('POSTGRES_USER', 'accounting')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'accounting_automation')}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session for FastAPI dependency injection.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Get database session as context manager.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute raw SQL query and return results as dictionaries.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        List of result dictionaries
    """
    from sqlalchemy import text

    with get_db_context() as db:
        result = db.execute(text(query), params or {})

        # For SELECT queries, return results
        if result.returns_rows:
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

        # For INSERT/UPDATE/DELETE, commit and return empty
        db.commit()
        return []


def execute_insert(
    table: str,
    data: dict,
    returning: str = "id",
) -> dict | None:
    """Execute INSERT and return the inserted row.

    Args:
        table: Table name
        data: Column-value dictionary
        returning: Column to return (default: id)

    Returns:
        Inserted row or None
    """
    columns = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING {returning}"

    results = execute_query(query, data)
    return results[0] if results else None
