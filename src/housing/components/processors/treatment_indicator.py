"""Treatment indicator processor for difference-in-differences analysis.

This module creates treatment indicators and relative time variables for
tract-level rental panel data, enabling difference-in-differences (DiD)
analysis of short-term rental (STR) prohibition effects on rental prices.
"""

import logging
from pathlib import Path
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Create treatment indicators for difference-in-differences analysis.

    This processor merges tract-level rental panel data with treatment dates
    (STR prohibition dates) and creates:
    1. Binary treatment indicator (`treated`): 0 before treatment, 1 after
    2. Relative time variable (`months_since_treatment`): months before/after
       treatment date

    Args:
    - output_dir: Optional output directory for visualizations

    Returns:
    - `did_panel`: DataFrame with added `treated` and `months_since_treatment`
      columns, ready for DiD analysis.
    - `did_panel_csv`: Path to did_panel DataFrame saved as csv
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the treatment indicator processor."""
        super().__init__(
            "treatment_indicator",
            "Create treatment indicators for difference-in-differences analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create treatment indicators and relative time variables.

        Merges the tract rental panel with treatment dates and creates:
        - `treated`: Binary indicator (0 = untreated, 1 = treated)
        - `months_since_treatment`: Relative time in months from treatment date

        Args:
            context: Pipeline context dictionary

        Returns:
            Dictionary with output key containing the DiD panel DataFrame with
            treatment indicators added.

        Raises:
            KeyError: If required data keys are missing from context.
            ValueError: If input data does not have expected columns.
        """
        # Get data from context
        treatments = context["tract_prohibition_dates"]
        panel_data = context["tract_panel_data"]

        # Merge panel data with treatment dates
        merged = panel_data.merge(treatments, on="tract_geoid", how="left")

        # Create indicator variable
        merged["treated"] = (
            merged["month"].dt.to_period("M") >= merged["first_prohibition_date"].dt.to_period("M")
        ).astype(int)

        treatment_counts = merged.groupby("treated")["tract_geoid"].nunique()
        logger.info(
            "Unique tracts by treatment status - Untreated (0): %d, Treated (1): %d",
            treatment_counts.get(0, 0),
            treatment_counts.get(1, 0),
        )

        # Create relative time variable
        # Never treated tracts will have NaN values (this is expected)
        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["first_prohibition_date"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)

        # Data Validation Checks

        # Check never-treated tracts have treated=0 always
        never_treated = merged[merged["first_prohibition_date"].isna()]
        never_treated_check = (never_treated["treated"] == 0).all()
        logger.info(
            "validation: never-treated tracts have treated=0: %s", never_treated_check
        )

        # Check treated tracts switch at the right time
        passed_check = 1
        treated_tracts = merged[merged["first_prohibition_date"].notna()]
        for tract_id, group in treated_tracts.groupby("tract_geoid"):
            first_treated_month = group.loc[group["treated"] == 1, "month"].min()
            prohibition_date = group["first_prohibition_date"].iloc[0]
            if (first_treated_month.month != prohibition_date.month) or (
                first_treated_month.year != prohibition_date.year
            ):
                logger.warning("Treatment date mismatch for %s", tract_id)
                passed_check = 0
        if passed_check == 1:
            logger.info("Treatment dates aligned for all tracts.")

        # Create csv file output
        output_path = Path(self.output_dir) / "did_panel_data.csv"
        merged.to_csv(output_path)

        return {"did_panel": merged, "did_panel_csv": str(output_path)}
