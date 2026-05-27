"""ZIP code to census tract crosswalk processor.

This module creates a crosswalk mapping ZIP codes to census tracts with
area-based weights, without requiring rental data.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)

COVERAGE_HIGH_SHARE = 0.95
COVERAGE_MED_SHARE = 0.50


class ZipTractCrosswalkProcessor(DataProcessor):
    """Create a crosswalk mapping ZIP codes to census tracts.

    This processor:
    1. Performs spatial intersection between ZIP and tract boundaries
    2. Calculates intersection areas for each ZIP-tract pair
    3. Returns a crosswalk table with area weights

    Unlike ZipToTractProcessor, this does NOT require rental data -
    it only needs the geographic boundaries to create the crosswalk.
    """

    def __init__(self, projected_crs: str = "EPSG:3435") -> None:
        """Initialize the ZIP-tract crosswalk processor."""
        super().__init__(
            "zip_tract_crosswalk",
            "Create ZIP code to census tract crosswalk with area weights",
        )
        self.required_data = ["zip_boundaries", "tract_boundaries"]
        self.projected_crs = projected_crs

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create the ZIP-tract crosswalk.

        Required context keys:
            - zip_boundaries: GeoDataFrame with ZIP code geometries
            - tract_boundaries: GeoDataFrame with census tract geometries

        Returns:
            Dictionary with 'zip_to_tract_crosswalk' containing a DataFrame with:
            - zip_code: ZIP code
            - tract_geoid: Census tract GEOID
            - intersection_area: Area of intersection (in CRS units)
        """
        zip_boundaries = context["zip_boundaries"]
        tract_boundaries = context["tract_boundaries"]

        logger.info("Creating ZIP-to-tract crosswalk...")
        logger.info("  ZIP codes: %d", len(zip_boundaries))
        logger.info("  Census tracts: %d", len(tract_boundaries))

        # Use a projected CRS for area calculations; degrees are not valid area units.
        zip_projected = zip_boundaries.to_crs(self.projected_crs)
        tract_projected = tract_boundaries.to_crs(self.projected_crs)

        # Perform spatial join to find intersecting pairs
        spatial_join = gpd.sjoin(
            zip_projected,
            tract_projected[["tract_geoid", "geometry"]],
            how="inner",
            predicate="intersects",
        )

        logger.info("  Found %d ZIP-tract intersections", len(spatial_join))

        # Calculate intersection areas for proper weighting
        intersection_data = []

        for _, row in spatial_join.iterrows():
            zip_geom = row.geometry
            tract_idx = row.get("index_right")

            if tract_idx is not None and tract_idx in tract_projected.index:
                tract_geom = tract_projected.loc[tract_idx, "geometry"]
                intersection = zip_geom.intersection(tract_geom)
                intersection_area = intersection.area

                if intersection_area > 0:
                    intersection_data.append(
                        {
                            "zip_code": row["zip_code"],
                            "tract_geoid": row["tract_geoid"],
                            "intersection_area": intersection_area,
                        }
                    )

        # Create crosswalk DataFrame
        crosswalk = pd.DataFrame(intersection_data)

        tract_areas = tract_projected[["tract_geoid", "geometry"]].copy()
        tract_areas["tract_area"] = tract_areas.geometry.area
        crosswalk = crosswalk.merge(
            tract_areas[["tract_geoid", "tract_area"]],
            on="tract_geoid",
            how="left",
        )
        crosswalk["zip_area_share"] = crosswalk.groupby("zip_code")[
            "intersection_area"
        ].transform(lambda x: x / x.sum())
        crosswalk["tract_area_share"] = (
            crosswalk["intersection_area"] / crosswalk["tract_area"]
        )

        tract_coverage = (
            crosswalk.groupby("tract_geoid")
            .agg(
                tract_coverage_share=("tract_area_share", "sum"),
                n_overlapping_zips=("zip_code", "nunique"),
            )
            .reset_index()
        )
        crosswalk = crosswalk.merge(
            tract_coverage,
            on="tract_geoid",
            how="left",
        )

        # Sort by zip_code and intersection_area (largest first)
        crosswalk = crosswalk.sort_values(
            ["zip_code", "intersection_area"], ascending=[True, False]
        ).reset_index(drop=True)

        # Log statistics
        n_zips = crosswalk["zip_code"].nunique()
        n_tracts = crosswalk["tract_geoid"].nunique()
        avg_tracts_per_zip = len(crosswalk) / n_zips if n_zips > 0 else 0
        coverage_summary = tract_coverage["tract_coverage_share"]
        n_tracts_95 = int((coverage_summary >= COVERAGE_HIGH_SHARE).sum())
        n_tracts_50 = int((coverage_summary >= COVERAGE_MED_SHARE).sum())

        logger.info("Crosswalk created successfully:")
        logger.info("  ZIP codes in crosswalk: %d", n_zips)
        logger.info("  Tracts in crosswalk: %d", n_tracts)
        logger.info("  Total ZIP-tract pairs: %d", len(crosswalk))
        logger.info("  Avg tracts per ZIP: %.1f", avg_tracts_per_zip)
        logger.info(
            "  Tract coverage by Chicago ZIP polygons: >=95%% for %d tracts, >=50%% for %d tracts",
            n_tracts_95,
            n_tracts_50,
        )

        return {
            "zip_to_tract_crosswalk": crosswalk,
            "crosswalk_diagnostics": {
                "projected_crs": self.projected_crs,
                "n_zip_codes": n_zips,
                "n_tracts": n_tracts,
                "n_zip_tract_pairs": int(len(crosswalk)),
                "avg_tracts_per_zip": float(avg_tracts_per_zip),
                "tracts_with_coverage_ge_95pct": n_tracts_95,
                "tracts_with_coverage_ge_50pct": n_tracts_50,
                "tracts_with_coverage_lt_50pct": int(
                    (coverage_summary < COVERAGE_MED_SHARE).sum()
                ),
            },
            "crosswalk_tract_coverage": tract_coverage,
        }
