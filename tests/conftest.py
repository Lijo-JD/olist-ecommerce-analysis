"""Shared pytest fixtures for the Olist test suite.

Tests run against a real PostgreSQL database (`olist_test`) rather than
SQLite, so the schema, DDL, and Postgres-specific SQL are exercised
against the same engine used in production.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import TEST_DATABASE_URL, SQL_DIR, DB_TEST_NAME
from src.db_utils import run_sql_file


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Session-scoped PostgreSQL engine pointing at the test database."""
    eng = create_engine(TEST_DATABASE_URL, future=True)

    try:
        with eng.connect() as conn:
            conn.exec_driver_sql("SELECT 1;")
    except Exception as exc:
        pytest.exit(
            f"\nCannot connect to test database at {TEST_DATABASE_URL}.\n"
            f"Error: {exc}\n\n"
            f"Fix:\n"
            f"  1. Confirm PostgreSQL is running.\n"
            f"  2. Create the test database:\n"
            f"       CREATE DATABASE {DB_TEST_NAME};\n"
            f"  3. Confirm .env has DB_TEST_NAME={DB_TEST_NAME}.\n",
            returncode=1,
        )

    run_sql_file(eng, SQL_DIR / "01_schema.sql")
    return eng