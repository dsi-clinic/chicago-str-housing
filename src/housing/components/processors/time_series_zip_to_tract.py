"""Time series ZIP to tract processor for DiD analysis.

This module converts ZIP code-level panel data to census tract-level panel data
using area-weighted interpolation from a pre-computed crosswalk.
"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Convert ZIP-level rental panel to tract-level panel.

    This processor:
    1. Takes ZIP-level panel data (zip_code, month, rental_price)
    2. Uses a crosswalk to map ZIPs to tracts with area weights
    3. Calculates area-weighted average rental prices per tract per month
    4. Returns tract-level panel data (tract_geoid, month, rental_price)

    The crosswalk provides intersection areas between ZIPs and tracts.
    We normalize these to weights (proportion of ZIP area in each tract)
    and use them to allocate rental prices to tracts.
    """

    def __init__(self) -> None:
        """Initialize the time series ZIP to tract processor."""
        super().__init__(
            "zip_to_tract_panel",
            "Convert ZIP-level rental panel to tract-level panel",
        )
        self.required_data = ["rental_panel_data", "zip_to_tract_crosswalk"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform area-weighted conversion from ZIP to tract level.

        Required context keys:
            - rental_panel_data: DataFrame with (zip_code, month, rental_price)
            - zip_to_tract_crosswalk: DataFrame with (zip_code, tract_geoid, intersection_area)

        Returns:
            Dictionary with 'tract_rental_panel' containing a DataFrame with columns:
            - tract_geoid: Census tract GEOID
            - month: datetime of the observation
            - rental_price: area-weighted rental price for that tract-month
        """
        # Get inputs from context
        zip_panel = context["rental_panel_data"]
        crosswalk = context["zip_to_tract_crosswalk"].copy()

        logger.info("Converting ZIP-level panel to tract-level panel...")
        logger.info("  Input ZIP panel: %d observations", len(zip_panel))
        logger.info("  Crosswalk entries: %d ZIP-tract pairs", len(crosswalk))

        # Step 1: Normalize crosswalk weights
        # Weight = proportion of ZIP's area that overlaps with each tract
        crosswalk["weight"] = crosswalk.groupby("zip_code")[
            "intersection_area"
        ].transform(lambda x: x / x.sum())

        # Log crosswalk statistics
        n_zips_crosswalk = crosswalk["zip_code"].nunique()
        n_tracts_crosswalk = crosswalk["tract_geoid"].nunique()
        logger.info(
            "  Crosswalk covers %d ZIPs → %d tracts",
            n_zips_crosswalk,
            n_tracts_crosswalk,
        )

        # Step 2: Merge panel data with crosswalk
        # Each ZIP-month observation gets expanded to multiple rows (one per overlapping tract)
        merged = zip_panel.merge(
            crosswalk[["zip_code", "tract_geoid", "weight"]],
            on="zip_code",
            how="inner",
        )

        # Check for ZIPs that didn't match
        n_zips_panel = zip_panel["zip_code"].nunique()
        n_zips_matched = merged["zip_code"].nunique()
        if n_zips_matched < n_zips_panel:
            logger.warning(
                "  %d ZIPs in panel not found in crosswalk (dropped)",
                n_zips_panel - n_zips_matched,
            )

        # Step 3: Calculate weighted rental prices
        merged["weighted_rent"] = merged["rental_price"] * merged["weight"]

        # Step 4: Aggregate to tract level for each month
        tract_panel = (
            merged.groupby(["tract_geoid", "month"])
            .agg(
                {
                    "weighted_rent": "sum",
                    "weight": "sum",  # Total weight for normalization
                }
            )
            .reset_index()
        )

        # Step 5: Normalize to get tract-level rental price
        # This accounts for partial coverage (some ZIPs may not have data)
        tract_panel["rental_price"] = (
            tract_panel["weighted_rent"] / tract_panel["weight"]
        )

        # Clean up intermediate columns
        tract_panel = tract_panel[["tract_geoid", "month", "rental_price"]]

        # Sort by tract and month
        tract_panel = tract_panel.sort_values(["tract_geoid", "month"]).reset_index(
            drop=True
        )

        # Log summary statistics
        n_tracts = tract_panel["tract_geoid"].nunique()
        n_months = tract_panel["month"].nunique()
        n_obs = len(tract_panel)

        logger.info("Tract-level panel created successfully:")
        logger.info("  Unique tracts: %d", n_tracts)
        logger.info("  Unique months: %d", n_months)
        logger.info("  Total observations: %d", n_obs)
        logger.info(
            "  Rental price range: $%.0f - $%.0f",
            tract_panel["rental_price"].min(),
            tract_panel["rental_price"].max(),
        )
        logger.info(
            "  Mean rental price: $%.0f",
            tract_panel["rental_price"].mean(),
        )

        # Check for balanced panel
        expected_obs = n_tracts * n_months
        if n_obs < expected_obs:
            logger.warning(
                "  Panel is unbalanced: %d observations vs %d expected (tracts × months)",
                n_obs,
                expected_obs,
            )

        return {"tract_rental_panel": tract_panel}
