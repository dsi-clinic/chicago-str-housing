"""Difference-in-Differences Time-Series Analysis Pipeline with Trend Matching.

This script demonstrates the DiD analysis workflow:
1. Loading time-series rental data from csv file
2. Spatial join to convert zip code data to Census tract level
3. Build DiD panel dataset with treatment variables
4. Conduct trend-matching to filter panel data
5. Analyze and visualize DiD data before experiment
6. Conduct DiD experiment and get treatment variable
7. Conduct event study to check parallel trends assumption
"""

import logging

from housing.components.analyzers.did import DIDAnalyzer
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.tract_prohibition_dates import (
    TractProhibitionDatesProcessor,
)
from housing.components.processors.treatment_indicator import (
    TreatmentIndicatorProcessor,
)
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study_visual import EventStudyVisualizer
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)

ZORI_FILE_PATH = "/project/data/Zip_zori_uc_sfrcondomfr_sm_sa_month.csv"
MATCHED_FOLDER = "/project/output/matched"


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate DiD Time-Series Analysis of Rental Prices"""
    logger.info("Running DiD Time-Series Analysis of Rental Prices")
    logger.info("=" * 70)

    pipeline = Pipeline("DiD Time-Series Analysis of Rental Prices")

    # Load boundaries and data
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(TimeSeriesRentalLoader(ZORI_FILE_PATH))

    # Load point-in-time data and use it to build the crosswalk
    pipeline.register_component(RentalDataLoader(ZORI_FILE_PATH))
    pipeline.register_component(ZipToTractProcessor())

    # Use crosswalk to convert panel data to tract-level
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    # Build treatment variable
    pipeline.register_component(STRProhibitionDataLoader())
    pipeline.register_component(TractProhibitionDatesProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())

    # Conduct trend-matching filter
    pipeline.register_component(TrendMatchingProcessor())

    # Conduct pre-experiment analysis
    pipeline.register_component(
        DIDDescriptiveAnalyzer(
            panel="did_panel_matched",
            output_dir=MATCHED_FOLDER,
            output_suffix="_matched",
        )
    )
    pipeline.register_component(
        DIDTrendsVisualizer(
            panel="did_panel_matched",
            output_dir=MATCHED_FOLDER,
            output_suffix="_matched",
        )
    )

    # Conduct DiD experiment
    pipeline.register_component(
        DIDAnalyzer(
            panel="did_panel_matched",
            output_dir=MATCHED_FOLDER,
            output_suffix="_matched",
        )
    )

    # Conduct parallel trends event study
    pipeline.register_component(EventStudyAnalyzer(panel="did_panel_matched"))
    pipeline.register_component(
        EventStudyVisualizer(output_dir=MATCHED_FOLDER, output_suffix="_matched")
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
    logger.info("Demo complete! Check the output/ directory for visualizations.")
