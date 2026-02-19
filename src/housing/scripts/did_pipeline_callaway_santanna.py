"""DiD Analysis Pipeline with Callaway & Sant'Anna (2020) estimator.

This pipeline runs both:
1. Standard TWFE event study (for comparison)
2. Callaway & Sant'Anna (2020) robust estimator

The comparison reveals whether heterogeneous treatment effects bias TWFE estimates.

**When to use Callaway-Sant'Anna:**

Use CS instead of TWFE when:
- Treatment adoption is staggered (different units treated at different times)
- Treatment effects may be heterogeneous across:
  * Cohorts (early vs. late adopters may have different effects)
  * Time since treatment (effects may grow/fade over time)
  * Calendar time (effects may vary with market conditions)

**Key differences from TWFE:**

1. **Comparison group**: CS uses only not-yet-treated or never-treated as controls
   (TWFE uses already-treated units as controls, which can bias estimates)

2. **Aggregation**: CS estimates ATT(g,t) for each (cohort, time) pair first,
   then aggregates transparently with known weights
   (TWFE pools all comparisons with implicit negative weights possible)

3. **Interpretation**: CS estimates are always valid ATTs under parallel trends
   (TWFE estimates can be biased if treatment effects are heterogeneous)

**Output:**

- TWFE event study (baseline)
- Callaway-Sant'Anna event study (robust)
- Side-by-side comparison plots
- Difference plot (CS - TWFE) showing bias
- Cohort-specific dynamics
- Comparison table
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

# Processors
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.time_series_zip_to_tract import TimeSeriesZipToTractProcessor
from housing.components.processors.treatment_indicator import TreatmentIndicatorProcessor

# Analyzers
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer

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
    "  DATA_DIR=/tmp/chicago_data make run-did-cs-pipeline"
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


def run_did_analysis_with_cs() -> tuple:
    """Run DiD analysis with both TWFE and Callaway-Sant'Anna estimators."""
    logger.info("=" * 80)
    logger.info("DiD Analysis Pipeline: TWFE vs. Callaway-Sant'Anna (2020)")
    logger.info("=" * 80)
    _preflight_check()

    pipeline = Pipeline("Chicago Housing DiD: TWFE vs. Callaway-Sant'Anna")

    # 1. Load Data
    logger.info("\n[1/5] Loading data...")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader())

    # 2. Process Data
    logger.info("\n[2/5] Processing panel data...")
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())

    # 3. Descriptive Analysis
    logger.info("\n[3/5] Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer())

    # 4. TWFE Event Study (baseline)
    logger.info("\n[4/5] Estimating TWFE event study (baseline)...")
    pipeline.register_component(EventStudyAnalyzer())
    pipeline.register_component(EventStudyVisualizer())

    # 5. Callaway-Sant'Anna (robust)
    logger.info("\n[5/5] Estimating Callaway-Sant'Anna event study (robust)...")
    # Use never-treated as comparison group (preferred)
    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,  # Require at least 5 tracts per cohort
        )
    )
    pipeline.register_component(CallawaySantAnnaVisualizer())
    pipeline.register_component(CallawaySantAnnaComparisonVisualizer())

    # Execute pipeline
    logger.info("\n" + "=" * 80)
    logger.info("Starting pipeline execution...")
    logger.info("=" * 80 + "\n")

    pipeline.execute()

    # Print summary (use pipeline.context, not the list of PipelineResult objects)
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)

    _print_summary(pipeline.context)

    return pipeline, pipeline.context


def _print_summary(results: dict) -> None:
    """Print summary of key findings."""
    logger.info("\n=== KEY FINDINGS ===\n")

    # Overall ATT from CS
    cs_overall = results.get("cs_overall_att", {})
    if cs_overall:
        att = cs_overall.get("att", float("nan"))
        se = cs_overall.get("se", float("nan"))
        p_val = cs_overall.get("p_value", float("nan"))
        ci_low = cs_overall.get("ci_low", float("nan"))
        ci_high = cs_overall.get("ci_high", float("nan"))

        logger.info("Callaway-Sant'Anna Overall ATT:")
        logger.info("  Point Estimate: $%.2f", att)
        logger.info("  Standard Error: $%.2f", se)
        logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low, ci_high)
        logger.info("  P-value: %.4f", p_val)
        logger.info("  Significant: %s", "Yes" if p_val < 0.05 else "No")

    # Cohort information
    cohort_info = results.get("cs_cohort_info", {})
    if cohort_info:
        n_cohorts = len(cohort_info.get("cohort_sizes", {}))
        n_never = cohort_info.get("n_never_treated", 0)
        logger.info("\nCohort Structure:")
        logger.info("  Number of treatment cohorts: %d", n_cohorts)
        logger.info("  Number of never-treated tracts: %d", n_never)

    # Comparison with TWFE
    cs_event = results.get("cs_event_study")
    twfe_event = results.get("event_study_results")

    if cs_event is not None and twfe_event is not None:
        # Post-treatment comparison
        cs_post = cs_event[cs_event["rel_time"] >= 0]
        twfe_post = twfe_event[twfe_event["rel_time"] >= 0]

        if not cs_post.empty and not twfe_post.empty:
            merged = cs_post.merge(twfe_post[["rel_time", "coef"]], on="rel_time")
            avg_diff = (merged["att"] - merged["coef"]).mean()

            logger.info("\nTWFE vs. CS Comparison (Post-Treatment):")
            logger.info("  Average difference (CS - TWFE): $%.2f", avg_diff)
            if abs(avg_diff) > 10:
                logger.warning(
                    "  ⚠ Large difference detected! This suggests significant "
                    "heterogeneity bias in TWFE estimates."
                )
            else:
                logger.info("  ✓ Estimates are similar, suggesting TWFE is approximately unbiased.")

    logger.info("\n=== OUTPUT FILES ===\n")
    logger.info("Check /project/output/ for:")
    logger.info("  • did_callaway_santanna_event_study.png - Main CS results")
    logger.info("  • did_twfe_vs_cs_comparison.png - Side-by-side comparison")
    logger.info("  • did_cs_twfe_difference.png - Bias visualization")
    logger.info("  • did_cohort_dynamics.png - Cohort-specific effects")
    logger.info("  • did_twfe_cs_comparison_table.csv - Detailed comparison")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_did_analysis_with_cs()
