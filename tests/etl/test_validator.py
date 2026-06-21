from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.etl.validator import (
    OUTPUT_PATH,
    create_validation_record,
    run_all_validations,
    validate_dq01,
    validate_dq02,
    validate_dq03,
    validate_dq04,
    validate_dq05,
    validate_dq06,
    validate_dq07,
    validate_dq08,
    validate_dq09,
    validate_dq10,
    validate_dq11,
    validate_dq12,
    validate_dq13,
    validate_dq14,
    validate_dq15,
    validate_dq16,
)


def _base_datasets() -> dict[str, pd.DataFrame]:
    companies = pd.DataFrame(
        {
            "id": ["AAA", "BBB", "CCC"],
            "company_name": ["A", "B", "C"],
        }
    )

    profitandloss = pd.DataFrame(
        {
            "company_id": ["AAA", "AAA", "BBB"],
            "year": ["Mar-23", "Mar-24", "Mar-23"],
            "sales": [100.0, 120.0, 150.0],
            "operating_profit": [20.0, 24.0, 30.0],
            "opm_percentage": [20.0, 20.0, 20.0],
            "tax_percentage": [10.0, 15.0, 12.0],
            "dividend_payout": [100.0, 120.0, 50.0],
            "eps": [5.0, 6.0, 7.0],
        }
    )

    balancesheet = pd.DataFrame(
        {
            "company_id": ["AAA", "AAA", "BBB"],
            "year": ["Mar-23", "Mar-24", "Mar-23"],
            "total_assets": [100.0, 100.0, 100.0],
            "total_liabilities": [100.0, 101.5, 100.0],
            "fixed_assets": [10.0, 11.0, 12.0],
        }
    )

    cashflow = pd.DataFrame(
        {
            "company_id": ["AAA", "AAA", "BBB"],
            "year": ["Mar-23", "Mar-24", "Mar-23"],
            "operating_activity": [100.0, 110.0, 120.0],
            "investing_activity": [-20.0, -10.0, -30.0],
            "financing_activity": [-30.0, -20.0, -40.0],
            "net_cash_flow": [50.0, 80.0, 50.0],
        }
    )

    financial_ratios = pd.DataFrame(
        {
            "company_id": ["AAA", "AAA", "BBB"],
            "year": ["Mar-23", "Mar-24", "Mar-23"],
            "earnings_per_share": [5.0, 6.0, 7.2],
        }
    )

    market_cap = pd.DataFrame(
        {
            "company_id": ["AAA", "AAA", "BBB"],
            "year": ["2023", "2024", "2023"],
            "market_cap_crore": [1000.0, 1200.0, 1300.0],
        }
    )

    documents = pd.DataFrame(
        {
            "company_id": ["AAA", "BBB", "CCC"],
            "Year": ["2024", "2023", "2022"],
            "Annual_Report": [
                "https://example.com/a.pdf",
                "https://example.com/b.pdf",
                "https://example.com/c.pdf",
            ],
        }
    )

    analysis = pd.DataFrame({"company_id": ["AAA"], "compounded_sales_growth": [1.0]})
    sectors = pd.DataFrame({"company_id": ["AAA"], "broad_sector": ["IT"]})
    stock_prices = pd.DataFrame({"company_id": ["AAA"], "date": ["2024-01-01"]})
    peer_groups = pd.DataFrame({"company_id": ["AAA"], "peer_group_name": ["Group"]})
    prosandcons = pd.DataFrame({"company_id": ["AAA"], "pros": ["x"], "cons": ["y"]})

    return {
        "companies": companies,
        "profitandloss": profitandloss,
        "balancesheet": balancesheet,
        "cashflow": cashflow,
        "financial_ratios": financial_ratios,
        "market_cap": market_cap,
        "documents": documents,
        "analysis": analysis,
        "sectors": sectors,
        "stock_prices": stock_prices,
        "peer_groups": peer_groups,
        "prosandcons": prosandcons,
    }


