"""One-command pipeline runner.

Usage:
    python scripts/run_pipeline.py
"""
from src.etl import run_etl
from src.features import build_all_features


def main() -> None:
    print("=" * 62)
    print("Olist pipeline — target: PostgreSQL")
    print("=" * 62)

    print("\n[1/2] Extract → Transform → Load")
    run_etl(rebuild_schema=True)

    print("\n[2/2] Feature engineering")
    build_all_features()

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()