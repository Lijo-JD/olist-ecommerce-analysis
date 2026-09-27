"""Extract → Transform → Load pipeline for the Olist dataset.

Design goals:
- Deterministic and idempotent: running twice produces the same DB state.
- Testable: transform() is a pure function with no disk side effects, so
  tests can call it freely without corrupting data/processed/.
- Postgres-first: bulk load via COPY with to_sql as a graceful fallback.
"""
import sys

import pandas as pd
from sqlalchemy.engine import Engine

from .config import (
    CSV_FILES,
    DATE_COLUMNS,
    DATA_PROCESSED,
    DATA_RAW,
    INTEGER_COLUMNS,
    SQL_DIR,
    TABLE_MAPPING,
)
from .db_utils import (
    bulk_copy_dataframe,
    get_engine,
    run_sql_file,
    table_exists,
)


# ---------------------------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------------------------
def extract() -> dict[str, pd.DataFrame]:
    """Read every expected CSV from `data/raw/` into a DataFrame.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys are the logical table names (`customers`, `orders`, ...).
        Missing files are skipped with a warning, not a crash, so partial
        runs are possible.
    """
    dataframes: dict[str, pd.DataFrame] = {}
    for name, filename in CSV_FILES.items():
        path = DATA_RAW / filename
        if not path.exists():
            print(f"WARN  missing file: {path}")
            continue
        df = pd.read_csv(path)
        dataframes[name] = df
        print(f"OK    {name}: {df.shape[0]:,} rows x {df.shape[1]} cols")
    return dataframes


# ---------------------------------------------------------------------------
# TRANSFORM
# ---------------------------------------------------------------------------
def transform(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Clean and normalize each DataFrame.

    This function is *pure*: it takes DataFrames in, returns DataFrames out,
    and touches nothing on disk. That means tests can call it with small
    synthetic inputs without overwriting the real Parquet files in
    data/processed/.

    Persisting to Parquet happens in `persist_parquet()` — called only by
    `run_etl()` — not here.

    Order of operations matters:
    1. Parse datetimes.
    2. Cast integer columns (handles source floats like "40.0").
    3. Strip whitespace and normalize nulls in string columns.
    4. Table-specific dedupe (reviews).
    """
    cleaned: dict[str, pd.DataFrame] = {}

    for name, df in raw.items():
        df = df.copy()

        # 1. Datetime parsing
        for col in DATE_COLUMNS.get(name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # 2. Integer casting.
        #    Source CSVs sometimes store integers as floats ("40.0"). We cast
        #    via nullable Int64 so genuine nulls survive.
        for col in INTEGER_COLUMNS.get(name, []):
            if col in df.columns:
                df[col] = (
                    pd.to_numeric(df[col], errors="coerce")
                      .astype("Int64")
                )

        # 3. String cleanup.
        #    `include=["object", "str"]` is forward-compatible with pandas 3.x,
        #    where the two dtypes are distinct.
        string_cols = df.select_dtypes(include=["object", "str"]).columns
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

        # 4. Reviews dedupe — keep the latest answer per review_id.
        if name == "reviews" and "review_id" in df.columns:
            df["review_answer_timestamp"] = pd.to_datetime(
                df["review_answer_timestamp"], errors="coerce"
            )
            df = (
                df.sort_values("review_answer_timestamp")
                .drop_duplicates(subset=["review_id"], keep="last")
                .reset_index(drop=True)
            )

        cleaned[name] = df

    return cleaned


# ---------------------------------------------------------------------------
# PERSIST (Parquet)
# ---------------------------------------------------------------------------
def persist_parquet(tables: dict[str, pd.DataFrame]) -> None:
    """Write cleaned tables to data/processed/ as Parquet.

    Kept separate from `transform()` so that:
    - Tests can call `transform()` with tiny synthetic DataFrames without
      overwriting the real Parquet files.
    - The write step is explicit and traceable in `run_etl()`.

    Parquet preserves dtypes (datetime64, Int64, categorical) that CSV
    would lose. It's also 5–10x smaller and much faster to read back.
    """
    for name, df in tables.items():
        try:
            df.to_parquet(DATA_PROCESSED / f"{name}.parquet", index=False)
        except Exception as exc:
            print(f"WARN  could not write {name}.parquet: {exc}")


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------
def load(
    tables: dict[str, pd.DataFrame],
    engine: Engine,
    rebuild_schema: bool = True,
) -> None:
    """Load DataFrames into PostgreSQL.

    Uses COPY for speed (10–100x faster than INSERT) with `to_sql` as a
    graceful fallback if COPY fails on a type issue.
    """
    if rebuild_schema:
        print("Rebuilding schema ...")
        run_sql_file(engine, SQL_DIR / "01_schema.sql")
        print("Schema ready.")

    for name, df in tables.items():
        table = TABLE_MAPPING[name]
        print(f"LOAD  {name} -> {table} ({len(df):,} rows)")

        try:
            bulk_copy_dataframe(engine, df, table)
            print(f"{table} done via COPY")
        except Exception as exc:
            print(f"{table} COPY failed ({exc}); falling back to to_sql")
            df.to_sql(
                table, engine,
                if_exists="append", index=False,
                method="multi", chunksize=1000,
            )
            print(f"{table} done via to_sql")


# ---------------------------------------------------------------------------
# ORCHESTRATION
# ---------------------------------------------------------------------------
def run_etl(rebuild_schema: bool = True) -> None:
    """Full ETL: extract → transform → persist → load into PostgreSQL.

    Parameters
    ----------
    rebuild_schema : bool
        If False and tables exist, skips the run (idempotent mode).
    """
    engine = get_engine()

    if not rebuild_schema and table_exists(engine, "orders"):
        print("Tables already populated; skipping ETL.")
        return

    raw = extract()
    if not raw:
        raise RuntimeError("No CSVs found in data/raw/.")

    clean = transform(raw)
    persist_parquet(clean)               # <-- explicit write step
    load(clean, engine=engine, rebuild_schema=rebuild_schema)
    print("\nDONE  ETL complete.")


if __name__ == "__main__":
    run_etl()