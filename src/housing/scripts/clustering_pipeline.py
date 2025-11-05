"""Chicago Housing Clustering Pipeline.

This script loads and merges housing-related data at the census tract level
for clustering analysis. It combines:
- Airbnb density (listings per tract)
- Rental prices (aggregated from zip to tract)
- STR prohibition unit density (prohibited units per tract)
- Census demographics (median income, house value, age, education, population)
"""

import logging
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from housing.components.constants import MIN_TRACT_AREA_KM2, NO_DATA_MARKER
from housing.components.loaders.affordable_development_data import (
    AffordableDataLoader,
)
from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.foreclosed_data import ForeclosedDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.affordable_development_points_to_tract import (
    AffordableToTractProcessor,
)
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.spatial_interpolator import SpatialInterpolator
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.utils import standardize_data, winsorize
from pipeline import Pipeline, PipelineResult
from pipeline.base import PipelineComponent
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

load_dotenv()

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Base paths for input and output
PROJECT_ROOT = Path("/project")
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Output file paths
CLUSTERING_DATA_OUTPUT = OUTPUT_DIR / "clustering_data.geojson"
CLUSTERING_DATA_SCALED_OUTPUT = OUTPUT_DIR / "clustering_data_scaled.csv"


class TractDataMerger(PipelineComponent):
    """Merge all housing data at the census tract level for clustering analysis."""

    def __init__(self) -> None:
        """Initialize the tract data merger."""
        super().__init__(
            name="tract_data_merger",
            description="Merge all housing data at census tract level",
        )
        self.required_data = [
            "tract_boundaries",
            "tract_rental_data",
            "airbnb_tract_data",
            "str_tract_data",
            "census_data",
            "affordable_development_tract_data",
            "foreclosed_tract_data",
        ]
        self.output_data = [
            "clustering_data",
            "cluster_variables",
            "clustering_data_scaled",
        ]

    def _load_chicago_boundaries(self) -> gpd.GeoDataFrame | None:
        """Load Chicago city boundaries for clipping."""
        try:
            loader = CityBoundariesLoader()
            city_data = loader.execute({})
            return city_data["city_boundaries"]
        except Exception as e:
            logger.warning(
                "Could not load Chicago boundaries: %s. Skipping clipping.", e
            )
            return None

    def _filter_non_residential_tracts(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Filter out non-residential tracts like airports, industrial areas, etc."""
        # O'Hare Airport tract IDs
        ohare_tract_ids = ["17031980000", "17031760801", "17031760802", "17031760803"]

        initial_count = len(gdf)

        # Filter out O'Hare airport tracts by ID
        if "tract_geoid" in gdf.columns:
            filtered_gdf = gdf[~gdf["tract_geoid"].isin(ohare_tract_ids)].copy()
        elif "GEOID" in gdf.columns:
            filtered_gdf = gdf[~gdf["GEOID"].isin(ohare_tract_ids)].copy()
        else:
            # If we can't find tract ID column, skip filtering
            logger.warning("Could not find tract ID column for filtering")
            filtered_gdf = gdf.copy()

        removed_count = initial_count - len(filtered_gdf)
        if removed_count > 0:
            logger.info(
                "Filtered out %d non-residential tracts (O'Hare airport area)",
                removed_count,
            )

        return filtered_gdf

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge all tract-level data for clustering analysis."""
        # Get tract boundaries as base
        tract_boundaries = context["tract_boundaries"]

        # Filter to tracts whose centroids are within Chicago boundaries
        # This ensures we only keep tracts that are truly within Chicago, avoiding edge cases
        try:
            city_boundaries = self._load_chicago_boundaries()
            if city_boundaries is not None:
                # Ensure same CRS
                if tract_boundaries.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(tract_boundaries.crs)

                # Calculate centroids (use projected CRS for accuracy)
                tract_boundaries_projected = tract_boundaries.to_crs("EPSG:32616")
                centroids = tract_boundaries_projected.geometry.centroid.to_crs(
                    tract_boundaries.crs
                )

                # Create temporary GeoDataFrame with centroids for spatial join
                centroids_gdf = gpd.GeoDataFrame(
                    geometry=centroids,
                    index=tract_boundaries.index,
                    crs=tract_boundaries.crs,
                )

                # Spatial join to find which centroids are within Chicago
                tracts_within = gpd.sjoin(
                    centroids_gdf, city_boundaries, how="inner", predicate="within"
                )

                # Filter tract boundaries to only those whose centroids are within Chicago
                tract_boundaries = tract_boundaries.loc[tracts_within.index].copy()

                logger.info(
                    "Filtered to tracts with centroids within Chicago: %d tracts remaining",
                    len(tract_boundaries),
                )
        except Exception as e:
            logger.warning("Could not filter to Chicago boundaries: %s", e)

        # Filter out non-residential areas (airports, etc.)
        tract_boundaries = self._filter_non_residential_tracts(tract_boundaries)

        # Start with tract boundaries and add tract_id for merging
        merged_data = tract_boundaries.copy()
        merged_data["tract_id"] = merged_data["tract_geoid"]

        # Merge rental data
        if "tract_rental_data" in context:
            rental_data = context["tract_rental_data"]

            # Select only the columns we want (exclude geometry and tract_geoid to avoid conflicts)
            rental_cols = [
                col
                for col in rental_data.columns
                if col not in ["geometry", "tract_geoid"]
            ]

            # Simple merge - just merge the dataframe columns
            merged_data = merged_data.merge(
                rental_data[rental_cols + ["tract_geoid"]],
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
            )

            # Rename rental columns for clarity
            # Use area-weighted as the primary metric (more accurate when tracts span multiple zips)
            if "area_weighted_avg_rent" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"area_weighted_avg_rent": "rental_price_mean"}
                )
            if "min_rental_price" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"min_rental_price": "rental_price_min"}
                )
            if "max_rental_price" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"max_rental_price": "rental_price_max"}
                )

            # Drop the unweighted average as it's less accurate
            if "avg_rental_price" in merged_data.columns:
                merged_data = merged_data.drop(columns=["avg_rental_price"])

            # Drop duplicate tract_geoid from merge (we only need tract_id)
            if "tract_geoid_y" in merged_data.columns:
                merged_data = merged_data.drop(columns=["tract_geoid_y"])
            elif "tract_geoid_rental" in merged_data.columns:
                merged_data = merged_data.drop(columns=["tract_geoid_rental"])
        else:
            logger.warning("No rental data found, skipping rental merge")

        # Merge Airbnb data
        if "airbnb_tract_data" in context:
            airbnb_data = context["airbnb_tract_data"]

            merged_data = merged_data.merge(
                airbnb_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_airbnb"),
            )

            # Rename Airbnb price columns (use median for robustness)
            if "price_numeric_median" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"price_numeric_median": "airbnb_price_mean"}
                )
            if "price_numeric_mean" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"price_numeric_mean": "airbnb_price_median"}
                )

            # Drop duplicate geometry column if it exists
            if "geometry_airbnb" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_airbnb"])
        else:
            logger.warning("No Airbnb data found, skipping Airbnb merge")

        # Merge STR prohibition data
        if "str_tract_data" in context:
            str_data = context["str_tract_data"]

            merged_data = merged_data.merge(
                str_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_str"),
            )

            # Rename STR prohibition columns
            if "number_of_units_sum" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"number_of_units_sum": "str_prohibition_units_total"}
                )
            if "number_of_units_mean" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"number_of_units_mean": "str_prohibition_units_mean"}
                )

            # Drop duplicate geometry column if it exists
            if "geometry_str" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_str"])
        else:
            logger.warning("No STR prohibition data found, skipping STR merge")

        # Merge census data
        if "census_data" in context:
            census_data = context["census_data"]

            # Rename columns to avoid conflicts
            census_cols = {
                "total_population": "census_population",
                "median_income": "census_median_income",
                "median_house_value": "census_median_house_value",
                "median_age": "census_median_age",
                "pct_bachelor": "census_pct_bachelor",
                "pct_rented": "census_pct_rented",
            }
            census_data_renamed = census_data.rename(columns=census_cols)

            merged_data = merged_data.merge(
                census_data_renamed[["tract_id"] + list(census_cols.values())],
                left_on="tract_id",
                right_on="tract_id",
                how="left",
            )
        else:
            logger.warning("No census data found, skipping census merge")

        # Merge affordable development data
        if "affordable_development_tract_data" in context:
            affordable_data = context["affordable_development_tract_data"]

            merged_data = merged_data.merge(
                affordable_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_affordable"),
            )

            # Rename affordable development columns for clarity
            if "units_sum" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"units_sum": "affordable_units_total"}
                )
            if "units_mean" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={"units_mean": "affordable_units_mean"}
                )
            if "affordable_development_unit_density" in merged_data.columns:
                merged_data = merged_data.rename(
                    columns={
                        "affordable_development_unit_density": "affordable_unit_density"
                    }
                )

            # Drop duplicate geometry column if it exists
            if "geometry_affordable" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_affordable"])
        else:
            logger.warning(
                "No affordable development data found, skipping affordable merge"
            )

        # Merge foreclosed data
        if "foreclosed_tract_data" in context:
            foreclosed_data = context["foreclosed_tract_data"]

            merged_data = merged_data.merge(
                foreclosed_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_foreclosed"),
            )

            # Drop duplicate geometry column if it exists
            if "geometry_foreclosed" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_foreclosed"])
        else:
            logger.warning("No foreclosed data found, skipping foreclosed merge")

        # Calculate population density before interpolation (so it can be interpolated too)
        if "census_population" in merged_data.columns:
            # Reproject to a projected CRS (meters) for accurate area calculation
            # Using Albers Equal Area Conic (EPSG:5070) which is good for US area calculations
            geometry_projected = merged_data.geometry.to_crs("EPSG:5070")
            # Convert area from square meters to square kilometers
            merged_data["area_sq_km"] = geometry_projected.area / 1_000_000

            # Filter out tracts with very small area (likely data errors)
            small_area_mask = (
                merged_data["area_sq_km"] < MIN_TRACT_AREA_KM2
            )  # Less than 10 hectares
            if small_area_mask.any():
                logger.info(
                    "Found %d tracts with very small area (< %.2f km²), setting density to NaN",
                    small_area_mask.sum(),
                    MIN_TRACT_AREA_KM2,
                )

            # Calculate population density
            merged_data["population_density"] = (
                merged_data["census_population"] / merged_data["area_sq_km"]
            )

            # Calculate STR prohibition densities
            if "str_prohibition_count" in merged_data.columns:
                merged_data["str_prohibition_building_density"] = (
                    merged_data["str_prohibition_count"] / merged_data["area_sq_km"]
                )
                # Set density to NaN for very small areas
                merged_data.loc[small_area_mask, "str_prohibition_building_density"] = (
                    np.nan
                )

            if "str_prohibition_units_total" in merged_data.columns:
                merged_data["str_prohibition_units_density"] = (
                    merged_data["str_prohibition_units_total"]
                    / merged_data["area_sq_km"]
                )
                # Set density to NaN for very small areas
                merged_data.loc[small_area_mask, "str_prohibition_units_density"] = (
                    np.nan
                )

            # Set density to NaN for very small areas (keep as NaN for proper handling)
            merged_data.loc[small_area_mask, "population_density"] = np.nan

        # Interpolate missing values using spatial KNN (now includes population_density)
        context["merged_tract_data"] = merged_data
        interpolator = SpatialInterpolator(k_neighbors=5)
        context = interpolator.execute(context)
        merged_data = context["merged_tract_data"]

        # Winsorize density variables after interpolation to cap extreme outliers
        merged_data = winsorize(
            merged_data,
            "population_density",
            max_bound=50000,
            unit_name="people",
            logger=logger,
        )
        merged_data = winsorize(
            merged_data,
            "str_prohibition_units_density",
            unit_name="units",
            logger=logger,
        )
        merged_data = winsorize(
            merged_data, "foreclosed_density", unit_name="properties", logger=logger
        )

        # Fill missing values with 0 for count/density columns
        count_columns = [
            "airbnb_count",
            "airbnb_density",
            "str_prohibition_count",
            "str_prohibition_building_density",
            "str_prohibition_units_total",
            "str_prohibition_units_density",
            "affordable_development_density",
            "affordable_unit_density",
            "foreclosed_density",
        ]
        for col in count_columns:
            if col in merged_data.columns:
                merged_data[col] = merged_data[col].fillna(0)

        # Clean up redundant columns
        merged_data = self._clean_columns(merged_data)

        # Process data for clustering (handle missing values, select variables, standardize)
        merged_data, cluster_variables = self._prepare_clustering_data(merged_data)

        # Standardize the cluster variables
        cluster_data = merged_data[cluster_variables].copy()
        scaled_data = standardize_data(cluster_data)

        # Convert scaled data to DataFrame for easy saving
        scaled_df = pd.DataFrame(
            scaled_data, columns=cluster_variables, index=cluster_data.index
        )

        # Log summary statistics
        self._log_merge_summary(merged_data)

        logger.info(
            "Standardized %d variables for %d tracts",
            len(cluster_variables),
            len(merged_data),
        )

        return {
            "clustering_data": merged_data,
            "cluster_variables": cluster_variables,
            "clustering_data_scaled": scaled_df,
        }

    def _clean_columns(self, df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Remove redundant columns and keep only essential data for clustering."""
        # Keep essential columns
        keep_columns = [
            "geometry",  # Always keep geometry
            "tract_id",  # Keep one tract identifier
            # Rental data
            "rental_price_mean",  # Area-weighted average (most accurate)
            "rental_price_min",
            "rental_price_max",
            # Airbnb data
            "airbnb_count",
            "airbnb_price_mean",
            "airbnb_price_median",
            "price_numeric_min",
            "price_numeric_max",
            "airbnb_density",
            # STR prohibition data
            "str_prohibition_count",
            "str_prohibition_units_total",
            "str_prohibition_units_mean",
            "number_of_units_median",
            "str_prohibition_building_density",
            "str_prohibition_units_density",
            # Census data
            "census_population",
            "census_median_income",
            "census_median_house_value",
            "census_median_age",
            "census_pct_bachelor",
            "census_pct_rented",
            # Affordable development data
            "affordable_development_density",
            "affordable_unit_density",
            # Foreclosed data
            "foreclosed_density",
            # Calculated fields
            "area_sq_km",
            "population_density",
        ]

        # Filter to only columns that exist
        available_columns = [col for col in keep_columns if col in df.columns]

        # Keep additional census columns if needed for reference
        census_cols = ["GEOID", "NAME"]  # Keep original identifiers for reference

        # Combine and filter
        cols_to_keep = available_columns + [
            col for col in census_cols if col in df.columns
        ]

        cleaned_df = df[cols_to_keep].copy()

        # Log what was removed
        removed_cols = set(df.columns) - set(cleaned_df.columns)
        if removed_cols:
            logger.info("Removed %d redundant columns", len(removed_cols))

        return cleaned_df

    def _prepare_clustering_data(
        self, df: gpd.GeoDataFrame
    ) -> tuple[gpd.GeoDataFrame, list[str]]:
        """Prepare data for clustering analysis by handling missing values and selecting variables.

        Returns:
            Tuple of (cleaned GeoDataFrame, list of cluster variable names)
        """
        # Define clustering variables (same as in clustering_analysis.py)
        cluster_variables = [
            # Demographics
            "census_median_income",
            "census_median_age",
            "census_pct_bachelor",
            # Housing market
            "census_median_house_value",
            "census_pct_rented",
            "rental_price_mean",
            "airbnb_price_mean",
            # STR activity
            "airbnb_density",
            "str_prohibition_building_density",
            "str_prohibition_units_density",
            # Population
            "population_density",
            # Affordable and foreclosed housing
            "affordable_development_density",
            "affordable_unit_density",
            "foreclosed_density",
        ]

        # Filter to only variables that exist in the data
        available_cluster_vars = [var for var in cluster_variables if var in df.columns]
        logger.info("Selected %d clustering variables", len(available_cluster_vars))

        # Replace -9999 (no-data marker from GeoJSON) with NaN for clustering variables
        for col in available_cluster_vars:
            # Count how many no-data markers we're replacing
            no_data_count = (df[col] == NO_DATA_MARKER).sum()
            if no_data_count > 0:
                df[col] = df[col].replace(NO_DATA_MARKER, np.nan)

        # Check for missing data in clustering variables
        cluster_subset = df[available_cluster_vars].copy()
        missing_data_mask = cluster_subset.isna().any(axis=1)

        if missing_data_mask.any():
            missing_count = missing_data_mask.sum()
            logger.info(
                "Found %d tracts with missing clustering data (%.1f%%), removing them",
                missing_count,
                100 * missing_count / len(df),
            )

            # Log which variables are most problematic
            missing_by_var = cluster_subset.isna().sum().sort_values(ascending=False)
            problematic_vars = missing_by_var[missing_by_var > 0]
            if len(problematic_vars) > 0:
                logger.info("Variables with missing data:")
                for var in problematic_vars.head(3).index:
                    count = problematic_vars[var]
                    logger.info("  %s: %d tracts missing", var, count)

            # Remove tracts with missing clustering data
            cleaned_df = df[~missing_data_mask].copy()
        else:
            # No missing data, use the original dataframe
            cleaned_df = df.copy()

        logger.info(
            "Final clustering dataset: %d tracts with complete data", len(cleaned_df)
        )

        return cleaned_df, available_cluster_vars

    def _log_merge_summary(self, df: gpd.GeoDataFrame) -> None:
        """Log summary statistics of merged data."""
        logger.info("Clustering Data Summary:")
        logger.info("  Total tracts: %d", len(df))

        # Count tracts with each type of data (non-redundant)
        data_sources = {
            "Rental data": "rental_price_mean",
            "Airbnb data": "airbnb_density",
            "STR prohibition data": "str_prohibition_building_density",
            "Census data": "census_median_income",
            "Affordable development data": "affordable_development_density",
            "Foreclosed data": "foreclosed_density",
        }

        for data_type, col in data_sources.items():
            if col in df.columns:
                count = df[col].notna().sum()
                logger.info(
                    "  %s: %d tracts (%.1f%%)", data_type, count, 100 * count / len(df)
                )


def run_clustering_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the clustering data preparation pipeline."""
    config = PipelineConfig()
    pipeline = Pipeline("Housing Clustering Data Pipeline", config=config)
    pipeline.load_config()

    # Load all data sources
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(AirbnbDataLoader())
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))
    pipeline.register_component(AffordableDataLoader())
    pipeline.register_component(ForeclosedDataLoader())

    # Aggregate zip-level rental data to tracts
    pipeline.register_component(ZipToTractProcessor())

    # Aggregate STR prohibition points to tracts
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "number_of_units": ["sum", "mean", "median"],
            },
            calculate_density=True,
        )
    )

    # Aggregate Airbnb points to tracts
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="airbnb_data",
            output_key="airbnb_tract_data",
            id_column="id",
            aggregate_columns={
                "price_numeric": ["mean", "median", "min", "max"],
            },
            calculate_density=True,
        )
    )

    # Aggregate affordable development points to tracts
    pipeline.register_component(AffordableToTractProcessor())

    # Aggregate foreclosed points to tracts
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="foreclosed_data",
            output_key="foreclosed_tract_data",
            id_column="id",
            aggregate_columns={},
            calculate_density=True,
        )
    )

    # Merge all data at tract level
    merger = TractDataMerger()
    pipeline.register_component(merger)

    # Execute the pipeline
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logger.info("Chicago Housing Clustering Data Pipeline")
    logger.info("=" * 50)

    pipeline, results = run_clustering_pipeline()

    # Print final summary
    logger.info("\n" + "=" * 50)
    logger.info("Pipeline execution completed!")

    # Check if clustering data was created successfully
    if "clustering_data" in pipeline.context:
        clustering_data = pipeline.context["clustering_data"]
        logger.info(
            "Successfully created clustering dataset with %d tracts",
            len(clustering_data),
        )

        # Clean data types for GeoJSON export
        # GeoJSON doesn't support nullable integer types or NaN values
        for col in clustering_data.columns:
            if col != "geometry":
                # Convert nullable integer types to regular float
                if clustering_data[col].dtype.name == "Int64":
                    clustering_data[col] = clustering_data[col].astype("float64")
                # Replace NaN with -9999 (standard no-data value) for float columns
                if clustering_data[col].dtype.name == "float64":
                    clustering_data[col] = clustering_data[col].fillna(-9999)

        # Save the merged data for further analysis
        clustering_data.to_file(CLUSTERING_DATA_OUTPUT, driver="GeoJSON")
        logger.info("Clustering data saved to: %s", CLUSTERING_DATA_OUTPUT)

        # Save standardized data to CSV
        if "clustering_data_scaled" in pipeline.context:
            scaled_df = pipeline.context["clustering_data_scaled"]
            scaled_df.to_csv(CLUSTERING_DATA_SCALED_OUTPUT)
            logger.info("Saved standardized data to: %s", CLUSTERING_DATA_SCALED_OUTPUT)
    else:
        logger.error("Failed to create clustering dataset")
