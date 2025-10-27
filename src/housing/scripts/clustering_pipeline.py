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
from typing import Any

from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd

from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult
from pipeline.base import PipelineComponent
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

load_dotenv()

class TractDataMerger(PipelineComponent):
    """Merge all housing data at the census tract level for clustering analysis."""
    
    def __init__(self) -> None:
        """Initialize the tract data merger."""
        super().__init__(
            name="tract_data_merger",
            description="Merge all housing data at census tract level"
        )
        self.required_data = [
            "tract_boundaries",
            "tract_rental_data", 
            "airbnb_tract_data",
            "str_tract_data",
            "census_data"
        ]
        self.output_data = ["clustering_data"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge all tract-level data for clustering analysis."""
        logger.info("Merging all housing data at census tract level")
        
        # Get tract boundaries as base
        tract_boundaries = context["tract_boundaries"]
        logger.info("Starting with %d census tracts", len(tract_boundaries))
        
        # Start with tract boundaries and add tract_id for merging
        merged_data = tract_boundaries.copy()
        merged_data["tract_id"] = merged_data["tract_geoid"]
        
        # Merge rental data - SKIP FOR NOW DUE TO PANDAS ISSUE
        logger.info("Skipping rental data merge due to pandas column selection issue")
        # TODO: Fix rental data merge
        
        # Merge Airbnb data - SIMPLIFIED APPROACH
        if "airbnb_tract_data" in context:
            airbnb_data = context["airbnb_tract_data"]
            logger.info("Merging Airbnb data: %d tracts", len(airbnb_data))
            
            # Simple merge - just merge the whole dataframe and rename later
            merged_data = merged_data.merge(
                airbnb_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_airbnb")
            )
            
            # Rename Airbnb columns
            if "point_count" in merged_data.columns:
                merged_data = merged_data.rename(columns={"point_count": "airbnb_count"})
            if "point_density" in merged_data.columns:
                merged_data = merged_data.rename(columns={"point_density": "airbnb_density"})
            if "price_numeric_mean" in merged_data.columns:
                merged_data = merged_data.rename(columns={"price_numeric_mean": "airbnb_price_mean"})
            if "price_numeric_median" in merged_data.columns:
                merged_data = merged_data.rename(columns={"price_numeric_median": "airbnb_price_median"})
            
            # Drop duplicate geometry column if it exists
            if "geometry_airbnb" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_airbnb"])
        else:
            logger.warning("No Airbnb data found, skipping Airbnb merge")
        
        # Merge STR prohibition data - SIMPLIFIED APPROACH
        if "str_tract_data" in context:
            str_data = context["str_tract_data"]
            logger.info("Merging STR prohibition data: %d tracts", len(str_data))
            
            # Simple merge - just merge the whole dataframe and rename later
            merged_data = merged_data.merge(
                str_data,
                left_on="tract_id",
                right_on="tract_geoid",
                how="left",
                suffixes=("", "_str")
            )
            
            # Rename STR prohibition columns
            if "point_count" in merged_data.columns:
                merged_data = merged_data.rename(columns={"point_count": "str_prohibition_count"})
            if "point_density" in merged_data.columns:
                merged_data = merged_data.rename(columns={"point_density": "str_prohibition_density"})
            if "number_of_units_sum" in merged_data.columns:
                merged_data = merged_data.rename(columns={"number_of_units_sum": "str_prohibition_units_total"})
            if "number_of_units_mean" in merged_data.columns:
                merged_data = merged_data.rename(columns={"number_of_units_mean": "str_prohibition_units_mean"})
            
            # Drop duplicate geometry column if it exists
            if "geometry_str" in merged_data.columns:
                merged_data = merged_data.drop(columns=["geometry_str"])
        else:
            logger.warning("No STR prohibition data found, skipping STR merge")
        
        # Merge census data
        if "census_data" in context:
            census_data = context["census_data"]
            logger.info("Merging census data: %d tracts", len(census_data))
            
            # Rename columns to avoid conflicts
            census_cols = {
                "total_population": "census_population",
                "median_income": "census_median_income",
                "median_house_value": "census_median_house_value", 
                "median_age": "census_median_age",
                "pct_bachelor": "census_pct_bachelor"
            }
            census_data_renamed = census_data.rename(columns=census_cols)
            
            merged_data = merged_data.merge(
                census_data_renamed[["tract_id"] + list(census_cols.values())],
                left_on="tract_id",
                right_on="tract_id",
                how="left"
            )
        else:
            logger.warning("No census data found, skipping census merge")
        
        # Fill missing values with 0 for count/density columns
        count_columns = [
            "airbnb_count", "airbnb_density", "str_prohibition_count", 
            "str_prohibition_density", "str_prohibition_units_total"
        ]
        for col in count_columns:
            if col in merged_data.columns:
                merged_data[col] = merged_data[col].fillna(0)
        
        # Calculate population density (people per square km)
        if "census_population" in merged_data.columns:
            # Reproject to a projected CRS (meters) for accurate area calculation
            # Using Albers Equal Area Conic (EPSG:5070) which is good for US area calculations
            geometry_projected = merged_data.geometry.to_crs("EPSG:5070")
            # Convert area from square meters to square kilometers
            merged_data["area_sq_km"] = geometry_projected.area / 1_000_000
            merged_data["population_density"] = (
                merged_data["census_population"] / merged_data["area_sq_km"]
            ).fillna(0)
        
        # Clean up redundant columns
        merged_data = self._clean_columns(merged_data)
        
        # Log summary statistics
        self._log_merge_summary(merged_data)
        
        return {"clustering_data": merged_data}
    
    def _clean_columns(self, df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Remove redundant columns and keep only essential data for clustering."""
        logger.info("Cleaning up redundant columns")
        
        # Keep essential columns
        keep_columns = [
            "geometry",  # Always keep geometry
            "tract_id",  # Keep one tract identifier
            
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
            "str_prohibition_density",
            
            # Census data
            "census_population",
            "census_median_income",
            "census_median_house_value",
            "census_median_age",
            "census_pct_bachelor",
            
            # Calculated fields
            "area_sq_km",
            "population_density",
        ]
        
        # Filter to only columns that exist
        available_columns = [col for col in keep_columns if col in df.columns]
        
        # Keep additional census columns if needed for reference
        census_cols = ["GEOID", "NAME"]  # Keep original identifiers for reference
        
        # Combine and filter
        cols_to_keep = available_columns + [col for col in census_cols if col in df.columns]
        
        cleaned_df = df[cols_to_keep].copy()
        
        # Log what was removed
        removed_cols = set(df.columns) - set(cleaned_df.columns)
        if removed_cols:
            logger.info("Removed %d redundant columns: %s", len(removed_cols), 
                       sorted(list(removed_cols))[:10])  # Show first 10
        
        return cleaned_df
    
    def _log_merge_summary(self, df: gpd.GeoDataFrame) -> None:
        """Log summary statistics of merged data."""
        logger.info("Clustering Data Summary:")
        logger.info("  Total tracts: %d", len(df))
        
        # Count tracts with each type of data
        data_types = {
            "Rental data": "rental_price_mean",
            "Airbnb data": "airbnb_count", 
            "STR prohibition data": "str_prohibition_count",
            "Census data": "census_population"
        }
        
        for data_type, col in data_types.items():
            if col in df.columns:
                count = df[col].notna().sum()
                logger.info("  %s: %d tracts (%.1f%%)", 
                          data_type, count, 100 * count / len(df))
        
        # Log data ranges for key variables
        if "airbnb_density" in df.columns:
            airbnb_tracts = df[df["airbnb_density"] > 0]
            if len(airbnb_tracts) > 0:
                logger.info("  Airbnb density range: %.2f - %.2f listings/km²",
                          airbnb_tracts["airbnb_density"].min(),
                          airbnb_tracts["airbnb_density"].max())
        
        if "str_prohibition_density" in df.columns:
            str_tracts = df[df["str_prohibition_density"] > 0]
            if len(str_tracts) > 0:
                logger.info("  STR prohibition density range: %.2f - %.2f units/km²",
                          str_tracts["str_prohibition_density"].min(),
                          str_tracts["str_prohibition_density"].max())
        
        if "rental_price_mean" in df.columns:
            rental_tracts = df[df["rental_price_mean"].notna()]
            if len(rental_tracts) > 0:
                logger.info("  Rental price range: $%.0f - $%.0f",
                          rental_tracts["rental_price_mean"].min(),
                          rental_tracts["rental_price_mean"].max())
        
        if "census_median_income" in df.columns:
            income_tracts = df[df["census_median_income"].notna()]
            if len(income_tracts) > 0:
                logger.info("  Census median income range: $%.0f - $%.0f",
                          income_tracts["census_median_income"].min(),
                          income_tracts["census_median_income"].max())


def run_clustering_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the clustering data preparation pipeline."""
    logger.info("Running Housing Clustering Data Pipeline")
    logger.info("=" * 50)
    
    config = PipelineConfig()
    pipeline = Pipeline("Housing Clustering Data Pipeline", config=config)
    pipeline.load_config()
    
    # Step 1: Load all data sources
    logger.info("Step 1: Loading data sources")
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(AirbnbDataLoader())
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))
    
    # Step 2: Aggregate zip-level rental data to tracts
    logger.info("Step 2: Aggregating rental data to tracts")
    pipeline.register_component(ZipToTractProcessor())
    
    # Step 3: Aggregate STR prohibition points to tracts
    logger.info("Step 3: Aggregating STR prohibition data to tracts")
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
    
    # Step 4: Aggregate Airbnb points to tracts
    logger.info("Step 4: Aggregating Airbnb data to tracts")
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
    
    # Step 5: Merge all data at tract level
    logger.info("Step 5: Merging all data at tract level")
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
        logger.info("Successfully created clustering dataset with %d tracts", len(clustering_data))
        logger.info("Available columns: %s", list(clustering_data.columns))
        
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
        output_path = "/project/output/clustering_data.geojson"
        clustering_data.to_file(output_path, driver="GeoJSON")
        logger.info("Clustering data saved to: %s", output_path)
    else:
        logger.error("Failed to create clustering dataset")
