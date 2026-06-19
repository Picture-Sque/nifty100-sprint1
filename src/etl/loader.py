from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"

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


if __name__ == "__main__":
    main()