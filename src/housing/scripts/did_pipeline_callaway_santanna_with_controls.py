"""DiD pipeline: same CS stack as `did_pipeline_callaway_santanna.py` plus covariate-adjusted CS.

Runs the baseline housing DiD path (TWFE event study, Callaway–Sant'Anna without
covariate adjustment in the estimator, comparison plots), then merges census and
baseline-rent covariates into the matched panel and estimates **Callaway–Sant'Anna
with controls** (doubly robust + optional tract trends in the analyzer).

Optional tract-cluster bootstrap for **baseline** CS uses the same flags as the
baseline pipeline: ``--cs-bootstrap-reps``, ``--cs-bootstrap-seed``, or ``CS_BOOTSTRAP_REPS``.

Requires the same data as the baseline CS pipeline (tract shapefile, ZORI CSV).
`CENSUS_API_KEY` improves covariate coverage; without it the census loader uses demo data.
"""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_pretrend_test import (
    log_and_export_pre_trend_joint_test,
)
from housing.components.analyzers.callaway_santanna_tract_bootstrap import (
    parse_cs_bootstrap_cli,
    write_cs_bootstrap_csv,
)
from housing.components.analyzers.callaway_santanna_with_controls import (
    CallawaySantAnnaWithControlsAnalyzer,
)
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.did_covariate_merger import DIDCovariateProcessor
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
from housing.components.visualizers.event_study import EventStudyVisualizer
from housing.did_spec import (
    DID_CS_ANTICIPATION,
    DID_CS_COMPARISON_GROUP_WITH_CONTROLS,
    DID_CS_MIN_COHORT_SIZE,
    DID_STR_PROHIBITION_POINTS_AGGREGATE_COLUMNS,
    DID_STR_PROHIBITION_POINTS_ID_COLUMN,
    DID_TREATMENT_THRESHOLD_PERCENTILE,
    DID_TREND_MATCH_K_NEIGHBORS,
    DID_TREND_MATCH_MIN_PRE_PERIODS,
    DID_TWFE_POST_PERIODS,
    DID_TWFE_PRE_PERIODS,
    did_cs_output_dir,
    tract_shapefile_path,
    zori_csv_path,
)
from pipeline import Pipeline

logger = logging.getLogger(__name__)
load_dotenv()

# Constants for reporting / checks
_ALPHA_005 = 0.05
_ERRNO_RESOURCE_UNAVAILABLE = (
    35  # EAGAIN on macOS/Linux when file on cloud-synced folder
)
_LARGE_CS_TWFE_DIFF_DOLLARS = 10.0


def _preflight_check() -> None:
    """Verify required data files exist and are readable."""
    tract_shp = tract_shapefile_path()
    zori_csv = zori_csv_path()
    missing = []
    if not tract_shp.exists():
        missing.append(str(tract_shp))
    elif tract_shp.stat().st_size == 0:
        logger.warning("Tract shapefile is empty (0 bytes).")
    if not zori_csv.exists():
        missing.append(str(zori_csv))
    elif zori_csv.stat().st_size == 0:
        logger.warning("ZORI CSV is empty (0 bytes).")
    if missing:
        raise FileNotFoundError(
            "DiD pipeline requires the following data files:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README). "
        )
    try:
        with zori_csv.open("rb") as f:
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
    """Return TWFE event study as DataFrame with rel_time, coef for summary comparison."""
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


