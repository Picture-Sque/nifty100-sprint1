from __future__ import annotations

import re
from datetime import date, datetime

PARSE_ERROR = "PARSE_ERROR"

MONTH_ALIASES = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


def _is_missing(value) -> bool:
    return value is None or value != value


def _parse_two_digit_year(year_text: str) -> int:
    year = int(year_text)
    if len(year_text) == 2:
        return 2000 + year
    return year


def normalize_ticker(ticker):
    """Normalize stock ticker symbols."""

    if _is_missing(ticker):
        return None

    return str(ticker).strip().upper()


def _normalize_year_from_parts(year: int, month: int) -> str:
    if year < 100:
        year += 2000

    if not 1 <= month <= 12:
        return PARSE_ERROR

    return f"{year:04d}-{month:02d}"


def normalize_year(year_value):
    """Normalize supported year formats into YYYY-MM."""

    if _is_missing(year_value):
        return PARSE_ERROR

    if isinstance(year_value, datetime):
        return f"{year_value.year:04d}-{year_value.month:02d}"

    if isinstance(year_value, date):
        return f"{year_value.year:04d}-{year_value.month:02d}"

    year_text = str(year_value).strip()
    if not year_text:
        return PARSE_ERROR

    upper_text = year_text.upper()

    if re.fullmatch(r"\d{4}", year_text):
        return f"{int(year_text):04d}-03"

    numeric_year_month = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", year_text)
    if numeric_year_month:
        year, month = map(int, numeric_year_month.groups())
        return _normalize_year_from_parts(year, month)

    fy_match = re.fullmatch(r"FY\s*(\d{2}|\d{4})", upper_text)
    if fy_match:
        return f"{_parse_two_digit_year(fy_match.group(1)):04d}-03"

    month_year_match = re.fullmatch(
        r"([A-Za-z]{3,9})[\s\-/.]*(\d{2}|\d{4})",
        year_text,
    )
    if month_year_match:
        month_text, year_part = month_year_match.groups()
        month = MONTH_ALIASES.get(month_text.upper())
        if month is None:
            return PARSE_ERROR

        year = _parse_two_digit_year(year_part)
        return f"{year:04d}-{month:02d}"

    return PARSE_ERROR