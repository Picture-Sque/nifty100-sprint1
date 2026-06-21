from __future__ import annotations

from pathlib import Path

import pytest

from src.etl.loader import (
    DATABASE_PATH,
    EXPECTED_TABLES,
    SCHEMA_PATH,
    create_database,
    execute_schema,
    get_connection,
    verify_schema,
)


def _table_names(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    return [row[0] for row in rows]


def test_schema_file_exists():
    assert SCHEMA_PATH.exists()


def test_get_connection_enables_foreign_keys(tmp_path):
    db_path = tmp_path / "test.db"
    connection = get_connection(db_path)
    try:
        assert connection.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
    finally:
        connection.close()


def test_create_database_creates_file(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        assert db_path.exists()
    finally:
        connection.close()


def test_execute_schema_creates_expected_tables(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = get_connection(db_path)
    try:
        execute_schema(connection, schema_path=SCHEMA_PATH)
        assert set(EXPECTED_TABLES).issubset(set(_table_names(connection)))
    finally:
        connection.close()


def test_verify_schema_reports_no_missing_tables(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        report = verify_schema(connection)
        assert report["missing_tables"] == []
    finally:
        connection.close()


def test_verify_schema_reports_foreign_keys_enabled(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        report = verify_schema(connection)
        assert report["foreign_keys_enabled"] is True
    finally:
        connection.close()


@pytest.mark.parametrize(
    "table_name",
    [
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
    ],
)
def test_child_tables_reference_companies(tmp_path, table_name):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        fk_rows = connection.execute(f"PRAGMA foreign_key_list({table_name});").fetchall()
        assert any(row[2] == "companies" and row[3] == "company_id" and row[4] == "id" for row in fk_rows)
    finally:
        connection.close()


def test_companies_primary_key_is_text(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        columns = connection.execute("PRAGMA table_info(companies);").fetchall()
        pk_column = next(column for column in columns if column[1] == "id")
        assert pk_column[5] == 1
        assert pk_column[2].upper() == "TEXT"
    finally:
        connection.close()


def test_expected_tables_are_present(tmp_path):
    db_path = tmp_path / "nifty100.db"
    connection = create_database(db_path=db_path)
    try:
        table_names = _table_names(connection)
        assert set(EXPECTED_TABLES).issubset(set(table_names))
        assert len([name for name in table_names if name in EXPECTED_TABLES]) == 12
    finally:
        connection.close()


def test_schema_can_be_executed_twice_with_fresh_database(tmp_path):
    db_path = tmp_path / "nifty100.db"
    first_connection = create_database(db_path=db_path)
    first_connection.close()
    second_connection = create_database(db_path=db_path)
    try:
        assert set(EXPECTED_TABLES).issubset(set(_table_names(second_connection)))
    finally:
        second_connection.close()