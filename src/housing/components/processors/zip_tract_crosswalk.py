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


class ZipTractCrosswalkProcessor(DataProcessor):
    """Create a crosswalk mapping ZIP codes to census tracts.

    This processor:
    1. Performs spatial intersection between ZIP and tract boundaries
    2. Calculates intersection areas for each ZIP-tract pair
    3. Returns a crosswalk table with area weights

    Unlike ZipToTractProcessor, this does NOT require rental data -
    it only needs the geographic boundaries to create the crosswalk.
    """

    def __init__(self) -> None:
        """Initialize the ZIP-tract crosswalk processor."""
        super().__init__(
            "zip_tract_crosswalk",
            "Create ZIP code to census tract crosswalk with area weights",
        )
        self.required_data = ["zip_boundaries", "tract_boundaries"]

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

        # Ensure same CRS for spatial operations
        if zip_boundaries.crs != tract_boundaries.crs:
            tract_boundaries = tract_boundaries.to_crs(zip_boundaries.crs)

        # Perform spatial join to find intersecting pairs
        spatial_join = gpd.sjoin(
            zip_boundaries,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="inner",
            predicate="intersects",
        )

        logger.info("  Found %d ZIP-tract intersections", len(spatial_join))

        # Calculate intersection areas for proper weighting
        intersection_data = []

        for _, row in spatial_join.iterrows():
            zip_geom = row.geometry
            tract_idx = row.get("index_right")

            if tract_idx is not None and tract_idx in tract_boundaries.index:
                tract_geom = tract_boundaries.loc[tract_idx, "geometry"]
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

        # Sort by zip_code and intersection_area (largest first)
        crosswalk = crosswalk.sort_values(
            ["zip_code", "intersection_area"], ascending=[True, False]
        ).reset_index(drop=True)

        # Log statistics
        n_zips = crosswalk["zip_code"].nunique()
        n_tracts = crosswalk["tract_geoid"].nunique()
        avg_tracts_per_zip = len(crosswalk) / n_zips if n_zips > 0 else 0

        logger.info("Crosswalk created successfully:")
        logger.info("  ZIP codes in crosswalk: %d", n_zips)
        logger.info("  Tracts in crosswalk: %d", n_tracts)
        logger.info("  Total ZIP-tract pairs: %d", len(crosswalk))
        logger.info("  Avg tracts per ZIP: %.1f", avg_tracts_per_zip)

        return {"zip_to_tract_crosswalk": crosswalk}
