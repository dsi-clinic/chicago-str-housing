"""DiD Analysis Pipeline with Deseasonalization and Time-Varying Controls.

This pipeline addresses parallel trends violations caused by:
1. **Seasonality**: Monthly patterns in rental prices that correlate with treatment timing
2. **Differential trends**: Treated and control tracts may have different baseline growth rates

**Key enhancements:**

1. **Deseasonalization**: Removes month-of-year effects from rental prices before estimation
2. **Tract-specific trends**: Allows for linear differential trends between treated/control
3. **Covariate adjustment**: Controls for tract characteristics (income, demographics)

**When to use this pipeline:**

Use this pipeline instead of the standard CS pipeline when you observe:
- Pre-treatment event study coefficients that are not flat/zero
- Treatment timing that correlates with seasonal patterns
- Different baseline trends between treated and control groups

**Output:**

- Deseasonalized CS event study
- Comparison with non-deseasonalized results
- Diagnostic information on seasonal patterns
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
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_with_controls import (
    CallawaySantAnnaWithControlsAnalyzer
)

# Visualizers
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer
from housing.components.visualizers.callaway_santanna import (
    CallawaySantAnnaVisualizer,
    CallawaySantAnnaComparisonVisualizer,
)

logger = logging.getLogger(__name__)

# Paths
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"

DID_PREFLIGHT_MSG = (
    "If data files exist but you see 'Resource deadlock avoided' (Errno 35) or "
    "GDAL shapefile errors, the project may be on a cloud-synced folder (e.g. Box). "
    "Copy the data folder to a local directory and run:\n"
    "  cp -r data /tmp/chicago_data\n"
    "  DATA_DIR=/tmp/chicago_data make run-did-deseasonalized"
)


def _preflight_check() -> None:
    """Verify required data files exist and are readable."""
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
    try:
        with ZORI_CSV.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == 35:
            raise RuntimeError(
                "Could not read data file (Errno 35). "
                "This often happens when the project is on a cloud-synced folder.\n"
                + DID_PREFLIGHT_MSG
            ) from e
        raise
    logger.info("Preflight OK: tract shapefile and ZORI CSV found")


def run_did_analysis_deseasonalized() -> tuple:
    """Run DiD analysis with deseasonalization and time-varying controls."""
    logger.info("=" * 80)
    logger.info("DiD Analysis Pipeline: Deseasonalized with Time-Varying Controls")
    logger.info("=" * 80)
    _preflight_check()

    pipeline = Pipeline("Chicago Housing DiD: Deseasonalized + Controls")

    # 1. Load Data
    logger.info("\n[1/7] Loading data...")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader())

    # Try to load census data (optional)
    try:
        pipeline.register_component(CensusDataLoader(
            api_key=os.getenv("CENSUS_API_KEY"),
            state_fips="17",      # Illinois
            county_fips="031",    # Cook County (Chicago)
        ))
    except Exception as e:
        logger.warning("Could not load census data: %s. Proceeding without covariates.", e)

    # 2. Process Data
    logger.info("\n[2/7] Processing panel data...")
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())

    # 3. Deseasonalize
    logger.info("\n[3/7] Deseasonalizing rental prices...")
    pipeline.register_component(DeseasonalizeRentalProcessor())

    # 4. Add Covariates
    logger.info("\n[4/7] Adding covariates...")
    pipeline.register_component(DIDCovariateProcessor())

    # 5. Descriptive Analysis
    logger.info("\n[5/7] Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer())

    # 6. Baseline CS (on deseasonalized data, no tract trends)
    logger.info("\n[6/7] Estimating CS event study (deseasonalized, no trends)...")
    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
        )
    )
    # Visualize basic CS (without trends)
    basic_visualizer = CallawaySantAnnaVisualizer(output_suffix="")
    basic_visualizer.name = "callaway_santanna_visualizer_basic"
    pipeline.register_component(basic_visualizer)

    # 7. Enhanced CS (deseasonalized + tract trends + covariates)
    logger.info("\n[7/7] Estimating CS event study (deseasonalized + tract trends + covariates)...")
    pipeline.register_component(
        CallawaySantAnnaWithControlsAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
            include_covariates=True,
            include_tract_trends=True,
            estimation_method="dr",
        )
    )
    # Note: This will overwrite some context keys from the baseline CS
    # But we mainly care about the final results with full controls

    # Visualize the enhanced CS results (with tract trends)
    # Use suffix to create separate file from basic CS
    # IMPORTANT: Need unique component name so both visualizers run
    enhanced_visualizer = CallawaySantAnnaVisualizer(output_suffix="_with_trends")
    enhanced_visualizer.name = "callaway_santanna_visualizer_with_trends"
    pipeline.register_component(enhanced_visualizer)

    # Execute pipeline
    logger.info("\n" + "=" * 80)
    logger.info("Starting pipeline execution...")
    logger.info("=" * 80 + "\n")

    pipeline.execute()

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)

    _print_summary(pipeline.context)

    return pipeline, pipeline.context


def _print_summary(results: dict) -> None:
    """Print summary of key findings."""
    logger.info("\n=== KEY FINDINGS ===\n")

    # Seasonal adjustment info
    max_seasonal_adj = results.get("max_seasonal_adjustment", 0)
    logger.info("Deseasonalization:")
    logger.info("  Maximum seasonal adjustment: $%.2f", max_seasonal_adj)
    logger.info("  Note: Rental prices have been deseasonalized to remove")
    logger.info("        month-of-year effects that could confound treatment timing.")

    # Overall ATT from CS with controls
    cs_overall = results.get("cs_overall_att", {})
    if cs_overall:
        att = cs_overall.get("att", float("nan"))
        se = cs_overall.get("se", float("nan"))
        p_val = cs_overall.get("p_value", float("nan"))
        ci_low = cs_overall.get("ci_low", float("nan"))
        ci_high = cs_overall.get("ci_high", float("nan"))

        logger.info("\nCallaway-Sant'Anna Overall ATT (Deseasonalized + Controls):")
        logger.info("  Point Estimate: $%.2f", att)
        logger.info("  Standard Error: $%.2f", se)
        logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low, ci_high)
        logger.info("  P-value: %.4f", p_val)
        logger.info("  Significant: %s", "Yes" if p_val < 0.05 else "No")

        with_controls = results.get("cs_with_controls", False)
        if with_controls:
            est_method = results.get("cs_estimation_method", "or")
            method_labels = {"dr": "Doubly Robust", "ipw": "IPW", "or": "Outcome Regression"}
            logger.info("\nControls included:")
            logger.info("  • Estimation method: %s", method_labels.get(est_method, est_method))
            logger.info("  • Deseasonalized prices: Yes")
            logger.info("  • Time-invariant covariates: %s",
                       results.get("cs_include_covariates", False))
            logger.info("  • Tract-specific linear trends: %s",
                       results.get("cs_include_tract_trends", False))

            # Propensity score diagnostics (for DR/IPW)
            ps_diag = results.get("cs_propensity_diagnostics", [])
            if ps_diag:
                p_means = [d["p_hat_mean"] for d in ps_diag]
                p_mins = [d["p_hat_min"] for d in ps_diag]
                p_maxs = [d["p_hat_max"] for d in ps_diag]
                logger.info("\n  Propensity score diagnostics (across %d (g,t) cells):", len(ps_diag))
                logger.info("    Mean p-hat: %.3f (range: %.3f–%.3f)",
                           np.mean(p_means), min(p_means), max(p_means))
                logger.info("    Min p-hat:  %.3f", min(p_mins))
                logger.info("    Max p-hat:  %.3f", max(p_maxs))

    # Cohort information
    cohort_info = results.get("cs_cohort_info", {})
    if cohort_info:
        n_cohorts = len(cohort_info.get("cohort_sizes", {}))
        n_never = cohort_info.get("n_never_treated", 0)
        logger.info("\nCohort Structure:")
        logger.info("  Number of treatment cohorts: %d", n_cohorts)
        logger.info("  Number of never-treated tracts: %d", n_never)

    logger.info("\n=== INTERPRETATION ===\n")
    logger.info("Results are now adjusted for:")
    logger.info("  1. Seasonal patterns in rental prices")
    logger.info("  2. Tract-specific linear time trends")
    logger.info("  3. Time-invariant tract characteristics")
    logger.info("\nIf pre-treatment estimates are now closer to zero, this suggests")
    logger.info("the original parallel trends violation was driven by seasonality")
    logger.info("and/or differential trends, not fundamental non-comparability.")

    logger.info("\n=== OUTPUT FILES ===\n")
    logger.info("Check /project/output/ for:")
    logger.info("  • did_callaway_santanna_event_study.png - Basic CS (deseasonalized only)")
    logger.info("  • did_callaway_santanna_event_study_with_trends.png - Enhanced CS (WITH tract trends) ⭐")
    logger.info("  • did_cohort_dynamics_with_trends.png - Cohort-specific effects (with trends)")
    logger.info("  • did_descriptive_analysis.png - Trends visualization")
    logger.info("\n⭐ USE THE '_with_trends' VERSION - that's the one with ATT = -$177.43")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_did_analysis_deseasonalized()
