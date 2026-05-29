"""Remove panel-wide calendar-month means from the rent outcome (seasonality diagnostic)."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


def demean_by_calendar_month(
    panel: pd.DataFrame,
    *,
    outcome_col: str = "rental_price",
    month_col: str = "month",
    raw_backup_col: str = "rental_price_raw",
) -> pd.DataFrame:
    """Subtract month-of-year means from ``outcome_col`` (panel-wide calendar-month FE)."""
    out = panel.copy()
    out[month_col] = pd.to_datetime(out[month_col])
    if raw_backup_col not in out.columns:
        out[raw_backup_col] = out[outcome_col]
    out["_month_of_year"] = out[month_col].dt.month
    month_means = out.groupby("_month_of_year", observed=True)[outcome_col].transform(
        "mean"
    )
    out[outcome_col] = out[outcome_col] - month_means
    out = out.drop(columns=["_month_of_year"])
    return out


class SeasonalDemeanProcessor(DataProcessor):
    """Apply calendar-month demeaning to ``rental_price`` on ``did_panel``."""

    def __init__(
        self,
        outcome_col: str = "rental_price",
        raw_backup_col: str = "rental_price_raw",
    ) -> None:
        """Configure outcome column names for calendar-month demeaning."""
        super().__init__(
            "seasonal_demean",
            "Demean rental outcome by calendar month of year",
        )
        self.outcome_col = outcome_col
        self.raw_backup_col = raw_backup_col

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Replace ``did_panel`` rental_price with seasonally demeaned values."""
        did_panel = context.get("did_panel")
        if did_panel is None:
            raise ValueError("SeasonalDemeanProcessor requires did_panel in context")

        adjusted = demean_by_calendar_month(
            did_panel,
            outcome_col=self.outcome_col,
            raw_backup_col=self.raw_backup_col,
        )
        logger.info(
            "Seasonal demean: adjusted %s using panel-wide month-of-year means",
            self.outcome_col,
        )
        return {"did_panel": adjusted}
