"""Difference-in-Differences Time-Series Analysis Pipeline.

This script demonstrates the DiD analysis workflow:
1. Loading time-series rental data from csv file
2. Building a ZIP–tract crosswalk from boundaries (same approach as the CS pipeline)
3. Converting ZIP-level panel rents to tract level
4. Build DiD panel dataset with treatment variables
5. Analyze and visualize DiD data before experiment
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.tract_prohibition_dates import (
    TractProhibitionDatesProcessor,
)
from housing.components.processors.treatment_threshold import (
    TreatmentThresholdProcessor,
)
from housing.components.processors.zip_tract_crosswalk import ZipTractCrosswalkProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.treatment_map import TreatmentMapVisualizer
from pipeline import Pipeline, PipelineResult

load_dotenv()

logger = logging.getLogger(__name__)


def _default_output_dir() -> Path:
    """Directory for demo DiD outputs (CS pipeline uses ``output/did-cs``)."""
    data_root = Path(os.environ.get("DATA_DIR", "/project/data"))
    repo_root = Path(__file__).resolve().parents[3]
    if str(data_root).startswith("/project"):
        return Path("/project/output")
    return repo_root / "output" / "did-demo"


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate DiD time-series analysis of rental prices (aligned with CS crosswalk)."""
    logger.info("Running DiD Time-Series Analysis of Rental Prices")
    logger.info("=" * 70)

    out_dir = Path(os.environ.get("DID_PIPELINE_OUTPUT_DIR", _default_output_dir()))
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline("DiD Time-Series Analysis of Rental Prices")

    # Load boundaries and data (single ZORI panel read + geometric crosswalk)
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(TimeSeriesRentalLoader())
    pipeline.register_component(
        CensusDataLoader(
            state_fips="17",
            county_fips="031",
        )
    )
    pipeline.register_component(ZipTractCrosswalkProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "prohibition_date": "min",
                "number_of_units": "sum",
            },
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )
    pipeline.register_component(TractProhibitionDatesProcessor(output_dir=str(out_dir)))
    pipeline.register_component(
        TreatmentThresholdProcessor(output_dir=str(out_dir), percentile=0.25)
    )

    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer(output_dir=str(out_dir)))
    pipeline.register_component(TreatmentMapVisualizer(output_dir=str(out_dir)))

    pipeline.set_execution_order(
        [
            "zip_boundaries",
            "tract_boundaries",
            "city_boundaries",
            "rental_panel_data",
            "census_data",
            "zip_tract_crosswalk",
            "zip_to_tract_panel",
            "str_prohibition_data",
            "points_to_tract_str_prohibition_data",
            "tract_prohibition_dates",
            "treatment_threshold",
            "did_descriptive_analysis",
            "did_trends_visualization",
            "treatment_map_visualization",
        ]
    )

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info(
        "DiD Time-Series Analysis Pipeline for STR Prohibitions and Rental Prices"
    )
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check %s for visualizations.", _default_output_dir())