def run_did_analysis_with_cs_and_covariate_controls(
    *,
    cs_bootstrap_reps: int | None = None,
    cs_bootstrap_seed: int = 0,
) -> tuple:
    """Run baseline CS pipeline plus covariate merge and CS-with-controls."""
    logger.info("=" * 80)
    logger.info("DiD: TWFE vs. CS (2020) + Callaway–Sant'Anna with covariate controls")
    logger.info("=" * 80)
    _preflight_check()

    out_dir = did_cs_output_dir()
    zori = zori_csv_path()
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline(
        "Chicago Housing DiD: TWFE vs. CS + CS with covariate/trend controls"
    )

    logger.info("\n[1/7] Loading data...")
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(
        TractBoundariesLoader(file_path=str(tract_shapefile_path()))
    )
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(file_path=zori))
    pipeline.register_component(RentalDataLoader(file_path=zori))
    pipeline.register_component(CensusDataLoader(api_key=os.getenv("CENSUS_API_KEY")))

    logger.info("\n[2/7] Processing panel data...")
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

    logger.info("\n[3/7] Trend matching for parallel trends...")
    pipeline.register_component(
        TrendMatchingProcessor(
            k_neighbors=DID_TREND_MATCH_K_NEIGHBORS,
            min_pre_periods=DID_TREND_MATCH_MIN_PRE_PERIODS,
        )
    )

    logger.info("\n[4/7] Merging tract covariates (for CS with controls)...")
    pipeline.register_component(DIDCovariateProcessor())

    logger.info("\n[5/7] Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer())

    logger.info("\n[6/7] TWFE event study + baseline Callaway–Sant'Anna...")
    pipeline.register_component(
        EventStudyAnalyzer(
            pre_periods=DID_TWFE_PRE_PERIODS,
            post_periods=DID_TWFE_POST_PERIODS,
            output_path=f"{out_dir}/event_study_coefficients.csv",
        )
    )
    pipeline.register_component(EventStudyVisualizer(output_dir=out_dir))
    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group=DID_CS_COMPARISON_GROUP_WITH_CONTROLS,
            anticipation=DID_CS_ANTICIPATION,
            min_cohort_size=DID_CS_MIN_COHORT_SIZE,
            bootstrap_reps=cs_bootstrap_reps,
            bootstrap_seed=cs_bootstrap_seed,
        )
    )
    pipeline.register_component(CallawaySantAnnaVisualizer(output_dir=out_dir))
    pipeline.register_component(
        CallawaySantAnnaComparisonVisualizer(output_dir=out_dir)
    )

    logger.info("\n[7/7] Callaway–Sant'Anna with covariate / tract-trend controls...")
    pipeline.register_component(
        CallawaySantAnnaWithControlsAnalyzer(
            comparison_group=DID_CS_COMPARISON_GROUP_WITH_CONTROLS,
            anticipation=DID_CS_ANTICIPATION,
            min_cohort_size=DID_CS_MIN_COHORT_SIZE,
            include_covariates=True,
            include_tract_trends=True,
            estimation_method="dr",
        )
    )
    cs_visualizer_with_controls = CallawaySantAnnaVisualizer(
        output_dir=out_dir,
        context_suffix="_with_controls",
        output_suffix="_with_controls",
    )
    cs_visualizer_with_controls.name = "callaway_santanna_visualizer_with_controls"
    pipeline.register_component(cs_visualizer_with_controls)

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
            "did_panel_with_covariates",
            "did_descriptive_analysis",
            "event_study_analysis",
            "event_study_visualizer",
            "callaway_santanna_analysis",
            "callaway_santanna_visualizer",
            "cs_comparison_visualizer",
            "callaway_santanna_with_controls",
            "callaway_santanna_visualizer_with_controls",
        ]
    )

    logger.info("\n" + "=" * 80)
    logger.info("Starting pipeline execution...")
    logger.info("=" * 80 + "\n")

    pipeline.execute()

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)

    _print_summary(pipeline.context, output_dir=out_dir)

    return pipeline, pipeline.context


