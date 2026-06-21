from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"
DATABASE_PATH = PROJECT_ROOT / "data" / "nifty100.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"

EXPECTED_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "financial_ratios",
    "market_cap",
    "peer_groups",
]

CORE_FILES = {
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
}


def _resolve_dataset_path(dataset: str | Path) -> Path:
    dataset_path = Path(dataset)

    if dataset_path.is_absolute():
        return dataset_path

    raw_candidate = RAW_DATA_PATH / dataset_path
    if raw_candidate.exists():
        return raw_candidate

    project_candidate = PROJECT_ROOT / dataset_path
    if project_candidate.exists():
        return project_candidate

    return dataset_path


def _read_excel_with_header(file_path: Path, header: int) -> pd.DataFrame:
    return pd.read_excel(file_path, header=header)


def load_excel(file_path: str | Path, header: int | None = None) -> pd.DataFrame:
    resolved_path = _resolve_dataset_path(file_path)

    if header is None:
        header = 1 if resolved_path.name in CORE_FILES else 0

    return _read_excel_with_header(resolved_path, header=header)


def load_dataset(dataset: str | Path) -> pd.DataFrame:
    return load_excel(dataset)


def load_all_datasets(raw_dir: str | Path = RAW_DATA_PATH) -> Dict[str, pd.DataFrame]:
    raw_path = _resolve_dataset_path(raw_dir)
    datasets: Dict[str, pd.DataFrame] = {}

    for file_path in sorted(raw_path.glob("*.xlsx")):
        datasets[file_path.stem] = load_dataset(file_path)

    return datasets


def build_audit_report(raw_dir: str | Path = RAW_DATA_PATH) -> str:
    datasets = load_all_datasets(raw_dir)
    report_lines = [
        "=" * 80,
        "NIFTY100 DATA AUDIT REPORT",
        "=" * 80,
    ]

    for dataset_name, dataframe in datasets.items():
        report_lines.extend(
            [
                f"\nDataset : {dataset_name}.xlsx",
                f"Rows     : {dataframe.shape[0]}",
                f"Columns  : {dataframe.shape[1]}",
                "Column Names:",
                str(list(dataframe.columns)),
                "-" * 80,
            ]
        )

    return "\n".join(report_lines)


def main() -> None:
    print(build_audit_report())


def get_connection(db_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(db_path))
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def execute_schema(
    connection: sqlite3.Connection,
    schema_path: str | Path = SCHEMA_PATH,
) -> None:
    schema_text = Path(schema_path).read_text(encoding="utf-8")
    connection.executescript(schema_text)
    connection.commit()


def create_database(
    db_path: str | Path = DATABASE_PATH,
    schema_path: str | Path = SCHEMA_PATH,
    fresh: bool = True,
) -> sqlite3.Connection:
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if fresh and database_path.exists():
        database_path.unlink()

    connection = get_connection(database_path)
    execute_schema(connection, schema_path=schema_path)
    return connection


def verify_schema(connection: sqlite3.Connection) -> dict[str, object]:
    table_rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    tables = [row[0] for row in table_rows]

    foreign_key_map: dict[str, list[dict[str, object]]] = {}
    for table_name in EXPECTED_TABLES:
        rows = connection.execute(f"PRAGMA foreign_key_list({table_name});").fetchall()
        foreign_key_map[table_name] = [
            {
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_update": row[5],
                "on_delete": row[6],
            }
            for row in rows
        ]

    return {
        "tables": tables,
        "missing_tables": [table for table in EXPECTED_TABLES if table not in tables],
        "foreign_keys_enabled": connection.execute("PRAGMA foreign_keys;").fetchone()[0] == 1,
        "foreign_key_map": foreign_key_map,
    }


if __name__ == "__main__":
    main()