"""Full-population audit tests (DuckDB SQL + Python) on a synthetic dataset."""

from pathlib import Path

__version__ = "0.1.0"

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
