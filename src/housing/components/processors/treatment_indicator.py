"""Treatment indicator processor for difference-in-differences analysis.

This module creates treatment indicators by merging tract-level rental panel data
with treatment dates and calculating treated status and months since treatment.
"""

from typing import Any

import pandas as pd

from pipeline.base import DataProcessor


class TreatmentIndicatorProcessor(DataProcessor):
    """Create treatment indicators for difference-in-differences analysis.

    This processor:
    1. Merges tract-level rental panel with treatment dates
    2. Creates binary treated indicator (0 = not treated, 1 = treated)
    3. Calculates months since treatment for event study analysis
    4. Outputs a DiD-ready panel DataFrame
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the treatment indicator processor."""
        super().__init__(
            "treatment_indicator", "Create treatment indicators for DiD analysis"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create treatment indicators by merging panel with treatment dates.

        Args:
            context: Pipeline context containing:
                - tract_panel_data: DataFrame with tract_geoid, month, rental_price
                - tract_prohibition_dates: DataFrame with tract_geoid, first_prohibition_date

        Returns:
            Dictionary with 'did_panel' key containing DiD-ready panel DataFrame
            with columns: tract_geoid, month, rental_price, first_prohibition_date,
            treated, months_since_treatment
        """
        # Get inputs from context
        tract_panel = context["tract_panel_data"]  # From TimeSeriesZipToTractProcessor
        treatment_dates = context["tract_prohibition_dates"]

        # Step 1: Ensure datetime types before merging
        if not pd.api.types.is_datetime64_any_dtype(tract_panel["month"]):
            tract_panel = tract_panel.copy()
            tract_panel["month"] = pd.to_datetime(tract_panel["month"])

        treatment_dates = treatment_dates.copy()
        if "first_prohibition_date" in treatment_dates.columns:
            if not pd.api.types.is_datetime64_any_dtype(
                treatment_dates["first_prohibition_date"]
            ):
                treatment_dates["first_prohibition_date"] = pd.to_datetime(
                    treatment_dates["first_prohibition_date"], errors="coerce"
                )

        # Step 2: Merge panel with treatment dates
        merged = tract_panel.merge(
            treatment_dates[["tract_geoid", "first_prohibition_date"]],
            on="tract_geoid",
            how="left",
        )

        # Step 3: Create treated indicator
        # treated = 1 if month >= first_prohibition_date, else 0
        merged["treated"] = (
            merged["month"] >= merged["first_prohibition_date"]
        ).astype(int)

        # Step 4: Calculate months since treatment
        # For never-treated tracts, this will be NaN
        # Calculate as difference in months between month and first_prohibition_date
        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["first_prohibition_date"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)

        # Step 5: Select columns
        did_panel = merged[
            [
                "tract_geoid",
                "month",
                "rental_price",
                "first_prohibition_date",
                "treated",
                "months_since_treatment",
            ]
        ].copy()

        # Sort by tract and month
        did_panel = did_panel.sort_values(["tract_geoid", "month"]).reset_index(
            drop=True
        )

        return {"did_panel": did_panel}
