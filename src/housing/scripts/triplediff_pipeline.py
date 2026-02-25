"""Chicago Housing Triple-Difference (DDD) pipeline.

Uses census data to define a third dimension (e.g. high vs low income tracts)
and estimates the differential effect of STR prohibition on rents across that group.

Requires census tract IDs to overlap with the DiD panel (tract_geoid). Use a
CENSUS_API_KEY for real ACS data; without it, demo census has only 10 tracts
and may not match the panel, so DDD estimation can fail.
"""

from __future__ import annotations

import logging
import os

from housing.components.analyzers.triplediff_analyzer import TripleDiffAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.census_panel_merger import CensusPanelMerger
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.treatment_indicator import (
    TreatmentIndicatorProcessor,
)
from housing.components.processors.triplediff_group import TripleDiffGroupProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.triplediff import TripleDiffVisualizer
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_triplediff_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the triple-difference pipeline with census data."""
    logger.info("Running Housing Triple-Difference Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Housing Triple-Difference Analysis")

    # Step 1: Load boundaries and data (same as DiD + census)
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(output_dir="/project/output"))
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(
        CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY"))
    )

    # Step 2: Build DiD panel (STR → tracts, zip→tract, time series panel, treatment)
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "number_of_units": ["sum", "mean", "median"],
                "prohibition_date": ["min", "max"],
            },
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(
        TimeSeriesZipToTractProcessor(output_dir="/project/output")
    )
    pipeline.register_component(TreatmentIndicatorProcessor(output_dir="/project/output"))

    # Step 3: Merge census into panel and create third-diff group
    pipeline.register_component(CensusPanelMerger())
    pipeline.register_component(
        TripleDiffGroupProcessor(
            group_variable="median_income",
            group_type="median",
            group_name="high_income",
        )
    )

    # Step 4: DDD analysis and visualization
    pipeline.register_component(TripleDiffAnalyzer())
    pipeline.register_component(TripleDiffVisualizer(output_dir="/project/output"))

    # Execution order: loaders → DiD panel builders → census merge → group → analyzer → visualizer
    pipeline.set_execution_order(
        [
            "rental_data",
            "str_prohibition_data",
            "rental_panel_data",
            "tract_boundaries",
            "zip_boundaries",
            "city_boundaries",
            "census_data",
            "points_to_tract_str_prohibition_data",
            "zip_to_tract",
            "time_series_zip_to_tract",
            "treatment_indicator",
            "census_panel_merger",
            "triplediff_group",
            "triplediff_analyzer",
            "triplediff_visualization",
        ]
    )

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Chicago Housing Triple-Difference Pipeline (Census + STR Prohibition)")
    logger.info("=" * 70)

    pipeline, results = run_triplediff_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Triple-diff complete. Check output/ for triplediff_*.csv and *.png")

    if "ddd_panel" in pipeline.context:
        ddd = pipeline.context["ddd_panel"]
        logger.info(
            "DDD panel: %d rows, %d tracts",
            len(ddd),
            ddd["tract_geoid"].nunique(),
        )
