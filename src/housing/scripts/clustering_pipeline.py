"""Chicago Housing Clustering Pipeline."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from housing.components.loaders.affordable_development_data import (
    AffordableDataLoader,
)
from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.foreclosed_data import ForeclosedDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.affordable_development_points_to_tract import (
    AffordableToTractProcessor,
)
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.tract_data_merger import TractDataMerger
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)

load_dotenv()

# Base paths for input and output
PROJECT_ROOT = Path("/project")
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
CLUSTERING_DATA_OUTPUT = OUTPUT_DIR / "clustering_data.geojson"
CLUSTERING_DATA_SCALED_OUTPUT = OUTPUT_DIR / "clustering_data_scaled.csv"


def run_clustering_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the clustering data preparation pipeline."""
    pipeline = Pipeline("Housing Clustering Data Pipeline")

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
