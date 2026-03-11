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

import pandas as pd
from dotenv import load_dotenv

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_summary import (
    CallawaySantAnnaSummaryAnalyzer,
)
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
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
from housing.components.visualizers.callaway_santanna import (
    CallawaySantAnnaComparisonVisualizer,
    CallawaySantAnnaVisualizer,
)
from housing.components.visualizers.cohort_choropleth import (
    CohortChoroplethVisualizer,
)
from housing.components.visualizers.event_study import EventStudyVisualizer
from pipeline import Pipeline

logger = logging.getLogger(__name__)
load_dotenv()

# Constants for reporting / checks
_ALPHA_005 = 0.05
_ERRNO_RESOURCE_UNAVAILABLE = (
    35  # EAGAIN on macOS/Linux when file on cloud-synced folder
)
_LARGE_CS_TWFE_DIFF_DOLLARS = 10.0

# Paths
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_sa_month.csv"
DID_CS_OUTPUT_DIR = "/project/output/did-cs"


def _preflight_check() -> None:
    """Verify required data files exist and are readable."""
    missing = []
    if not TRACT_SHP.exists():
        missing.append(str(TRACT_SHP))
    elif TRACT_SHP.stat().st_size == 0:
        logger.warning("Tract shapefile is empty (0 bytes).")
    if not ZORI_CSV.exists():
        missing.append(str(ZORI_CSV))
    elif ZORI_CSV.stat().st_size == 0:
        logger.warning("ZORI CSV is empty (0 bytes).")
    if missing:
        raise FileNotFoundError(
            "DiD pipeline requires the following data files:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README). "
        )
    try:
        with ZORI_CSV.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == _ERRNO_RESOURCE_UNAVAILABLE:
            raise RuntimeError(
                "Could not read data file (Errno 35). "
                "This often happens when the project is on a cloud-synced folder.\n"
            ) from e
        raise
    logger.info("Preflight OK: tract shapefile and ZORI CSV found")


def _get_twfe_event_df(results: dict) -> pd.DataFrame | None:
    """Return TWFE event study as DataFrame with rel_time, coef for summary comparison.

    Housing's EventStudyAnalyzer stores raw PanelOLS in event_study_results and
    the coefficient table in event_study_coefficients. Normalize to rel_time, coef.
    """
    event_study_results = results.get("event_study_results")
    if isinstance(event_study_results, pd.DataFrame) and not event_study_results.empty:
        return event_study_results
    coef_df = results.get("event_study_coefficients")
    if coef_df is None or coef_df.empty:
        return None
    twfe_coef = coef_df.rename(
        columns={
            "relative_time": "rel_time",
            "coefficient": "coef",
        }
    )[["rel_time", "coef"]].copy()
    return twfe_coef[twfe_coef["rel_time"] != -1].reset_index(drop=True)


