"""Treatment indicator processor.

This processor creates a treatment indicator for each tract based on the prohibition dates.
"""

import logging
from pathlib import Path
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Treatment indicator processor."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the treatment indicator processor."""
        super().__init__(
            "treatment_indicator", "Create a treatment indicator for each tract."
        )
        self.output_dir = Path(output_dir) if output_dir is not None else None

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the treatment indicator processor."""
        # Get the data from the context
        str_tract_data = context["str_tract_data"]
        tract_panel_data = context["tract_panel_data"]

        # Step 1: Structure the STR tract data for merging
        logger.info("Structuring STR tract data for merging...")
        str_tract_data = str_tract_data.rename(
            columns={
                "prohibition_date_min": "first_prohibition_date",
                "str_prohibition_count": "building_count",
            }
        )
        str_tract_data = str_tract_data[str_tract_data["building_count"] != 0]
        str_tract_data = str_tract_data.reset_index(drop=True)

        # Step 2: Merge the STR tract data with the tract panel data
        logger.info("Merging STR tract data with tract panel data...")
        merged = tract_panel_data.merge(
            str_tract_data[["tract_geoid", "first_prohibition_date", "building_count"]],
            on="tract_geoid",
            how="left",
        )

        # Step 3: Create treatment indicator
        logger.info("Creating treatment indicator...")
        merged["treated"] = (
            merged["month"] >= merged["first_prohibition_date"]
        ).astype(int)
        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["first_prohibition_date"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)

        # Output the structured STR tract data
        if self.output_dir is not None:
            output_path = Path(self.output_dir) / "tract_prohibition_dates.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            str_tract_data.to_csv(output_path, index=False)
            output_path = Path(self.output_dir) / "did_panel_data.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            merged.to_csv(output_path, index=False)
            logger.info("Tract prohibition dates saved to: %s", output_path)

        return {"did_panel": merged}

    def run_validation(self, context: dict[str, Any]) -> None:
        """Run validation on the treatment indicator."""
        did_panel = context["did_panel"]

        # 1. Check structure
        print(did_panel.columns.tolist())
        # Expected: ['tract_geoid', 'month', 'rental_price', 'first_prohibition_date',
        #            'treated', 'months_since_treatment']

        # 2. Verify treated indicator
        # Pick a tract you know is treated and check the switch point
        tract = "17031010100"
        print(
            did_panel[did_panel["tract_geoid"] == tract][
                ["month", "treated", "months_since_treatment"]
            ].head(20)
        )

        # 3. Count treated vs control
        print(did_panel.groupby("treated")["tract_geoid"].nunique())

        # 4. Check never-treated tracts have treated=0 always
        never_treated = did_panel[did_panel["first_prohibition_date"].isna()]
        if not (never_treated["treated"] == 0).all():
            raise ValueError("Never-treated should have treated=0")

        # 5. Check treated tracts switch at the right time
        treated_tracts = did_panel[did_panel["first_prohibition_date"].notna()]
        for tract_id, group in treated_tracts.groupby("tract_geoid"):
            first_treated_month = group.loc[group["treated"] == 1, "month"].min()
            prohibition_date = group["first_prohibition_date"].iloc[0]
            if first_treated_month.month != prohibition_date.month:
                raise ValueError(f"Mismatch for {tract_id}")
