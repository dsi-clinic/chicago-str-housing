"""DiD pipeline: Callaway–Sant'Anna + post-treatment trajectory (growth vs. plateau).

Runs the same loaders, processors, and trend matching as the main CS pipeline
(without TWFE), then baseline :class:`CallawaySantAnnaAnalyzer`,
:class:`CallawaySantAnnaTrajectoryAnalyzer`, and
:class:`CallawaySantAnnaTrajectoryVisualizer`.

Outputs under :func:`housing.did_spec.did_cs_output_dir` (default
``/project/output/did-cs``; override with ``DID_CS_OUTPUT_DIR``).

- Baseline CS figures from :class:`CallawaySantAnnaVisualizer`
- ``did_cs_trajectory_fit.png``, ``did_cs_trajectory_phases.png``,
  ``cs_trajectory_summary.csv`` from the trajectory visualizer
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_trajectory import (
    CallawaySantAnnaTrajectoryAnalyzer,
)
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
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
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.callaway_santanna import CallawaySantAnnaVisualizer
from housing.components.visualizers.callaway_santanna_trajectory import (
    CallawaySantAnnaTrajectoryVisualizer,
)
from housing.did_spec import (
    DID_CS_ANTICIPATION,
    DID_CS_COMPARISON_GROUP,
    DID_CS_MIN_COHORT_SIZE,
    DID_STR_PROHIBITION_POINTS_AGGREGATE_COLUMNS,
    DID_STR_PROHIBITION_POINTS_ID_COLUMN,
    DID_TREATMENT_THRESHOLD_PERCENTILE,
    DID_TREND_MATCH_K_NEIGHBORS,
    DID_TREND_MATCH_MIN_PRE_PERIODS,
    did_cs_output_dir,
    tract_shapefile_path,
    zori_csv_path,
)
from pipeline import Pipeline

logger = logging.getLogger(__name__)
load_dotenv()

_ERRNO_RESOURCE_UNAVAILABLE = 35


def _preflight_check() -> None:
    tract_shp = tract_shapefile_path()
    zori_csv = zori_csv_path()
    missing = []
    if not tract_shp.exists():
        missing.append(str(tract_shp))
    if not zori_csv.exists():
        missing.append(str(zori_csv))
    if missing:
        raise FileNotFoundError(
            "DiD trajectory pipeline requires:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README)."
        )
    try:
        with zori_csv.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == _ERRNO_RESOURCE_UNAVAILABLE:
            raise RuntimeError(
                "Could not read ZORI CSV (Errno 35). Cloud-synced folders often cause this."
            ) from e
        raise
    logger.info("Preflight OK for CS trajectory pipeline")


def run_cs_trajectory_pipeline() -> tuple[Pipeline, dict]:
    """Build panel, baseline CS, trajectory analysis, and figures."""
    logger.info("=" * 80)
    logger.info("DiD: Callaway–Sant'Anna + post-treatment trajectory")
    logger.info("=" * 80)
    _preflight_check()

    out_dir = did_cs_output_dir()
    zori = zori_csv_path()
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline("Chicago Housing DiD: CS trajectory")

    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(
        TractBoundariesLoader(file_path=str(tract_shapefile_path()))
    )
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(file_path=zori))
    pipeline.register_component(RentalDataLoader(file_path=zori))
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))

    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column=DID_STR_PROHIBITION_POINTS_ID_COLUMN,
            aggregate_columns=DID_STR_PROHIBITION_POINTS_AGGREGATE_COLUMNS,
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )
    pipeline.register_component(TractProhibitionDatesProcessor(output_dir=out_dir))
    pipeline.register_component(
        TreatmentThresholdProcessor(
            output_dir=out_dir,
            percentile=DID_TREATMENT_THRESHOLD_PERCENTILE,
        )
    )
    pipeline.register_component(
        TrendMatchingProcessor(
            k_neighbors=DID_TREND_MATCH_K_NEIGHBORS,
            min_pre_periods=DID_TREND_MATCH_MIN_PRE_PERIODS,
        )
    )

    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group=DID_CS_COMPARISON_GROUP,
            anticipation=DID_CS_ANTICIPATION,
            min_cohort_size=DID_CS_MIN_COHORT_SIZE,
        )
    )
    pipeline.register_component(CallawaySantAnnaVisualizer(output_dir=out_dir))
    pipeline.register_component(CallawaySantAnnaTrajectoryAnalyzer())
    pipeline.register_component(CallawaySantAnnaTrajectoryVisualizer(output_dir=out_dir))

    pipeline.set_execution_order(
        [
            "zip_boundaries",
            "tract_boundaries",
            "str_prohibition_data",
            "rental_panel_data",
            "rental_data",
            "census_data",
            "zip_to_tract",
            "zip_to_tract_panel",
            "points_to_tract_str_prohibition_data",
            "tract_prohibition_dates",
            "treatment_threshold",
            "trend_matching",
            "callaway_santanna_analysis",
            "callaway_santanna_visualizer",
            "callaway_santanna_trajectory_analysis",
            "callaway_santanna_trajectory_visualizer",
        ]
    )

    logger.info("Executing pipeline...")
    pipeline.execute()

    logger.info("=" * 80)
    logger.info("CS trajectory pipeline complete. Outputs in %s", out_dir)
    logger.info("=" * 80)

    return pipeline, pipeline.context


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_cs_trajectory_pipeline()
