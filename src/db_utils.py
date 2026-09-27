"""Database utilities for the Olist project.

Wraps SQLAlchemy so that notebooks and ETL code don't touch connection
strings or driver details. Targets PostgreSQL only.
"""
from pathlib import Path
from typing import Union

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import DATABASE_URL, SQL_DIR


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def get_engine(echo: bool = False) -> Engine:
    """Return a SQLAlchemy engine connected to PostgreSQL.

    Parameters
    ----------
    echo : bool
        If True, SQLAlchemy logs every SQL statement.
    """
    return create_engine(DATABASE_URL, echo=echo, future=True)


# ---------------------------------------------------------------------------
# SQL file execution
# ---------------------------------------------------------------------------
def run_sql_file(engine: Engine, sql_path: Union[str, Path]) -> None:
    """Execute an entire .sql file, handling multiple statements."""
    script = Path(sql_path).read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(script)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def query_df(engine: Engine, sql: str,
             params: dict | None = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    return pd.read_sql(text(sql), engine, params=params or {})


def execute(engine: Engine, sql: str, params: dict | None = None) -> None:
    """Execute a non-SELECT statement."""
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def table_exists(engine: Engine, table_name: str) -> bool:
    """Return True if `table_name` exists in the public schema."""
    sql = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :t
        );
    """
    return bool(query_df(engine, sql, {"t": table_name}).iloc[0, 0])


# ---------------------------------------------------------------------------
# Bulk loading
# ---------------------------------------------------------------------------
def bulk_copy_dataframe(engine: Engine, df: pd.DataFrame, table: str) -> None:
    """Load a DataFrame into PostgreSQL using the COPY protocol."""
    from io import StringIO

    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.copy_expert(
            f"COPY {table} FROM STDIN WITH (FORMAT CSV, NULL '\\N')",
            buffer,
        )
        raw.commit()
        cursor.close()
    finally:
        raw.close()


# ---------------------------------------------------------------------------
# Batch query runner
# ---------------------------------------------------------------------------
def run_all_analysis_queries(engine: Engine) -> dict[str, pd.DataFrame]:
    """Run each sql/0[2-3]_*.sql file, returning results keyed by filename."""
    results: dict[str, pd.DataFrame] = {}
    for sql_file in sorted(SQL_DIR.glob("0[2-3]_*.sql")):
        try:
            results[sql_file.name] = query_df(engine, sql_file.read_text())
            print(f"OK  {sql_file.name}: {len(results[sql_file.name])} rows")
        except Exception as exc:
            print(f"ERR {sql_file.name}: {exc}")
    return results