def run_did_analysis_with_cs() -> tuple:
    """Run DiD analysis with both TWFE and Callaway-Sant'Anna estimators."""
    logger.info("=" * 80)
    logger.info("DiD Analysis Pipeline: TWFE vs. Callaway-Sant'Anna (2020)")
    logger.info("=" * 80)
    _preflight_check()

    Path(DID_CS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline("Chicago Housing DiD: TWFE vs. Callaway-Sant'Anna")

    # 1. Load Data
    logger.info("\n[1/5] Loading data...")
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(file_path=ZORI_CSV))
    pipeline.register_component(RentalDataLoader(file_path=ZORI_CSV))
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))

    # 2. Process Data
    logger.info("\n[2/5] Processing panel data...")
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
    # pipeline.register_component(
    # TreatmentIndicatorProcessor(output_dir=DID_CS_OUTPUT_DIR)
    # )
    pipeline.register_component(
        TreatmentThresholdProcessor(  # REPLACE TreatmentIndicatorProcessor
            output_dir=DID_CS_OUTPUT_DIR, percentile=0.25
        )
    )

    # 3. Trend matching (restrict panel to matched treated + control tracts)
    logger.info("\n[3/6] Trend matching for parallel trends...")
    pipeline.register_component(
        TrendMatchingProcessor(k_neighbors=3, min_pre_periods=6)
    )

    # 4. Descriptive Analysis (on matched sample)
    logger.info("\n[4/6] Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer())

    # 5. TWFE Event Study (on matched sample)
    logger.info("\n[5/6] Estimating TWFE event study (matched sample)...")
    pipeline.register_component(
        EventStudyAnalyzer(
            pre_periods=12,
            post_periods=36,
            output_path=f"{DID_CS_OUTPUT_DIR}/event_study_coefficients.csv",
        )
    )
    pipeline.register_component(EventStudyVisualizer(output_dir=DID_CS_OUTPUT_DIR))

    # 6. Callaway-Sant'Anna (robust, on matched sample)
    logger.info("\n[6/6] Estimating Callaway-Sant'Anna event study (robust)...")
    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
        )
    )
    pipeline.register_component(
        CallawaySantAnnaSummaryAnalyzer(output_dir=DID_CS_OUTPUT_DIR)
    )
    pipeline.register_component(
        CallawaySantAnnaVisualizer(output_dir=DID_CS_OUTPUT_DIR)
    )
    pipeline.register_component(
        CallawaySantAnnaComparisonVisualizer(output_dir=DID_CS_OUTPUT_DIR)
    )
    pipeline.register_component(
        CohortChoroplethVisualizer(output_dir=DID_CS_OUTPUT_DIR)
    )

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
        logger.info("  Significant: %s", "Yes" if p_val < _ALPHA_005 else "No")

    # Trend matching info
    matching_info = results.get("matching_info")
    if matching_info is not None and not matching_info.empty:
        logger.info("\nTrend Matching:")
        logger.info(
            "  Matched treated tracts: %d", matching_info["treated_tract"].nunique()
        )
        logger.info(
            "  Matched control tracts: %d", matching_info["control_tract"].nunique()
        )
        logger.info("  Average slope distance: %.4f", matching_info["distance"].mean())

    # Cohort information
    cohort_info = results.get("cs_cohort_info", {})
    if cohort_info:
        n_cohorts = len(cohort_info.get("cohort_sizes", {}))
        n_never = cohort_info.get("n_never_treated", 0)
        logger.info("\nCohort Structure:")
        logger.info("  Number of treatment cohorts: %d", n_cohorts)
        logger.info("  Number of never-treated tracts: %d", n_never)

    # Cohort-level overall ATTs (post-treatment average per cohort)
    cohort_overall = results.get("cs_overall_att_by_cohort")
    if isinstance(cohort_overall, pd.DataFrame) and not cohort_overall.empty:
        logger.info("\nCohort-Level Overall ATTs (Callaway-Sant'Anna):")
        for _, row in cohort_overall.iterrows():
            cohort = str(row.get("cohort"))[:10]
            att = row.get("att", float("nan"))
            se = row.get("se", float("nan"))
            ci_low = row.get("ci_low", float("nan"))
            ci_high = row.get("ci_high", float("nan"))
            p_val = row.get("p_value", float("nan"))
            logger.info(
                "  Cohort %s: ATT=$%.2f (SE=$%.2f, 95%% CI=[$%.2f, $%.2f], p=%.4f)",
                cohort,
                att,
                se,
                ci_low,
                ci_high,
                p_val,
            )

    # Comparison with TWFE (use housing's event_study_coefficients format)
    cs_event = results.get("cs_event_study")
    twfe_event = _get_twfe_event_df(results)

    if cs_event is not None and twfe_event is not None:
        # Post-treatment comparison
        cs_post = cs_event[cs_event["rel_time"] >= 0]
        twfe_post = twfe_event[twfe_event["rel_time"] >= 0]

        if not cs_post.empty and not twfe_post.empty:
            merged = cs_post.merge(twfe_post[["rel_time", "coef"]], on="rel_time")
            avg_diff = (merged["att"] - merged["coef"]).mean()

            logger.info("\nTWFE vs. CS Comparison (Post-Treatment):")
            logger.info("  Average difference (CS - TWFE): $%.2f", avg_diff)
            if abs(avg_diff) > _LARGE_CS_TWFE_DIFF_DOLLARS:
                logger.warning(
                    "  Large difference detected! This suggests significant "
                    "heterogeneity bias in TWFE estimates."
                )
            else:
                logger.info(
                    "  Estimates are similar, suggesting TWFE is approximately unbiased."
                )

    logger.info("\n=== OUTPUT FILES ===\n")
    logger.info("Check %s/ for:", DID_CS_OUTPUT_DIR)
    logger.info("  • did_callaway_santanna_event_study.png - Main CS results")
    logger.info("  • did_twfe_vs_cs_comparison.png - Side-by-side comparison")
    logger.info("  • did_cs_twfe_difference.png - Bias visualization")
    logger.info("  • did_cohort_dynamics.png - Cohort-specific effects")
    logger.info(
        "  • did_cs_dynamic_att.png - Dynamic ATT (Eq. 3.8) and cumulative ATT (Eq. 3.9)"
    )
    logger.info("  • did_cs_dynamic_att.csv - Dynamic and cumulative ATT table")
    logger.info("  • did_twfe_cs_comparison_table.csv - Detailed comparison")
    logger.info("  • cohort-choropleths/ - Per-cohort and combined choropleth maps")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    pipeline, context = run_did_analysis_with_cs()