def _print_summary(results: dict, *, output_dir: str) -> None:
    """Print summary of key findings."""
    logger.info("\n=== KEY FINDINGS ===\n")

    cs_overall = results.get("cs_overall_att", {})
    if cs_overall:
        att = cs_overall.get("att", float("nan"))
        se = cs_overall.get("se", float("nan"))
        p_val = cs_overall.get("p_value", float("nan"))
        ci_low = cs_overall.get("ci_low", float("nan"))
        ci_high = cs_overall.get("ci_high", float("nan"))

        logger.info("Callaway-Sant'Anna Overall ATT (baseline):")
        logger.info("  Point Estimate: $%.2f", att)
        logger.info("  Standard Error: $%.2f", se)
        logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low, ci_high)
        logger.info("  P-value: %.4f", p_val)
        logger.info("  Significant: %s", "Yes" if p_val < _ALPHA_005 else "No")

    cs_overall_ctrl = results.get("cs_overall_att_with_controls", {})
    if cs_overall_ctrl:
        att_c = cs_overall_ctrl.get("att", float("nan"))
        se_c = cs_overall_ctrl.get("se", float("nan"))
        p_val_c = cs_overall_ctrl.get("p_value", float("nan"))
        ci_low_c = cs_overall_ctrl.get("ci_low", float("nan"))
        ci_high_c = cs_overall_ctrl.get("ci_high", float("nan"))

        logger.info("\nCallaway-Sant'Anna Overall ATT (with controls):")
        logger.info("  Point Estimate: $%.2f", att_c)
        logger.info("  Standard Error: $%.2f", se_c)
        logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low_c, ci_high_c)
        logger.info("  P-value: %.4f", p_val_c)
        logger.info("  Significant: %s", "Yes" if p_val_c < _ALPHA_005 else "No")
        if results.get("cs_include_covariates"):
            logger.info("  Covariates: included")
        if results.get("cs_include_tract_trends"):
            logger.info("  Tract trends: included")

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

    cohort_info = results.get("cs_cohort_info", {})
    if cohort_info:
        n_cohorts = len(cohort_info.get("cohort_sizes", {}))
        n_never = cohort_info.get("n_never_treated", 0)
        logger.info("\nCohort Structure:")
        logger.info("  Number of treatment cohorts: %d", n_cohorts)
        logger.info("  Number of never-treated tracts: %d", n_never)

    log_and_export_pre_trend_joint_test(
        results,
        output_dir,
        summary_key="cs_pre_trend_joint_test",
        periods_key="cs_pre_trend_joint_test_periods",
        aggregate_basename="cs_pre_trend_joint_test_aggregate",
        periods_basename="cs_pre_trend_joint_test_periods",
        label="Callaway–Sant'Anna (baseline CS)",
    )
    log_and_export_pre_trend_joint_test(
        results,
        output_dir,
        summary_key="cs_pre_trend_joint_test_with_controls",
        periods_key="cs_pre_trend_joint_test_periods_with_controls",
        aggregate_basename="cs_pre_trend_joint_test_with_controls_aggregate",
        periods_basename="cs_pre_trend_joint_test_with_controls_periods",
        label="Callaway–Sant'Anna (with controls)",
    )

    boot_df = results.get("cs_event_study_tract_bootstrap")
    boot_meta = results.get("cs_bootstrap_meta")
    if (
        isinstance(boot_df, pd.DataFrame)
        and not boot_df.empty
        and isinstance(boot_meta, dict)
    ):
        write_cs_bootstrap_csv(boot_df, boot_meta, output_dir)
        logger.info("\nCallaway–Sant'Anna tract-cluster bootstrap (baseline CS):")
        logger.info(
            "  Overall ATT: point $%.2f (analytic SE $%.2f) | bootstrap SE $%.2f, "
            "95%% CI [$%.2f, $%.2f] (%d valid draws, %d reps)",
            float(boot_meta.get("overall_att_point", float("nan"))),
            float(boot_meta.get("overall_se_analytic", float("nan"))),
            float(boot_meta.get("overall_se_boot", float("nan"))),
            float(boot_meta.get("overall_ci_low_boot", float("nan"))),
            float(boot_meta.get("overall_ci_high_boot", float("nan"))),
            int(boot_meta.get("overall_n_valid_draws", 0)),
            int(boot_meta.get("n_reps", 0)),
        )

    cs_event = results.get("cs_event_study")
    twfe_event = _get_twfe_event_df(results)

    if cs_event is not None and twfe_event is not None:
        cs_post = cs_event[cs_event["rel_time"] >= 0]
        twfe_post = twfe_event[twfe_event["rel_time"] >= 0]

        if not cs_post.empty and not twfe_post.empty:
            merged = cs_post.merge(twfe_post[["rel_time", "coef"]], on="rel_time")
            avg_diff = (merged["att"] - merged["coef"]).mean()

            logger.info("\nTWFE vs. CS Comparison (Post-Treatment, baseline CS):")
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
    logger.info("Check %s/ for:", output_dir)
    logger.info("  • did_callaway_santanna_event_study.png - Main CS results")
    logger.info(
        "  • did_callaway_santanna_event_study_with_controls.png - CS with controls"
    )
    logger.info("  • did_twfe_vs_cs_comparison.png - Side-by-side comparison")
    logger.info("  • did_cs_twfe_difference.png - Bias visualization")
    logger.info("  • did_cohort_dynamics.png - Cohort-specific effects")
    logger.info("  • did_twfe_cs_comparison_table.csv - Detailed comparison")
    logger.info(
        "  • cs_pre_trend_joint_test_aggregate.csv - Pre-trend joint Wald (baseline CS)"
    )
    logger.info("  • cs_pre_trend_joint_test_periods.csv - Per rel_time (baseline CS)")
    logger.info(
        "  • cs_pre_trend_joint_test_with_controls_aggregate.csv - Pre-trend joint Wald (with controls)"
    )
    logger.info(
        "  • cs_pre_trend_joint_test_with_controls_periods.csv - Per rel_time (with controls)"
    )
    logger.info(
        "  • cs_event_study_tract_bootstrap.csv - Tract-cluster bootstrap (when enabled)"
    )
    logger.info("  • cs_tract_bootstrap_meta.csv - Bootstrap metadata (when enabled)")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    _reps, _seed = parse_cs_bootstrap_cli()
    run_did_analysis_with_cs_and_covariate_controls(
        cs_bootstrap_reps=_reps, cs_bootstrap_seed=_seed
    )
