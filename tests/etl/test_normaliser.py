from datetime import date, datetime

import pytest

from src.etl.normaliser import PARSE_ERROR, normalize_ticker, normalize_year


@pytest.mark.parametrize(
    "ticker, expected",
    [
        ("tcs", "TCS"),
        ("  infy  ", "INFY"),
        ("HDFCBANK", "HDFCBANK"),
        ("m&m", "M&M"),
        (" M&M ", "M&M"),
        ("bajaj-auto", "BAJAJ-AUTO"),
        (" bajaj-auto ", "BAJAJ-AUTO"),
        ("reliance", "RELIANCE"),
        ("  reliance  ", "RELIANCE"),
        ("itc", "ITC"),
        ("  ITC  ", "ITC"),
        ("sbin", "SBIN"),
        ("SBIN", "SBIN"),
        ("ongc", "ONGC"),
        ("  ongc  ", "ONGC"),
        ("nhpc", "NHPC"),
        (None, None),
    ],
)
def test_normalize_ticker_cases(ticker, expected):
    assert normalize_ticker(ticker) == expected


@pytest.mark.parametrize(
    "year_value, expected",
    [
        ("Mar-23", "2023-03"),
        ("Mar 23", "2023-03"),
        ("March-2023", "2023-03"),
        ("2023", "2023-03"),
        ("FY23", "2023-03"),
        ("Dec-22", "2022-12"),
        ("Jun-23", "2023-06"),
        ("2023-03", "2023-03"),
        ("Dec 2012", "2012-12"),
        ("Mar 2014", "2014-03"),
        ("  Mar-23  ", "2023-03"),
        ("MAY-24", "2024-05"),
        ("february-2021", "2021-02"),
        ("2024/07", "2024-07"),
        ("2024.7", "2024-07"),
        ("FY2024", "2024-03"),
        (date(2019, 1, 1), "2019-01"),
        (datetime(2020, 11, 15, 8, 30), "2020-11"),
        (" 2025 ", "2025-03"),
        ("Sep-29", "2029-09"),
        ("OCT 2018", "2018-10"),
        ("jan-00", "2000-01"),
    ],
)
def test_normalize_year_supported_cases(year_value, expected):
    assert normalize_year(year_value) == expected


@pytest.mark.parametrize(
    "year_value",
    [
        None,
        "",
        "   ",
        "abc",
        "2023-13",
        "2023-00",
        "FY",
        "Month-23",
        "202",
        "23",
        "Mar-20233",
        "2023-3-5",
        "13-2023",
        "Q1-2023",
        "2023-abc",
        float("nan"),
    ],
)
def test_normalize_year_invalid_cases(year_value):
    assert normalize_year(year_value) == PARSE_ERROR