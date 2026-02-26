"""TWFE Event Study Pipeline (Deseasonalized).

Runs the standard Two-Way Fixed Effects event study on deseasonalized data.
This produces the traditional TWFE event study plot that can be compared
against the Callaway & Sant'Anna doubly-robust estimates from the CS pipeline.

**Output:**
- did_event_study.png  — TWFE event study plot
"""

import logging
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from pipeline import Pipeline

# Loaders
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.census_data import CensusDataLoader

# Processors
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.time_series_zip_to_tract import TimeSeriesZipToTractProcessor
from housing.components.processors.treatment_indicator import TreatmentIndicatorProcessor
from housing.components.processors.deseasonalize_rental import DeseasonalizeRentalProcessor
from housing.components.processors.did_covariate_merger import DIDCovariateProcessor

# Analyzers
from housing.components.analyzers.event_study import EventStudyAnalyzer

# Visualizers
from housing.components.visualizers.event_study import EventStudyVisualizer

logger = logging.getLogger(__name__)

# Paths
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"


def run_twfe_analysis() -> tuple:
    """Run TWFE event study on deseasonalized data."""
    logger.info("=" * 80)
    logger.info("TWFE Event Study Pipeline (Deseasonalized)")
    logger.info("=" * 80)

    pipeline = Pipeline("Chicago Housing DiD: TWFE Event Study")

    # 1. Load Data
    logger.info("\n[1/5] Loading data...")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader())

    try:
        pipeline.register_component(CensusDataLoader(
            api_key=os.getenv("CENSUS_API_KEY"),
            state_fips="17",
            county_fips="031",
        ))
    except Exception as e:
        logger.warning("Could not load census data: %s. Proceeding without covariates.", e)

    # 2. Process Data
    logger.info("\n[2/5] Processing panel data...")
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())

    # 3. Deseasonalize
    logger.info("\n[3/5] Deseasonalizing rental prices...")
    pipeline.register_component(DeseasonalizeRentalProcessor())

    # 4. TWFE Event Study
    logger.info("\n[4/5] Estimating TWFE event study...")
    pipeline.register_component(EventStudyAnalyzer(include_covariates=False))

    # 5. Visualize
    logger.info("\n[5/5] Creating TWFE event study plot...")
    pipeline.register_component(EventStudyVisualizer())

    # Execute
    logger.info("\n" + "=" * 80)
    logger.info("Starting pipeline execution...")
    logger.info("=" * 80 + "\n")

    pipeline.execute()

    # Summary
    results = pipeline.context
    logger.info("\n" + "=" * 80)
    logger.info("TWFE ANALYSIS COMPLETE")
    logger.info("=" * 80)

    es = results.get("event_study_results")
    if es is not None and not es.empty:
        post = es[es["rel_time"] >= 0]
        if not post.empty:
            mean_post = post["coef"].mean()
            logger.info("\nTWFE Results:")
            logger.info("  Mean post-treatment coefficient: $%.2f", mean_post)
            logger.info("  Number of relative-time coefficients: %d", len(es))

    logger.info("\nOutput: /project/output/did_event_study.png")
    logger.info("\nNote: TWFE may be biased with staggered treatment timing.")
    logger.info("Compare against CS results from: make run-did-pipeline-deseasonalized")
    logger.info("=" * 80)

    return pipeline, results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_twfe_analysis()
