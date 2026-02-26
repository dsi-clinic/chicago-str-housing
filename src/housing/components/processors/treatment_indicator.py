"""Treatment indicator processor for DiD analysis.

This module adds treatment indicators to the tract-level rental panel,
creating a DiD-ready dataset with treatment timing information.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Add treatment indicators to tract-level rental panel.

    This processor:
    1. Merges the tract-level rental panel with tract prohibition dates
    2. Creates binary treatment indicator (0 before treatment, 1 after)
    3. Creates relative time variable (months since treatment) for event study
    4. Returns DiD-ready panel data

    For never-treated tracts:
    - treated = 0 for all periods
    - months_since_treatment = NaN (no treatment event)
    """

    def __init__(self, output_path: str | None = None) -> None:
        """Initialize the treatment indicator processor.

        Args:
            output_path: Optional path to save DiD panel CSV
        """
        super().__init__(
            "treatment_indicator",
            "Add treatment indicators to tract-level rental panel for DiD analysis",
        )
        self.required_data = ["tract_rental_panel", "tract_prohibition_dates"]
        self.output_path = output_path or "/project/output/did_panel_data.csv"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Add treatment indicators to the rental panel.

        Required context keys:
            - tract_rental_panel: DataFrame with (tract_geoid, month, rental_price)
            - tract_prohibition_dates: DataFrame with (tract_geoid, first_prohibition_date, building_count)

        Returns:
            Dictionary with 'did_panel' containing a DataFrame with columns:
            - tract_geoid: Census tract GEOID
            - month: datetime of the observation
            - rental_price: rental price for that tract-month
            - treated: 0 if pre-treatment or never-treated, 1 if post-treatment
            - months_since_treatment: relative time (negative before, 0 at, positive after treatment)
            - first_prohibition_date: treatment date (NaT for never-treated)
        """
        # Get inputs from context
        panel = context["tract_rental_panel"].copy()
        treatment_dates = context["tract_prohibition_dates"]

        logger.info("Adding treatment indicators to tract-level rental panel...")
        logger.info("  Input panel observations: %d", len(panel))
        logger.info("  Tracts in panel: %d", panel["tract_geoid"].nunique())
        logger.info("  Treated tracts available: %d", len(treatment_dates))

        # Step 1: Merge panel with treatment dates
        # Use left join to keep all tract-months, including never-treated tracts
        merged = panel.merge(
            treatment_dates[["tract_geoid", "first_prohibition_date"]],
            on="tract_geoid",
            how="left",
        )

        # Ensure dates are datetime
        merged["month"] = pd.to_datetime(merged["month"])
        merged["first_prohibition_date"] = pd.to_datetime(
            merged["first_prohibition_date"]
        )

        # Step 2: Create treatment indicator
        # treated = 1 if month >= first_prohibition_date, else 0
        # For never-treated tracts (NaT date), comparison returns False → 0
        merged["treated"] = (
            merged["month"] >= merged["first_prohibition_date"]
        ).astype(int)

        # Step 3: Create relative time (months since treatment)
        # This is used for event study analysis
        # For never-treated tracts, this will be NaN
        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["first_prohibition_date"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)

        # Sort by tract and month
        merged = merged.sort_values(["tract_geoid", "month"]).reset_index(drop=True)

        # Log summary statistics
        n_tracts = merged["tract_geoid"].nunique()
        n_treated_tracts = merged[merged["first_prohibition_date"].notna()][
            "tract_geoid"
        ].nunique()
        n_never_treated = n_tracts - n_treated_tracts
        n_treated_obs = merged["treated"].sum()
        n_control_obs = len(merged) - n_treated_obs

        logger.info("DiD panel created successfully:")
        logger.info("  Total tracts: %d", n_tracts)
        logger.info("  Treated tracts: %d", n_treated_tracts)
        logger.info("  Never-treated tracts (pure control): %d", n_never_treated)
        logger.info("  Treated observations: %d", n_treated_obs)
        logger.info("  Control observations: %d", n_control_obs)
        logger.info(
            "  Months since treatment range: %d to %d",
            int(merged["months_since_treatment"].min()),
            int(merged["months_since_treatment"].max()),
        )

        # Validate treatment indicator logic
        self._validate_treatment_indicator(merged)

        # Save to CSV
        output_file = Path(self.output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(output_file, index=False)
        logger.info("  Saved DiD panel to: %s", output_file)

        return {"did_panel": merged}

    def _validate_treatment_indicator(self, df: pd.DataFrame) -> None:
        """Validate that treatment indicators are correctly assigned.

        Args:
            df: DiD panel DataFrame

        Raises:
            ValueError: If validation fails
        """
        # Check 1: Never-treated tracts should have treated=0 always
        never_treated = df[df["first_prohibition_date"].isna()]
        if len(never_treated) > 0:
            if not (never_treated["treated"] == 0).all():
                raise ValueError(
                    "Never-treated tracts should have treated=0 for all periods"
                )
            logger.info("  Validation passed: Never-treated tracts have treated=0")

        # Check 2: Treated tracts should switch from 0 to 1 at the right time
        treated_tracts = df[df["first_prohibition_date"].notna()]
        if len(treated_tracts) > 0:
            # Sample a few tracts for detailed validation
            sample_tracts = treated_tracts["tract_geoid"].drop_duplicates().head(5)

            for tract_id in sample_tracts:
                tract_data = df[df["tract_geoid"] == tract_id].copy()
                prohibition_date = tract_data["first_prohibition_date"].iloc[0]

                # Check that treated=0 before treatment and treated=1 after
                pre_treatment = tract_data[tract_data["month"] < prohibition_date]
                post_treatment = tract_data[tract_data["month"] >= prohibition_date]

                if len(pre_treatment) > 0:
                    if not (pre_treatment["treated"] == 0).all():
                        raise ValueError(
                            f"Tract {tract_id}: should have treated=0 before {prohibition_date}"
                        )

                if len(post_treatment) > 0:
                    if not (post_treatment["treated"] == 1).all():
                        raise ValueError(
                            f"Tract {tract_id}: should have treated=1 after {prohibition_date}"
                        )

            logger.info("  Validation passed: Treatment switches at correct time")

        # Check 3: months_since_treatment should be 0 at treatment month
        at_treatment = df[df["months_since_treatment"] == 0]
        if len(at_treatment) > 0:
            if not (at_treatment["treated"] == 1).all():
                raise ValueError(
                    "Observations at treatment month should have treated=1"
                )
            logger.info(
                "  Validation passed: months_since_treatment=0 aligned with treatment"
            )
