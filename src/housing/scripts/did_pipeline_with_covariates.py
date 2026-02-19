"""Enhanced DiD Analysis Pipeline with Covariate Controls.

This script implements the staggered Difference-in-Differences analysis with
covariate controls to address pre-treatment divergence concerns:

1. Load data (Trajectories, Boundaries, STR Prohibitions, Census)
2. Prepare panel data (Rental Time Series, Zip->Tract conversion)
3. Generate DiD indicators (Treatment timing)
4. Merge tract-level covariates (Census demographics, baseline characteristics)
5. Perform diagnostic analysis (Pre-trend tests, balance checks)
6. Run baseline event study (No covariates)
7. Run covariate-adjusted event study (With controls)
8. Generate comparison visualizations
"""
import logging
import os
from pathlib import Path

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
from housing.components.processors.did_covariate_merger import DIDCovariateProcessor

# Analyzers & Visualizers
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.analyzers.event_study_with_covariates import EventStudyWithCovariatesAnalyzer
from housing.components.analyzers.pretrend_diagnostic import PretrendDiagnosticAnalyzer
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer
from housing.components.visualizers.event_study_comparison import EventStudyComparisonVisualizer

logger = logging.getLogger(__name__)

# Paths used by loaders (must match loader defaults when run in container)
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"

DID_PREFLIGHT_MSG = (
    "If data files exist but you see 'Resource deadlock avoided' (Errno 35) or "
    "GDAL shapefile errors, the project may be on a cloud-synced folder (e.g. Box). "
    "Copy the data folder to a local directory and run:\n"
    "  cp -r data /tmp/chicago_data\n"
    "  DATA_DIR=/tmp/chicago_data make run-did-pipeline-covariates"
)


def _preflight_check() -> None:
    """Verify required data files exist and are readable before running the pipeline."""
    missing = []
    if not TRACT_SHP.exists():
        missing.append(str(TRACT_SHP))
    elif TRACT_SHP.stat().st_size == 0:
        logger.warning("Tract shapefile is empty (0 bytes). %s", DID_PREFLIGHT_MSG)
    if not ZORI_CSV.exists():
        missing.append(str(ZORI_CSV))
    elif ZORI_CSV.stat().st_size == 0:
        logger.warning("ZORI CSV is empty (0 bytes). %s", DID_PREFLIGHT_MSG)
    if missing:
        raise FileNotFoundError(
            "DiD pipeline requires the following data files:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README). "
            + DID_PREFLIGHT_MSG
        )
    # Try a quick read to catch Errno 35 (resource deadlock) on synced drives
    try:
        with ZORI_CSV.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == 35:  # Resource deadlock avoided (e.g. Box + Docker)
            raise RuntimeError(
                "Could not read data file (Errno 35). "
                "This often happens when the project is on a cloud-synced folder.\n"
                + DID_PREFLIGHT_MSG
            ) from e
        raise
    logger.info("Preflight OK: tract shapefile and ZORI CSV found")


def run_did_analysis_with_covariates() -> tuple:
    """Run the complete DiD analysis pipeline with covariate controls."""
    logger.info("Starting Enhanced DiD Analysis Pipeline (with covariates)")
    _preflight_check()

    pipeline = Pipeline("Chicago Housing DiD Analysis with Covariates")

    # 1. Load Data
    logger.info("Step 1: Loading spatial and rental data...")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())  # For crosswalk
    pipeline.register_component(TimeSeriesRentalLoader())  # For analysis

    # NEW: Load census data for covariates
    logger.info("Step 2: Loading census demographic data...")
    pipeline.register_component(CensusDataLoader(
        # API key from environment if available, otherwise uses demo data
        state_fips="17",  # Illinois
        county_fips="031"  # Cook County (Chicago)
    ))

    # 2. Process Data
    logger.info("Step 3: Processing spatial crosswalks...")
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    logger.info("Step 4: Creating treatment indicators...")
    pipeline.register_component(TreatmentIndicatorProcessor())

    # NEW: Merge covariates into DID panel
    logger.info("Step 5: Merging tract-level covariates...")
    pipeline.register_component(DIDCovariateProcessor())

    # 3. Analyze & Visualize
    logger.info("Step 6: Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer())

    # NEW: Run diagnostic analysis to investigate pre-trends
    logger.info("Step 7: Diagnosing pre-treatment trends...")
    pipeline.register_component(PretrendDiagnosticAnalyzer())

    # Run BOTH event studies: baseline and with covariates
    logger.info("Step 8: Estimating event studies...")
    pipeline.register_component(EventStudyAnalyzer())  # Baseline
    pipeline.register_component(EventStudyWithCovariatesAnalyzer())  # With covariates

    logger.info("Step 9: Creating visualizations...")
    pipeline.register_component(EventStudyVisualizer())  # Original baseline plot
    pipeline.register_component(EventStudyComparisonVisualizer())  # Comparison plot

    # Execute
    logger.info("Executing pipeline...")
    results = pipeline.execute()

    logger.info("=" * 70)
    logger.info("Enhanced DiD Analysis Pipeline Completed Successfully")
    logger.info("=" * 70)

    # Print key findings (context holds outputs from successful components)
    _print_key_findings(pipeline.context)

    return pipeline, results


def _print_key_findings(context: dict) -> None:
    """Print summary of key findings from the analysis."""
    if not isinstance(context, dict):
        logger.warning("Key findings require pipeline context (dict), got %s", type(context).__name__)
        return

    logger.info("\nKEY FINDINGS:")

    # 1. Sample size
    if "event_study_n_obs" in context:
        logger.info("  Sample: %d tract-month observations", context["event_study_n_obs"])

    # 2. Covariate balance
    balance = context.get("pretrend_balance_check", {})
    if "balance_assessment" in balance:
        logger.info("  Covariate balance: %s", balance["balance_assessment"])
        if balance.get("imbalanced_covariates"):
            logger.info("    Imbalanced: %s", ", ".join(balance["imbalanced_covariates"]))

    # 3. Pre-trend test
    pretrend = context.get("pretrend_test_results", {})
    if "interpretation" in pretrend:
        logger.info("  Pre-trend test: %s", pretrend["interpretation"])

    # 4. Covariates used
    covariates = context.get("event_study_covariates_used", [])
    if covariates:
        logger.info("  Covariates included: %s", ", ".join(covariates))

    # 5. Output files
    logger.info("\nOUTPUT FILES:")
    if "event_study_plot_path" in context:
        logger.info("  - %s", context["event_study_plot_path"])
    if "event_study_comparison_plot_path" in context:
        logger.info("  - %s", context["event_study_comparison_plot_path"])

    logger.info("=" * 70)


if __name__ == "__main__":
    run_did_analysis_with_covariates()
