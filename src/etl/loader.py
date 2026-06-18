from pathlib import Path
import pandas as pd

RAW_DATA_PATH = Path("data/raw")

CORE_FILES = {
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx"
}

excel_files = sorted(RAW_DATA_PATH.glob("*.xlsx"))

print("=" * 80)
print("NIFTY100 DATA AUDIT REPORT")
print("=" * 80)

for file in excel_files:

    if file.name in CORE_FILES:
        df = pd.read_excel(file, header=1)
    else:
        df = pd.read_excel(file)

    print(f"\nDataset : {file.name}")
    print(f"Rows     : {df.shape[0]}")
    print(f"Columns  : {df.shape[1]}")

    print("Column Names:")
    print(list(df.columns))

    print("-" * 80)