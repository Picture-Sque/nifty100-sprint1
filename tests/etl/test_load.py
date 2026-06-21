from __future__ import annotations

from pathlib import Path

import sqlite3

import pandas as pd
import pytest

from src.etl.loader import run_full_load, DATABASE_PATH


def test_run_full_load_creates_audit_and_db(tmp_path):
    db_path = tmp_path / "nifty100.db"
    audit_path = tmp_path / "load_audit.csv"

    audit_df = run_full_load(output_audit=audit_path, db_path=db_path, fresh=True)

    assert audit_path.exists()
    assert isinstance(audit_df, pd.DataFrame)

    conn = sqlite3.connect(db_path)
    try:
        # Check tables have rows
        for table in ["companies", "profitandloss", "balancesheet", "cashflow", "stock_prices"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
            assert count > 0

        # Check approximate expected row counts
        companies_count = conn.execute("SELECT COUNT(*) FROM companies;").fetchone()[0]
        assert companies_count >= 80

        profit_count = conn.execute("SELECT COUNT(*) FROM profitandloss;").fetchone()[0]
        assert profit_count >= 1000

        balancesheet_count = conn.execute("SELECT COUNT(*) FROM balancesheet;").fetchone()[0]
        assert balancesheet_count >= 1000

        cashflow_count = conn.execute("SELECT COUNT(*) FROM cashflow;").fetchone()[0]
        assert cashflow_count >= 1000

        stock_count = conn.execute("SELECT COUNT(*) FROM stock_prices;").fetchone()[0]
        assert stock_count >= 4000

        # Foreign key check should return no rows
        fk_failures = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert fk_failures == []
    finally:
        conn.close()
