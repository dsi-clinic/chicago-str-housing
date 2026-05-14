"""DiD Analysis Pipeline with Callaway & Sant'Anna (2021) estimator.

This pipeline runs both:
1. Standard TWFE event study (for comparison)
2. Callaway & Sant'Anna (2021) robust estimator

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

- Env ``DID_TREATMENT_MODE`` (or ``run_did_analysis_with_cs(treatment_mode=...)``): ``threshold``,
  ``binary``, or ``both`` (latter writes ``{output}-threshold`` and ``{output}-binary``).
- TWFE event study (baseline)
- Callaway-Sant'Anna event study (robust)
- Callaway-Sant'Anna with controls (covariates + tract trends; optional census)
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
from housing.components.analyzers.callaway_santanna_with_controls import (
    CallawaySantAnnaWithControlsAnalyzer,
)
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.did_story_tables import DIDStoryTablesAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.analyzers.honest_pretrends import HonestPretrendsAnalyzer
from housing.components.analyzers.latex_table_exporter import LaTeXTableExporter
from housing.components.analyzers.pretrend_diagnostic import PretrendDiagnosticAnalyzer
from housing.components.analyzers.sutva_donut_dose import SUTVADonutDoseAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
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
from housing.components.processors.treatment_indicator import (
    TreatmentIndicatorProcessor,
)
from housing.components.processors.treatment_threshold import (
    TreatmentThresholdProcessor,
)
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.processors.zip_tract_crosswalk import ZipTractCrosswalkProcessor
from housing.components.visualizers.callaway_santanna import (
    CallawaySantAnnaComparisonVisualizer,
    CallawaySantAnnaVisualizer,
)
from housing.components.visualizers.cohort_dynamics_explainer import (
    CohortDynamicsExplainerVisualizer,
)
from housing.components.visualizers.data_funnel import DataFunnelVisualizer
from housing.components.visualizers.did_sample_map import DiDSampleMapVisualizer
from housing.components.visualizers.did_story_graphics import DIDStoryGraphicsVisualizer
from housing.components.visualizers.did_story_map import DiDStoryMapVisualizer
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer
from pipeline import Pipeline

load_dotenv()

logger = logging.getLogger(__name__)

SIGNIFICANCE_LEVEL = 0.05
BIAS_THRESHOLD = 10  # $ threshold for TWFE vs CS difference

# Paths (defaults work in Docker; local runs resolve repo-relative output unless overridden)
_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"
DID_WHITEPAPER_MODE = os.environ.get("DID_WHITEPAPER_MODE", "").lower() in (
    "1",
    "true",
    "yes",
)
_default_leaf = "did-cs-whitepaper" if DID_WHITEPAPER_MODE else "did-cs"
_default_out = _REPO_ROOT / "output" / _default_leaf
_fallback_out = (
    f"/project/output/{_default_leaf}"
    if str(DATA_ROOT).startswith("/project")
    else str(_default_out)
)
DID_CS_OUTPUT_DIR = os.environ.get(
    "DID_CS_OUTPUT_DIR",
    _fallback_out,
)

DID_PREFLIGHT_MSG = (
    "If data files exist but you see 'Resource deadlock avoided' (Errno 35) or "
    "GDAL shapefile errors, the project may be on a cloud-synced folder (e.g. Box). "
    "Copy the data folder to a local directory and run:\n"
    "  cp -r data /tmp/chicago_data\n"
    "  DATA_DIR=/tmp/chicago_data make run-did-pipeline-cs"
)


def _resolve_treatment_mode(explicit: str | None) -> str:
    """Normalize treatment mode: ``threshold``, ``binary``, or ``both``."""
    raw = (
        (explicit or os.environ.get("DID_TREATMENT_MODE") or "threshold")
        .strip()
        .lower()
    )
    if raw not in {"threshold", "binary", "both"}:
        msg = (
            f"DID_TREATMENT_MODE must be 'threshold', 'binary', or 'both'; got {raw!r}"
        )
        raise ValueError(msg)
    return raw


def _output_dir_with_treatment_suffix(base: str, suffix: str) -> str:
    """Append ``-{suffix}`` to the last path segment (separate artefact trees per mode)."""
    p = Path(base)
    return str(p.parent / f"{p.name}-{suffix}")


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
        if e.errno == 35:  # noqa: PLR2004
            raise RuntimeError(
                "Could not read data file (Errno 35). "
                "This often happens when the project is on a cloud-synced folder.\n"
                + DID_PREFLIGHT_MSG
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
    twfe_data = coef_df.rename(
        columns={
            "relative_time": "rel_time",
            "coefficient": "coef",
        }
    )[["rel_time", "coef"]].copy()
    return twfe_data[twfe_data["rel_time"] != -1].reset_index(drop=True)


def run_did_analysis_with_cs(
    *,
    treatment_mode: str | None = None,
    output_dir: str | None = None,
) -> tuple:
    """Run DiD analysis with both TWFE and Callaway-Sant'Anna estimators.

    Args:
        treatment_mode: ``threshold`` (unit-share rule), ``binary`` (any first prohibition
            month), or ``both`` (two full pipeline runs). If omitted, uses env
            ``DID_TREATMENT_MODE`` (default ``threshold``).
        output_dir: Artefact directory; defaults to ``DID_CS_OUTPUT_DIR``. For
            ``treatment_mode='both'``, the two runs use ``{base}-threshold`` and
            ``{base}-binary`` where ``base`` is ``output_dir`` or ``DID_CS_OUTPUT_DIR``.
    """
    mode = _resolve_treatment_mode(treatment_mode)
    if mode == "both":
        base_out = output_dir or DID_CS_OUTPUT_DIR
        out_th = _output_dir_with_treatment_suffix(base_out, "threshold")
        out_bi = _output_dir_with_treatment_suffix(base_out, "binary")
        logger.info(
            "DID_TREATMENT_MODE=both: threshold → %s; binary → %s",
            out_th,
            out_bi,
        )
        run_did_analysis_with_cs(treatment_mode="threshold", output_dir=out_th)
        return run_did_analysis_with_cs(treatment_mode="binary", output_dir=out_bi)

    out_dir = output_dir or DID_CS_OUTPUT_DIR

    logger.info("=" * 80)
    logger.info("DiD Analysis Pipeline: TWFE vs. Callaway-Sant'Anna (2021)")
    logger.info("Treatment mode: %s", mode)
    logger.info("Output directory: %s", out_dir)
    logger.info("=" * 80)
    _preflight_check()

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline("Chicago Housing DiD: TWFE vs. Callaway-Sant'Anna")

    # 1. Load Data
    logger.info("\n[1/5] Loading data...")
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader(file_path=str(TRACT_SHP)))
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(file_path=str(ZORI_CSV)))

    # 2. Process Data
    logger.info("\n[2/5] Processing panel data...")
    pipeline.register_component(ZipTractCrosswalkProcessor())
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
    pipeline.register_component(TractProhibitionDatesProcessor(output_dir=out_dir))
    pipeline.register_component(
        CensusDataLoader(state_fips="17", county_fips="031"),
    )
    if mode == "threshold":
        pipeline.register_component(
            TreatmentThresholdProcessor(
                output_dir=out_dir,
                percentile=0.25,
            )
        )
    else:
        pipeline.register_component(
            TreatmentIndicatorProcessor(
                output_path=str(Path(out_dir) / "did_panel_data.csv"),
            ),
        )

    logger.info("\n[2b/5] Estimating full-panel Callaway-Sant'Anna before matching...")
    cs_full_panel = CallawaySantAnnaAnalyzer(
        comparison_group="nevertreated",
        anticipation=0,
        min_cohort_size=5,
        result_suffix="_full_panel",
    )
    cs_full_panel.name = "callaway_santanna_analysis_full_panel"
    pipeline.register_component(cs_full_panel)
    cs_full_panel_viz = CallawaySantAnnaVisualizer(
        output_dir=out_dir,
        context_suffix="_full_panel",
        output_suffix="_full_panel",
        title_suffix=" (full panel)",
    )
    cs_full_panel_viz.name = "callaway_santanna_visualizer_full_panel"
    pipeline.register_component(cs_full_panel_viz)

    # 3. Trend matching (restrict panel to matched treated + control tracts)
    logger.info("\n[3/7] Trend matching for parallel trends...")
    pipeline.register_component(
        TrendMatchingProcessor(
            k_neighbors=3,
            min_pre_periods=6,
            matching_features=("pre_trend_slope", "avg_pre_rent"),
        )
    )

    # 3b. Covariates (for CS with controls; census_data must exist in context)
    logger.info(
        "\n[3b/7] Merging covariates into matched DID panel (CS with controls)..."
    )
    pipeline.register_component(DIDCovariateProcessor())

    # 4. Descriptive Analysis (on matched sample)
    logger.info("\n[4/7] Running descriptive analysis...")
    pipeline.register_component(DIDDescriptiveAnalyzer(output_dir=out_dir))
    pipeline.register_component(DIDStoryTablesAnalyzer(output_dir=out_dir))
    pipeline.register_component(DIDStoryGraphicsVisualizer(output_dir=out_dir))
    pipeline.register_component(DIDTrendsVisualizer(output_dir=out_dir))
    pipeline.register_component(PretrendDiagnosticAnalyzer(output_dir=out_dir))
    pipeline.register_component(DiDSampleMapVisualizer(output_dir=out_dir))
    if DID_WHITEPAPER_MODE:
        pipeline.register_component(DiDStoryMapVisualizer(output_dir=out_dir))

    # 5. TWFE Event Study (on matched sample)
    logger.info("\n[5/7] Estimating TWFE event study (matched sample)...")
    pipeline.register_component(
        EventStudyAnalyzer(
            pre_periods=12,
            post_periods=36,
            output_path=f"{out_dir}/event_study_coefficients.csv",
        )
    )
    pipeline.register_component(EventStudyVisualizer(output_dir=out_dir))

    # 6. Callaway-Sant'Anna (robust, on matched sample)
    logger.info("\n[6/7] Estimating Callaway-Sant'Anna event study (robust)...")
    pipeline.register_component(
        CallawaySantAnnaAnalyzer(
            comparison_group="nevertreated",
            anticipation=0,
            min_cohort_size=5,
        )
    )
    pipeline.register_component(CallawaySantAnnaVisualizer(output_dir=out_dir))
    pipeline.register_component(
        CallawaySantAnnaComparisonVisualizer(output_dir=out_dir)
    )

    # 7. Callaway-Sant'Anna with controls (covariates + tract trends)
    logger.info("\n[7/7] Estimating Callaway-Sant'Anna with controls...")
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
    cs_visualizer_with_controls = CallawaySantAnnaVisualizer(
        output_dir=out_dir,
        context_suffix="_with_controls",
        output_suffix="_with_controls",
    )
    cs_visualizer_with_controls.name = "callaway_santanna_visualizer_with_controls"
    pipeline.register_component(cs_visualizer_with_controls)

    wp_order_suffix: list[str] = []
    if DID_WHITEPAPER_MODE:
        logger.info("Whitepaper mode: registering extra diagnostics and LaTeX tables")
        pipeline.register_component(HonestPretrendsAnalyzer(output_dir=out_dir))
        pipeline.register_component(
            SUTVADonutDoseAnalyzer(
                comparison_group="nevertreated",
                anticipation=0,
                min_cohort_size=5,
                output_dir=out_dir,
            )
        )
        pipeline.register_component(
            CohortDynamicsExplainerVisualizer(output_dir=out_dir)
        )
        pipeline.register_component(DataFunnelVisualizer(output_dir=out_dir))
        pipeline.register_component(LaTeXTableExporter(output_dir=out_dir))
        wp_order_suffix.extend(
            [
                "honest_pretrends_analysis",
                "sutva_donut_dose_analysis",
                "cohort_dynamics_explainer",
                "data_funnel_visualization",
                "latex_whitepaper_tables",
            ]
        )

    treatment_step = (
        "treatment_threshold" if mode == "threshold" else "treatment_indicator"
    )

    # Set execution order
    exec_order_core = [
        "zip_boundaries",
        "tract_boundaries",
        "city_boundaries",
        "zip_tract_crosswalk",
        "str_prohibition_data",
        "rental_panel_data",
        "zip_to_tract_panel",
        "points_to_tract_str_prohibition_data",
        "tract_prohibition_dates",
        "census_data",
        treatment_step,
        "callaway_santanna_analysis_full_panel",
        "callaway_santanna_visualizer_full_panel",
        "trend_matching",
        "did_panel_with_covariates",
        "did_descriptive_analysis",
        "did_story_tables",
        "did_story_graphics",
        "did_trends_visualization",
        "pretrend_diagnostic",
        "did_sample_map_visualization",
        *(["did_story_map_visualization"] if DID_WHITEPAPER_MODE else []),
        "event_study_analysis",
        "event_study_visualization",
        "callaway_santanna_analysis",
        "callaway_santanna_visualizer",
        "cs_comparison_visualizer",
        "callaway_santanna_with_controls",
        "callaway_santanna_visualizer_with_controls",
    ]
    pipeline.set_execution_order(exec_order_core + wp_order_suffix)

    # Execute pipeline
    logger.info("\n" + "=" * 80)
    logger.info("Starting pipeline execution...")
    logger.info("=" * 80 + "\n")

    pipeline.execute()

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)

    _print_summary(pipeline.context, output_dir=out_dir)

    return pipeline, pipeline.context


def _print_summary(results: dict, *, output_dir: str) -> None:
    """Print summary of key findings."""
    logger.info("\n=== KEY FINDINGS ===\n")

    cs_full_panel = results.get("cs_overall_att_full_panel", {})
    if cs_full_panel:
        att = cs_full_panel.get("att", float("nan"))
        se = cs_full_panel.get("se", float("nan"))
        p_val = cs_full_panel.get("p_value", float("nan"))
        ci_low = cs_full_panel.get("ci_low", float("nan"))
        ci_high = cs_full_panel.get("ci_high", float("nan"))

        logger.info("Callaway-Sant'Anna Overall ATT (full panel):")
        logger.info("  Point Estimate: $%.2f", att)
        logger.info("  Standard Error: $%.2f", se)
        logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low, ci_high)
        logger.info("  P-value: %.4f", p_val)
        logger.info("  Significant: %s", "Yes" if p_val < SIGNIFICANCE_LEVEL else "No")

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
        logger.info("  Significant: %s", "Yes" if p_val < SIGNIFICANCE_LEVEL else "No")

    # Overall ATT from CS with controls
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
        logger.info(
            "  Significant: %s", "Yes" if p_val_c < SIGNIFICANCE_LEVEL else "No"
        )
        if results.get("cs_include_covariates"):
            logger.info("  Covariates: included")
        if results.get("cs_include_tract_trends"):
            logger.info("  Tract trends: included")

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
            if abs(avg_diff) > BIAS_THRESHOLD:
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
    logger.info(
        "  • did_adoption_curve.png, did_parallel_trends.png — temporal/sample dynamics"
    )
    logger.info(
        "  • did_spatial_sample*.png, pretrend_*.csv — geography and parallel-trends diagnostics"
    )
    logger.info("  • did_twfe_cs_comparison_table.csv - Detailed comparison")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_did_analysis_with_cs()
