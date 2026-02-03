"""Treatment indicator processor.

This module contains two processors:
1. PointsToTractProcessor - Converts STR prohibition points to tract-level data
2. TreatmentIndicatorProcessor - Creates treatment indicators for DiD analysis
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class PointsToTractProcessor(DataProcessor):
    """STR prohibition points to tract aggregation processor.

    Performs spatial join (points within tracts) and aggregates by tract_geoid
    with application_id count and prohibition_date min/max.
    """

    def __init__(
        self,
        input_key: str = "str_prohibition_data",
        output_key: str = "str_tract_data",
        aggregate_columns: dict[str, list[str]] | None = None,
        calculate_density: bool = True,
        output_dir: str | None = None,
    ) -> None:
        """Initialize the points to tract processor.

        Args:
            input_key: Key for point data in context
            output_key: Key for output tract data in context
            aggregate_columns: Columns to aggregate (default: {"prohibition_date": ["min", "max"]})
            calculate_density: Whether to calculate density per km²
            output_dir: Optional directory to save output CSV
        """
        super().__init__(
            "points_to_tract_str",
            "Aggregate STR prohibition points to census tract level",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.aggregate_columns = aggregate_columns or {"prohibition_date": ["min", "max"]}
        self.calculate_density = calculate_density
        self.output_dir = Path(output_dir) if output_dir is not None else None

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation."""
        # Get data from context
        point_data = context[self.input_key]
        tract_boundaries = context["tract_boundaries"]

        logger.info("Aggregating STR prohibition points to tracts...")
        logger.info("Input points: %d", len(point_data))

        # Step 1: Ensure both datasets are in same CRS
        if point_data.crs != tract_boundaries.crs:
            point_data = point_data.to_crs(tract_boundaries.crs)

        # Step 2: Spatial join - which tract is each point in?
        points_with_tract = gpd.sjoin(
            point_data,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        logger.info(
            "Points matched to tracts: %d",
            points_with_tract["tract_geoid"].notna().sum(),
        )

        # Step 3: Aggregate by tract
        # Build aggregation dictionary
        agg_dict = {}

        # Count application_id (or use first column if not available)
        if "application_id" in points_with_tract.columns:
            agg_dict["application_id"] = "count"
        else:
            # Use first available column for counting
            agg_dict[points_with_tract.columns[0]] = "count"

        # Add custom aggregations (prohibition_date min/max)
        for col, funcs in self.aggregate_columns.items():
            if col in points_with_tract.columns:
                if isinstance(funcs, list):
                    for func in funcs:
                        agg_dict[col] = func
                else:
                    agg_dict[col] = funcs

        # Perform aggregation
        tract_agg = points_with_tract.groupby("tract_geoid").agg(agg_dict).reset_index()

        # Flatten MultiIndex columns if they exist
        if isinstance(tract_agg.columns, pd.MultiIndex):
            tract_agg.columns = [
                "_".join(col).strip() if col[1] else col[0]
                for col in tract_agg.columns.to_numpy()
            ]

        # Rename count column
        if "application_id_count" in tract_agg.columns:
            tract_agg = tract_agg.rename(columns={"application_id_count": "str_prohibition_count"})
        elif "application_id" in tract_agg.columns:
            tract_agg = tract_agg.rename(columns={"application_id": "str_prohibition_count"})

        # Step 4: Join with tract geometries
        tract_data = tract_boundaries[["tract_geoid", "geometry"]].merge(
            tract_agg, on="tract_geoid", how="left"
        )

        # Fill NaN counts with 0 (tracts with no points)
        tract_data["str_prohibition_count"] = tract_data["str_prohibition_count"].fillna(0)

        # Step 5: Calculate density if requested
        if self.calculate_density:
            # Convert to projected CRS for accurate area calculation
            tract_projected = tract_data.to_crs("EPSG:32616")  # UTM Zone 16N
            tract_projected["area_km2"] = tract_projected.geometry.area / 1_000_000

            # Calculate density
            tract_projected["str_prohibition_density"] = (
                tract_projected["str_prohibition_count"] / tract_projected["area_km2"]
            )

            # Copy calculated columns back to original CRS
            tract_data["area_km2"] = tract_projected["area_km2"].to_numpy()
            tract_data["str_prohibition_density"] = tract_projected[
                "str_prohibition_density"
            ].to_numpy()

        # Convert to GeoDataFrame
        tract_data = gpd.GeoDataFrame(
            tract_data, geometry="geometry", crs=tract_boundaries.crs
        )

        logger.info("Aggregated to %d tracts", len(tract_data))
        logger.info(
            "Tracts with prohibitions: %d",
            (tract_data["str_prohibition_count"] > 0).sum(),
        )

        # Optional: Save to CSV
        if self.output_dir is not None:
            output_path = self.output_dir / "tract_prohibition_dates.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Drop geometry for CSV
            tract_data.drop(columns=["geometry"]).to_csv(output_path, index=False)
            logger.info("Tract prohibition dates saved to: %s", output_path)

        return {
            self.output_key: tract_data,
            f"{self.output_key}_summary": {
                "total_tracts": len(tract_data),
                "tracts_with_prohibitions": (tract_data["str_prohibition_count"] > 0).sum(),
                "total_prohibitions": int(tract_data["str_prohibition_count"].sum()),
            },
        }


class TreatmentIndicatorProcessor(DataProcessor):
    """Treatment indicator processor.

    Reads str_tract_data and tract_panel_data from context.
    Creates treatment indicators for difference-in-differences analysis.
    """

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
        # Keep only treated tracts (building_count != 0)
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
        # Fix: Compare at year-month level, not exact date
        # When panel month is 2016-08-01 and first_prohibition_date is 2016-08-08,
        # the treatment should occur in month 2016-08
        logger.info("Creating treatment indicator...")
        
        # Convert to year-month periods for comparison
        merged["month_period"] = merged["month"].dt.to_period("M")
        merged["first_prohibition_period"] = merged["first_prohibition_date"].dt.to_period("M")
        
        # Treated = 1 if month >= first_prohibition_date at year-month level
        merged["treated"] = (
            merged["month_period"] >= merged["first_prohibition_period"]
        ).astype(int)
        
        # Handle never-treated tracts (NaN first_prohibition_date)
        merged.loc[merged["first_prohibition_date"].isna(), "treated"] = 0
        
        # Calculate months_since_treatment
        # For treated tracts, calculate difference; never-treated remain NaN
        merged["months_since_treatment"] = (
            (merged["month"].dt.year - merged["first_prohibition_date"].dt.year) * 12
            + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)
        )
        # Set to NaN for never-treated tracts
        merged.loc[merged["first_prohibition_date"].isna(), "months_since_treatment"] = pd.NA

        # Drop temporary period columns
        merged = merged.drop(columns=["month_period", "first_prohibition_period"])

        # Output the structured data
        if self.output_dir is not None:
            # Save tract prohibition dates
            tract_prohibition_path = self.output_dir / "tract_prohibition_dates.csv"
            tract_prohibition_path.parent.mkdir(parents=True, exist_ok=True)
            str_tract_data.drop(columns=["geometry"]).to_csv(
                tract_prohibition_path, index=False
            )
            logger.info("Tract prohibition dates saved to: %s", tract_prohibition_path)
            
            # Save DiD panel data
            did_panel_path = self.output_dir / "did_panel_data.csv"
            did_panel_path.parent.mkdir(parents=True, exist_ok=True)
            merged.to_csv(did_panel_path, index=False)
            logger.info("DiD panel data saved to: %s", did_panel_path)

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
        # Fix: Check both year AND month
        treated_tracts = did_panel[did_panel["first_prohibition_date"].notna()]
        for tract_id, group in treated_tracts.groupby("tract_geoid"):
            first_treated_month = group.loc[group["treated"] == 1, "month"].min()
            prohibition_date = group["first_prohibition_date"].iloc[0]
            if pd.isna(first_treated_month):
                continue  # Skip if no treated months found
            # Check both year and month
            if (
                first_treated_month.year != prohibition_date.year
                or first_treated_month.month != prohibition_date.month
            ):
                raise ValueError(
                    f"Mismatch for {tract_id}: "
                    f"first_treated_month={first_treated_month}, "
                    f"prohibition_date={prohibition_date}"
                )