def test_dq01_detects_duplicate_company_ids():
    datasets = _base_datasets()
    datasets["companies"] = pd.DataFrame({"id": ["AAA", "AAA", "BBB"]})

    records = validate_dq01(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-01"


def test_dq02_detects_duplicate_company_year_pairs():
    datasets = _base_datasets()
    datasets["profitandloss"] = pd.DataFrame(
        {"company_id": ["AAA", "AAA"], "year": ["Mar-23", "Mar-23"], "sales": [1, 2]}
    )

    records = validate_dq02(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-02"


def test_dq03_detects_foreign_key_violation():
    datasets = _base_datasets()
    datasets["cashflow"] = pd.DataFrame(
        {
            "company_id": ["ZZZ"],
            "year": ["Mar-23"],
            "operating_activity": [1.0],
            "investing_activity": [0.0],
            "financing_activity": [0.0],
            "net_cash_flow": [1.0],
        }
    )

    records = validate_dq03(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-03"


def test_dq04_detects_balance_sheet_imbalance():
    datasets = _base_datasets()
    datasets["balancesheet"].loc[1, "total_liabilities"] = 150.0

    records = validate_dq04(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-04"


def test_dq05_detects_opm_mismatch():
    datasets = _base_datasets()
    datasets["profitandloss"].loc[0, "opm_percentage"] = 5.0

    records = validate_dq05(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-05"


def test_dq06_detects_negative_sales():
    datasets = _base_datasets()
    datasets["profitandloss"].loc[0, "sales"] = -1.0

    records = validate_dq06(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-06"


def test_dq07_detects_invalid_year():
    datasets = _base_datasets()
    datasets["documents"].loc[0, "Year"] = "not-a-year"

    records = validate_dq07(datasets)

    assert any(record["rule_id"] == "DQ-07" for record in records)


def test_dq08_detects_invalid_ticker_length():
    datasets = _base_datasets()
    datasets["cashflow"].loc[0, "company_id"] = "A"

    records = validate_dq08(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-08"


def test_dq09_detects_cash_flow_mismatch():
    datasets = _base_datasets()
    datasets["cashflow"].loc[0, "net_cash_flow"] = 999.0

    records = validate_dq09(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-09"


def test_dq10_detects_negative_fixed_assets():
    datasets = _base_datasets()
    datasets["balancesheet"].loc[0, "fixed_assets"] = -10.0

    records = validate_dq10(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-10"


def test_dq11_detects_tax_out_of_range():
    datasets = _base_datasets()
    datasets["profitandloss"].loc[0, "tax_percentage"] = 61.0

    records = validate_dq11(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-11"


def test_dq11_ignores_null_tax_percentage():
    datasets = _base_datasets()
    datasets["profitandloss"].loc[0, "tax_percentage"] = None

    records = validate_dq11(datasets)

    assert records == []


def test_dq12_detects_dividend_cap_breach():
    datasets = _base_datasets()
    datasets["profitandloss"].loc[0, "dividend_payout"] = 201.0

    records = validate_dq12(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-12"


def test_dq13_detects_invalid_url():
    datasets = _base_datasets()
    datasets["documents"].loc[0, "Annual_Report"] = "ftp://invalid.example.com/file.pdf"

    records = validate_dq13(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-13"


def test_dq14_detects_eps_mismatch():
    datasets = _base_datasets()
    datasets["financial_ratios"].loc[0, "earnings_per_share"] = 20.0

    records = validate_dq14(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-14"


def test_dq15_detects_non_positive_market_cap():
    datasets = _base_datasets()
    datasets["market_cap"].loc[0, "market_cap_crore"] = 0.0

    records = validate_dq15(datasets)

    assert len(records) == 1
    assert records[0]["rule_id"] == "DQ-15"


def test_dq16_detects_low_history_coverage():
    datasets = _base_datasets()

    records = validate_dq16(datasets)

    assert len(records) == 3
    assert all(record["rule_id"] == "DQ-16" for record in records)


def test_run_all_validations_exports_csv(tmp_path, monkeypatch):
    datasets = _base_datasets()
    monkeypatch.setattr("src.etl.validator.OUTPUT_PATH", tmp_path / "validation_failures.csv")

    failures = run_all_validations(datasets)

    assert isinstance(failures, pd.DataFrame)
    assert Path(tmp_path / "validation_failures.csv").exists()
    assert list(failures.columns) == ["rule_id", "severity", "table_name", "company_id", "year", "message"]
