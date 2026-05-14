"""DiD pipeline: Callaway–Sant'Anna baseline + subgroup heterogeneity.

Runs the same loaders, processors, and trend matching as the main CS pipeline,
then baseline :class:`CallawaySantAnnaAnalyzer` and
:class:`CallawaySantAnnaHeterogeneityAnalyzer` + visualizer.

Does **not** run TWFE, tract-cluster bootstrap, or covariate-adjusted CS.

Outputs (under ``DID_CS_OUTPUT_DIR``):

- Baseline CS figures/CSVs from ``CallawaySantAnnaAnalyzer`` / visualizer (optional;
  heterogeneity-only outputs are always written when the heterogeneity step runs).
- ``cs_heterogeneity_summary.csv``, ``did_cs_heterogeneity_*.png``,
  ``did_cs_cohort_early_vs_late.png`` from the heterogeneity visualizer.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_heterogeneity import (
    CallawaySantAnnaHeterogeneityAnalyzer,
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
from housing.components.visualizers.callaway_santanna_heterogeneity import (
    CallawaySantAnnaHeterogeneityVisualizer,
)
from pipeline import Pipeline

logger = logging.getLogger(__name__)
load_dotenv()

_ERRNO_RESOURCE_UNAVAILABLE = 35

DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"
DID_CS_OUTPUT_DIR = "/project/output/did-cs"


def _preflight_check() -> None:
    missing = []
    if not TRACT_SHP.exists():
        missing.append(str(TRACT_SHP))
    if not ZORI_CSV.exists():
        missing.append(str(ZORI_CSV))
    if missing:
        raise FileNotFoundError(
            "DiD heterogeneity pipeline requires:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README)."
        )
    try:
        with ZORI_CSV.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == _ERRNO_RESOURCE_UNAVAILABLE:
            raise RuntimeError(
                "Could not read ZORI CSV (Errno 35). Cloud-synced folders often cause this."
            ) from e
        raise
    logger.info("Preflight OK for CS heterogeneity pipeline")


def run_cs_heterogeneity_pipeline() -> tuple[Pipeline, dict]:
    """Build panel, baseline CS, subgroup heterogeneity, and figures."""
    logger.info("=" * 80)
    logger.info("DiD: Callaway–Sant'Anna + subgroup heterogeneity")
    logger.info("=" * 80)
    _preflight_check()

    Path(DID_CS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline("Chicago Housing DiD: CS heterogeneity")

    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(file_path=ZORI_CSV))
    pipeline.register_component(RentalDataLoader(file_path=ZORI_CSV))
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))

    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
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
    pipeline.register_component(
        TractProhibitionDatesProcessor(output_dir=DID_CS_OUTPUT_DIR)
    )
    pipeline.register_component(
        TreatmentThresholdProcessor(output_dir=DID_CS_OUTPUT_DIR, percentile=0.1)
    )
    pipeline.register_component(
        TrendMatchingProcessor(k_neighbors=3, min_pre_periods=6)
    )

    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
        )
    )
    pipeline.register_component(CallawaySantAnnaVisualizer(output_dir=DID_CS_OUTPUT_DIR))

    pipeline.register_component(
        CallawaySantAnnaHeterogeneityAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
        )
    )
    pipeline.register_component(
        CallawaySantAnnaHeterogeneityVisualizer(output_dir=DID_CS_OUTPUT_DIR)
    )

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
            "callaway_santanna_heterogeneity_analysis",
            "callaway_santanna_heterogeneity_visualizer",
        ]
    )

    logger.info("Executing pipeline...")
    pipeline.execute()

    logger.info("=" * 80)
    logger.info("CS heterogeneity pipeline complete. Outputs in %s", DID_CS_OUTPUT_DIR)
    logger.info("=" * 80)

    return pipeline, pipeline.context


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_cs_heterogeneity_pipeline()
