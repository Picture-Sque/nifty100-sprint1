from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

import pandas as pd

from src.etl.loader import load_all_datasets
from src.etl.normaliser import PARSE_ERROR, normalize_ticker, normalize_year

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "output" / "validation_failures.csv"

VALIDATION_COLUMNS = [
    "rule_id",
    "severity",
    "table_name",
    "company_id",
    "year",
    "message",
]

CRITICAL = "CRITICAL"
WARNING = "WARNING"


def _is_missing(value) -> bool:
    return value is None or value != value


def _to_number(value):
    if _is_missing(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_company_id(value) -> Optional[str]:
    normalized = normalize_ticker(value)
    if normalized is None:
        return None

    return normalized


def _normalize_year_value(value) -> Optional[str]:
    if _is_missing(value):
        return None

    normalized = normalize_year(value)
    if normalized == PARSE_ERROR:
        return PARSE_ERROR

    return normalized


def _year_column(frame: pd.DataFrame) -> Optional[str]:
    for candidate in ("year", "Year"):
        if candidate in frame.columns:
            return candidate
    return None


def _frame_row_count(frame: pd.DataFrame) -> int:
    return int(frame.shape[0])


def create_validation_record(
    rule_id: str,
    severity: str,
    table_name: str,
    company_id: Optional[str],
    year: Optional[str],
    message: str,
) -> dict:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "table_name": table_name,
        "company_id": company_id,
        "year": year,
        "message": message,
    }


def _duplicate_key_records(
    frame: pd.DataFrame,
    table_name: str,
    rule_id: str,
    severity: str,
    key_columns: List[str],
) -> List[dict]:
    if frame.empty:
        return []

    working_frame = frame.copy()
    for column in key_columns:
        if column == "company_id":
            working_frame[column] = working_frame[column].map(_normalize_company_id)
        elif column in ("year", "Year"):
            working_frame[column] = working_frame[column].map(_normalize_year_value)

    duplicate_mask = working_frame.duplicated(subset=key_columns, keep=False)
    duplicates = working_frame.loc[duplicate_mask, key_columns].drop_duplicates()

    records = []
    for _, row in duplicates.iterrows():
        company_id = row[key_columns[0]] if "company_id" in key_columns else None
        year_value = None
        if "year" in key_columns:
            year_value = row["year"]
        elif "Year" in key_columns:
            year_value = row["Year"]

        records.append(
            create_validation_record(
                rule_id=rule_id,
                severity=severity,
                table_name=table_name,
                company_id=company_id,
                year=year_value,
                message=f"Duplicate {', '.join(key_columns)} combination detected.",
            )
        )

    return records


