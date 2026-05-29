"""Tests for cohort ATT LaTeX table builder and seasonal demean."""

from __future__ import annotations

import pandas as pd

from housing.components.analyzers.cohort_att_latex import build_cohort_att_table_lines
from housing.components.processors.seasonal_demean import demean_by_calendar_month


def test_demean_by_calendar_month_removes_month_means() -> None:
    """Month-of-year means are removed from the demeaned outcome."""
    panel = pd.DataFrame(
        {
            "tract_geoid": ["1", "1", "2", "2"],
            "month": pd.to_datetime(
                ["2020-01-01", "2020-02-01", "2020-01-01", "2020-02-01"]
            ),
            "rental_price": [100.0, 200.0, 110.0, 210.0],
        }
    )
    out = demean_by_calendar_month(panel)
    jan_mean = out.loc[out["month"].dt.month == 1, "rental_price"].mean()
    feb_mean = out.loc[out["month"].dt.month == 2, "rental_price"].mean()
    assert abs(jan_mean) < 1e-9
    assert abs(feb_mean) < 1e-9
    assert "rental_price_raw" in out.columns


def test_build_cohort_att_table_highlights_2019_10() -> None:
    """2019-10 cohort row is bolded in the LaTeX table output."""
    att = pd.DataFrame(
        [
            {
                "level": "overall",
                "cohort": None,
                "att": 5.0,
                "se": 1.0,
                "n_treated": None,
            },
            {
                "level": "cohort",
                "cohort": "2019-10-01",
                "att": 8.0,
                "se": 2.0,
                "n_treated": 13,
            },
            {
                "level": "cohort",
                "cohort": "2016-07-01",
                "att": 3.0,
                "se": 5.0,
                "n_treated": 62,
            },
        ]
    )
    sig = pd.DataFrame(
        [
            {"cohort": "2019-10-01", "n_pre_periods": 11, "n_significant_pre_coefs": 1},
            {"cohort": "2016-07-01", "n_pre_periods": 11, "n_significant_pre_coefs": 9},
        ]
    )
    lines = build_cohort_att_table_lines(att, sig)
    text = "\n".join(lines)
    assert "\\textbf{2019-10}" in text
    assert "2016-07" in text
    assert "Clean" in text
