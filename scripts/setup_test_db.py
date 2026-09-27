"""Create the olist_test database.

Run once before the first `pytest` invocation:
    python scripts/setup_test_db.py

This project uses the `postgres` superuser for local development — there
is no separate application role. In a production deployment you would
create a dedicated least-privilege role instead.

Uses AUTOCOMMIT because CREATE DATABASE cannot run inside a transaction.
"""
import sys
from pathlib import Path

# Bootstrap sys.path so `from src...` works when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from src.config import (
    DB_HOST, DB_PORT, DB_NAME, DB_TEST_NAME,
    DB_USER, DB_PASSWORD,
)


def main() -> None:
    print(f"Setting up test database: {DB_TEST_NAME}")
    print(f"  host: {DB_HOST}:{DB_PORT}")
    print(f"  user: {DB_USER}")
    print()

    # Connect to the default `postgres` maintenance database.
    # AUTOCOMMIT is required for CREATE/DROP DATABASE.
    admin_url = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/postgres"
    )
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)

    # --- Ensure the main database exists ---
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": DB_NAME},
            ).fetchone()

            if exists:
                print(f"Database '{DB_NAME}' already exists.")
            else:
                conn.exec_driver_sql(f'CREATE DATABASE "{DB_NAME}";')
                print(f"Created database '{DB_NAME}'.")
    except Exception as exc:
        print(f"\nFailed to ensure main database: {exc}")
        sys.exit(1)

    # --- Recreate the test database ---
    try:
        with admin.connect() as conn:
            # Terminate lingering connections to the test DB
            conn.exec_driver_sql(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{DB_TEST_NAME}'
                  AND pid <> pg_backend_pid();
            """)
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{DB_TEST_NAME}";')
            conn.exec_driver_sql(f'CREATE DATABASE "{DB_TEST_NAME}";')
        print(f"Created database '{DB_TEST_NAME}'.")
    except Exception as exc:
        print(f"\nFailed to create test database: {exc}")
        sys.exit(1)

    # --- Verify connection to the test DB ---
    test_url = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_TEST_NAME}"
    )
    test_engine = create_engine(test_url, future=True)

    try:
        with test_engine.connect() as conn:
            result = conn.execute(
                text("SELECT current_database(), current_user;")
            ).fetchone()
        print(f"\nVerified connection: {result[1]} @ {result[0]}")
        print("\nSetup complete. Run `pytest` to start testing.")
    except Exception as exc:
        print(f"\nVerification failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()