def validate_dq01(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    companies = datasets["companies"]
    working_frame = companies.copy()
    working_frame["id"] = working_frame["id"].map(_normalize_company_id)

    duplicate_mask = working_frame.duplicated(subset=["id"], keep=False)
    duplicates = working_frame.loc[duplicate_mask, ["id"]].drop_duplicates()

    return [
        create_validation_record(
            rule_id="DQ-01",
            severity=CRITICAL,
            table_name="companies",
            company_id=row["id"],
            year=None,
            message="Duplicate primary key detected in companies.id.",
        )
        for _, row in duplicates.iterrows()
    ]


def validate_dq02(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    records: List[dict] = []
    for table_name in [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
    ]:
        frame = datasets[table_name]
        year_column = _year_column(frame)
        if year_column is None:
            continue

        working_frame = frame.copy()
        working_frame["company_id"] = working_frame["company_id"].map(_normalize_company_id)
        working_frame[year_column] = working_frame[year_column].map(_normalize_year_value)

        duplicate_mask = working_frame.duplicated(subset=["company_id", year_column], keep=False)
        duplicates = working_frame.loc[duplicate_mask, ["company_id", year_column]].drop_duplicates()

        for _, row in duplicates.iterrows():
            records.append(
                create_validation_record(
                    rule_id="DQ-02",
                    severity=CRITICAL,
                    table_name=table_name,
                    company_id=row["company_id"],
                    year=row[year_column],
                    message="Duplicate company_id/year combination detected.",
                )
            )

    return records


def validate_dq03(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    companies = datasets["companies"]
    valid_company_ids = {
        _normalize_company_id(value)
        for value in companies["id"].tolist()
    }

    records: List[dict] = []
    child_tables = [
        table_name
        for table_name, frame in datasets.items()
        if table_name != "companies" and "company_id" in frame.columns
    ]

    for table_name in child_tables:
        frame = datasets[table_name]
        year_column = _year_column(frame)
        working_frame = frame.copy()
        working_frame["company_id"] = working_frame["company_id"].map(_normalize_company_id)
        if year_column is not None:
            working_frame[year_column] = working_frame[year_column].map(_normalize_year_value)

        invalid_mask = ~working_frame["company_id"].isin(valid_company_ids)
        invalid_rows = working_frame.loc[invalid_mask]

        for _, row in invalid_rows.iterrows():
            records.append(
                create_validation_record(
                    rule_id="DQ-03",
                    severity=CRITICAL,
                    table_name=table_name,
                    company_id=row["company_id"],
                    year=row[year_column] if year_column is not None else None,
                    message="Foreign key company_id not found in companies.id.",
                )
            )

    return records


def validate_dq04(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["balancesheet"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        total_assets = _to_number(row.get("total_assets"))
        total_liabilities = _to_number(row.get("total_liabilities"))
        if total_assets in (None, 0) or total_liabilities is None:
            continue

        gap = abs(total_assets - total_liabilities)
        tolerance = max(abs(total_assets), abs(total_liabilities)) * 0.01
        if gap > tolerance:
            records.append(
                create_validation_record(
                    rule_id="DQ-04",
                    severity=WARNING,
                    table_name="balancesheet",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Balance sheet assets and liabilities differ by more than 1%.",
                )
            )

    return records


def validate_dq05(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["profitandloss"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        sales = _to_number(row.get("sales"))
        operating_profit = _to_number(row.get("operating_profit"))
        opm_percentage = _to_number(row.get("opm_percentage"))
        if sales in (None, 0) or operating_profit is None or opm_percentage is None:
            continue

        computed = operating_profit / sales * 100
        if abs(computed - opm_percentage) > max(1.0, abs(opm_percentage) * 0.01):
            records.append(
                create_validation_record(
                    rule_id="DQ-05",
                    severity=WARNING,
                    table_name="profitandloss",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Operating profit margin does not match operating_profit / sales.",
                )
            )

    return records


def validate_dq06(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["profitandloss"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        sales = _to_number(row.get("sales"))
        if sales is not None and sales <= 0:
            records.append(
                create_validation_record(
                    rule_id="DQ-06",
                    severity=WARNING,
                    table_name="profitandloss",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Sales must be positive.",
                )
            )

    return records


def validate_dq07(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    records: List[dict] = []
    for table_name, frame in datasets.items():
        year_column = _year_column(frame)
        if year_column is None:
            continue

        for _, row in frame.iterrows():
            normalized_year = _normalize_year_value(row.get(year_column))
            if normalized_year == PARSE_ERROR:
                records.append(
                    create_validation_record(
                        rule_id="DQ-07",
                        severity=CRITICAL,
                        table_name=table_name,
                        company_id=_normalize_company_id(row.get("company_id")) if "company_id" in frame.columns else None,
                        year=str(row.get(year_column)).strip() if not _is_missing(row.get(year_column)) else None,
                        message="Year value could not be normalized.",
                    )
                )

    return records


def validate_dq08(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    records: List[dict] = []
    child_tables = [
        table_name
        for table_name, frame in datasets.items()
        if table_name != "companies" and "company_id" in frame.columns
    ]

    for table_name in child_tables:
        frame = datasets[table_name]
        year_column = _year_column(frame)
        for _, row in frame.iterrows():
            raw_value = row.get("company_id")
            normalized = normalize_ticker(raw_value)
            if normalized is None or not (2 <= len(normalized) <= 20) or normalized != normalized.upper():
                records.append(
                    create_validation_record(
                        rule_id="DQ-08",
                        severity=CRITICAL,
                        table_name=table_name,
                        company_id=normalized,
                        year=_normalize_year_value(row.get(year_column)) if year_column else None,
                        message="Invalid ticker format.",
                    )
                )

    return records


def validate_dq09(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["cashflow"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        operating = _to_number(row.get("operating_activity"))
        investing = _to_number(row.get("investing_activity"))
        financing = _to_number(row.get("financing_activity"))
        net_cash_flow = _to_number(row.get("net_cash_flow"))
        if None in (operating, investing, financing, net_cash_flow):
            continue

        computed = operating + investing + financing
        if abs(computed - net_cash_flow) > max(1.0, abs(net_cash_flow) * 0.01):
            records.append(
                create_validation_record(
                    rule_id="DQ-09",
                    severity=WARNING,
                    table_name="cashflow",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Cash flow components do not reconcile to net cash flow.",
                )
            )

    return records


def validate_dq10(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["balancesheet"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        fixed_assets = _to_number(row.get("fixed_assets"))
        if fixed_assets is not None and fixed_assets < 0:
            records.append(
                create_validation_record(
                    rule_id="DQ-10",
                    severity=WARNING,
                    table_name="balancesheet",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Fixed assets must be non-negative.",
                )
            )

    return records


def validate_dq11(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["profitandloss"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        tax_percentage = _to_number(row.get("tax_percentage"))
        if tax_percentage is None:
            continue

        if tax_percentage < 0 or tax_percentage > 60:
            records.append(
                create_validation_record(
                    rule_id="DQ-11",
                    severity=WARNING,
                    table_name="profitandloss",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Tax percentage must be between 0 and 60.",
                )
            )

    return records


def validate_dq12(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["profitandloss"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        dividend_payout = _to_number(row.get("dividend_payout"))
        if dividend_payout is None:
            continue

        if dividend_payout > 200:
            records.append(
                create_validation_record(
                    rule_id="DQ-12",
                    severity=WARNING,
                    table_name="profitandloss",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Dividend payout must not exceed 200.",
                )
            )

    return records


def validate_dq13(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["documents"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        url_value = row.get("Annual_Report")
        if _is_missing(url_value) or not str(url_value).strip():
            records.append(
                create_validation_record(
                    rule_id="DQ-13",
                    severity=WARNING,
                    table_name="documents",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Annual_Report URL is missing.",
                )
            )
            continue

        parsed = urlparse(str(url_value).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            records.append(
                create_validation_record(
                    rule_id="DQ-13",
                    severity=WARNING,
                    table_name="documents",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Annual_Report URL is invalid.",
                )
            )

    return records


def validate_dq14(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    profitandloss = datasets["profitandloss"]
    financial_ratios = datasets["financial_ratios"]

    pl_year_column = _year_column(profitandloss)
    fr_year_column = _year_column(financial_ratios)

    pl_frame = profitandloss.copy()
    fr_frame = financial_ratios.copy()
    pl_frame["company_id"] = pl_frame["company_id"].map(_normalize_company_id)
    fr_frame["company_id"] = fr_frame["company_id"].map(_normalize_company_id)
    if pl_year_column:
        pl_frame[pl_year_column] = pl_frame[pl_year_column].map(_normalize_year_value)
    if fr_year_column:
        fr_frame[fr_year_column] = fr_frame[fr_year_column].map(_normalize_year_value)

    merged = pl_frame[["company_id", pl_year_column, "eps"]].merge(
        fr_frame[["company_id", fr_year_column, "earnings_per_share"]],
        left_on=["company_id", pl_year_column],
        right_on=["company_id", fr_year_column],
        how="inner",
        suffixes=("_pl", "_fr"),
    )

    records: List[dict] = []
    for _, row in merged.iterrows():
        eps_pl = _to_number(row.get("eps"))
        eps_fr = _to_number(row.get("earnings_per_share"))
        if None in (eps_pl, eps_fr):
            continue

        tolerance = max(0.1, abs(eps_fr) * 0.05)
        if abs(eps_pl - eps_fr) > tolerance:
            records.append(
                create_validation_record(
                    rule_id="DQ-14",
                    severity=WARNING,
                    table_name="financial_ratios",
                    company_id=row["company_id"],
                    year=row[pl_year_column],
                    message="EPS values do not match across profitandloss and financial_ratios.",
                )
            )

    return records


def validate_dq15(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    frame = datasets["market_cap"]
    year_column = _year_column(frame)
    records: List[dict] = []

    for _, row in frame.iterrows():
        market_cap = _to_number(row.get("market_cap_crore"))
        if market_cap is not None and market_cap <= 0:
            records.append(
                create_validation_record(
                    rule_id="DQ-15",
                    severity=WARNING,
                    table_name="market_cap",
                    company_id=_normalize_company_id(row.get("company_id")),
                    year=_normalize_year_value(row.get(year_column)) if year_column else None,
                    message="Market cap must be positive.",
                )
            )

    return records


def validate_dq16(datasets: Dict[str, pd.DataFrame]) -> List[dict]:
    history_tables = [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
    ]

    history_by_company: Dict[str, set] = {
        company_id: set()
        for company_id in [
            _normalize_company_id(value)
            for value in datasets["companies"]["id"].tolist()
        ]
        if company_id is not None
    }
    for table_name in history_tables:
        frame = datasets[table_name]
        year_column = _year_column(frame)
        if year_column is None:
            continue

        for _, row in frame.iterrows():
            company_id = _normalize_company_id(row.get("company_id"))
            year_value = _normalize_year_value(row.get(year_column))
            if company_id is None or year_value in (None, PARSE_ERROR):
                continue

            history_by_company.setdefault(company_id, set()).add(year_value)

    records: List[dict] = []
    for company_id, years in sorted(history_by_company.items()):
        if len(years) < 5:
            records.append(
                create_validation_record(
                    rule_id="DQ-16",
                    severity=WARNING,
                    table_name="companies",
                    company_id=company_id,
                    year=max(years) if years else None,
                    message=f"Company has only {len(years)} years of financial history.",
                )
            )

    return records


def run_all_validations(datasets: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    if datasets is None:
        datasets = load_all_datasets()

    records: List[dict] = []
    records.extend(validate_dq01(datasets))
    records.extend(validate_dq02(datasets))
    records.extend(validate_dq03(datasets))
    records.extend(validate_dq04(datasets))
    records.extend(validate_dq05(datasets))
    records.extend(validate_dq06(datasets))
    records.extend(validate_dq07(datasets))
    records.extend(validate_dq08(datasets))
    records.extend(validate_dq09(datasets))
    records.extend(validate_dq10(datasets))
    records.extend(validate_dq11(datasets))
    records.extend(validate_dq12(datasets))
    records.extend(validate_dq13(datasets))
    records.extend(validate_dq14(datasets))
    records.extend(validate_dq15(datasets))
    records.extend(validate_dq16(datasets))

    failures = pd.DataFrame(records, columns=VALIDATION_COLUMNS)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    failures.to_csv(OUTPUT_PATH, index=False)
    return failures


def main() -> pd.DataFrame:
    failures = run_all_validations()
    print(f"Validation failures written to {OUTPUT_PATH}")
    print(f"Total records: {len(failures)}")
    return failures


if __name__ == "__main__":
    main()