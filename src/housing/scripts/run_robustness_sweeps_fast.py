r"""Fast robustness sweeps: rematch + re-estimate CS from saved ``did_panel_data.csv``.

Avoids reloading shapefiles/ZORI; suitable when a full whitepaper run already exists.
Writes the same summary CSVs as ``run_robustness_sweeps.py``.

Usage:
  export PYTHONPATH=src CENSUS_API_KEY=...
  python src/housing/scripts/run_robustness_sweeps_fast.py \\
    --panel-csv output/did-cs-whitepaper-threshold/did_panel_data.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_with_controls import (
    CallawaySantAnnaWithControlsAnalyzer,
)
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.processors.did_covariate_merger import DIDCovariateProcessor
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.did_spec import (
    DID_CS_ANTICIPATION,
    DID_CS_COMPARISON_GROUP,
    DID_CS_MIN_COHORT_SIZE,
    DID_TREND_MATCH_FEATURES_2,
    DID_TREND_MATCH_MIN_PRE_PERIODS,
    resolve_trend_match_features,
)
from housing.scripts import plot_robustness_sweeps

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROBUSTNESS = REPO_ROOT / "docs" / "robustness"
K_VALUES = (1, 2, 3, 4, 5)
PERCENTILES = (0.10, 0.15, 0.25, 0.33, 0.50)


def _sweep_output_paths() -> tuple[Path, Path]:
    """Return k-neighbors and percentile CSV paths (suffix for matching spec)."""
    features = resolve_trend_match_features()
    suffix = "2feat" if len(features) == len(DID_TREND_MATCH_FEATURES_2) else "5feat"
    return (
        DOCS_ROBUSTNESS / f"k_neighbors_sweep_summary_{suffix}.csv",
        DOCS_ROBUSTNESS / f"threshold_percentile_sweep_summary_{suffix}.csv",
    )


def _load_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path, low_memory=False)
    panel["month"] = pd.to_datetime(panel["month"])
    panel["tract_geoid"] = panel["tract_geoid"].astype(str)
    return panel


def _reapply_percentile(panel: pd.DataFrame, percentile: float) -> pd.DataFrame:
    """Recompute ``treated`` from stored share columns (same logic as threshold processor)."""
    merged = panel.copy()
    active = merged[merged["pct_units_restricted"] > 0].copy()
    thresholds_by_year = (
        active.groupby("year")["pct_units_restricted"]
        .quantile(percentile)
        .reset_index()
        .rename(columns={"pct_units_restricted": "threshold"})
    )
    merged = merged.drop(columns=["threshold"], errors="ignore").merge(
        thresholds_by_year, on="year", how="left"
    )
    merged["threshold"] = merged["threshold"].fillna(1.0)
    above = merged["pct_units_restricted"] >= merged["threshold"]
    start = (
        merged.loc[above]
        .groupby("tract_geoid")["month"]
        .min()
        .reset_index()
        .rename(columns={"month": "treatment_start_month"})
    )
    merged = merged.drop(
        columns=["treatment_start_month", "treated", "months_since_treatment"],
        errors="ignore",
    ).merge(start, on="tract_geoid", how="left")
    merged["treated"] = (
        merged["treatment_start_month"].notna()
        & (
            merged["month"].dt.to_period("M")
            >= merged["treatment_start_month"].dt.to_period("M")
        )
    ).astype(int)
    merged["months_since_treatment"] = np.where(
        merged["treatment_start_month"].notna(),
        (merged["month"].dt.year - merged["treatment_start_month"].dt.year) * 12
        + (merged["month"].dt.month - merged["treatment_start_month"].dt.month),
        np.nan,
    )
    return merged


def _estimate_row(
    panel: pd.DataFrame,
    census_df: pd.DataFrame,
    *,
    k_neighbors: int = 3,
    full_panel_att: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Match panel, run matched CS + residualized CS; optional fixed full-panel ATT."""
    matcher = TrendMatchingProcessor(
        k_neighbors=k_neighbors,
        min_pre_periods=DID_TREND_MATCH_MIN_PRE_PERIODS,
        matching_features=resolve_trend_match_features(),
    )
    match_out = matcher.execute({"did_panel": panel})
    matched = match_out["did_panel"]
    diagnostics = match_out.get("matching_diagnostics") or {}

    cs = CallawaySantAnnaAnalyzer(
        comparison_group=DID_CS_COMPARISON_GROUP,
        anticipation=DID_CS_ANTICIPATION,
        min_cohort_size=DID_CS_MIN_COHORT_SIZE,
    )
    cs_out = cs.execute({"did_panel": matched})

    cov = DIDCovariateProcessor()
    panel_cov = cov.execute({"did_panel": matched, "census_data": census_df})[
        "did_panel_with_covariates"
    ]
    csw = CallawaySantAnnaWithControlsAnalyzer(
        comparison_group="nevertreated",
        anticipation=0,
        min_cohort_size=5,
        include_covariates=True,
        include_tract_trends=True,
        estimation_method="dr",
    )
    csw_out = csw.execute({"did_panel_with_covariates": panel_cov})

    if full_panel_att is None:
        cs_full = CallawaySantAnnaAnalyzer(
            comparison_group=DID_CS_COMPARISON_GROUP,
            anticipation=DID_CS_ANTICIPATION,
            min_cohort_size=DID_CS_MIN_COHORT_SIZE,
            result_suffix="_full_panel",
        )
        full_panel_att = cs_full.execute({"did_panel": panel}).get(
            "cs_overall_att_full_panel", {}
        )

    mi = match_out.get("matching_info")
    n_treated = (
        int(mi["treated_tract"].nunique()) if isinstance(mi, pd.DataFrame) else None
    )
    n_control = (
        int(mi["control_tract"].nunique()) if isinstance(mi, pd.DataFrame) else None
    )

    return {
        "n_matched_treated_tracts": n_treated,
        "n_matched_control_tracts": n_control,
        "max_control_reuse": diagnostics.get("control_reuse_max"),
        "n_ever_treated_tracts": int(
            panel.groupby("tract_geoid")["treated"].max().ge(1).sum()
        ),
        "cs_full_panel_att": full_panel_att.get("att") if full_panel_att else None,
        "cs_full_panel_se": full_panel_att.get("se") if full_panel_att else None,
        "cs_matched_att": cs_out.get("cs_overall_att", {}).get("att"),
        "cs_matched_se": cs_out.get("cs_overall_att", {}).get("se"),
        "cs_with_controls_att": csw_out.get("cs_overall_att_with_controls", {}).get(
            "att"
        ),
        "cs_with_controls_se": csw_out.get("cs_overall_att_with_controls", {}).get(
            "se"
        ),
    }


def run_k_sweep(panel: pd.DataFrame, census_df: pd.DataFrame) -> pd.DataFrame:
    """k-neighbors sweep on fixed threshold panel."""
    k_csv, _ = _sweep_output_paths()
    cs_full = CallawaySantAnnaAnalyzer(
        comparison_group=DID_CS_COMPARISON_GROUP,
        anticipation=DID_CS_ANTICIPATION,
        min_cohort_size=DID_CS_MIN_COHORT_SIZE,
        result_suffix="_full_panel",
    )
    full_att = cs_full.execute({"did_panel": panel}).get(
        "cs_overall_att_full_panel", {}
    )

    rows: list[dict[str, Any]] = []
    for k in K_VALUES:
        logger.info("Fast k sweep: k=%d", k)
        try:
            row = _estimate_row(
                panel, census_df, k_neighbors=k, full_panel_att=full_att
            )
            row.update(
                {"sweep": "k_neighbors", "parameter": "k_neighbors", "value": str(k)}
            )
            rows.append(row)
        except Exception as exc:
            logger.exception("k=%d failed", k)
            rows.append(
                {
                    "sweep": "k_neighbors",
                    "parameter": "k_neighbors",
                    "value": str(k),
                    "error": str(exc),
                }
            )
        pd.DataFrame(rows).to_csv(k_csv, index=False)
    return pd.DataFrame(rows)


def run_percentile_sweep(
    base_panel: pd.DataFrame, census_df: pd.DataFrame
) -> pd.DataFrame:
    """Threshold percentile sweep."""
    _, pct_csv = _sweep_output_paths()
    rows: list[dict[str, Any]] = []
    for pct in PERCENTILES:
        logger.info("Fast percentile sweep: %.2f", pct)
        panel = _reapply_percentile(base_panel, pct)
        try:
            row = _estimate_row(panel, census_df, k_neighbors=3)
            row.update(
                {
                    "sweep": "threshold_percentile",
                    "parameter": "percentile",
                    "value": f"{pct:.2f}",
                }
            )
            rows.append(row)
        except Exception as exc:
            logger.exception("percentile=%.2f failed", pct)
            rows.append(
                {
                    "sweep": "threshold_percentile",
                    "parameter": "percentile",
                    "value": f"{pct:.2f}",
                    "error": str(exc),
                }
            )
        pd.DataFrame(rows).to_csv(pct_csv, index=False)
    return pd.DataFrame(rows)


def main() -> None:
    """Load panel, census, run fast sweeps, plot."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel-csv",
        default=str(
            REPO_ROOT / "output" / "did-cs-whitepaper-threshold" / "did_panel_data.csv"
        ),
    )
    parser.add_argument("--k-only", action="store_true")
    parser.add_argument("--percentile-only", action="store_true")
    args = parser.parse_args()

    DOCS_ROBUSTNESS.mkdir(parents=True, exist_ok=True)
    panel = _load_panel(Path(args.panel_csv))
    logger.info(
        "Loaded panel: %d rows, %d tracts", len(panel), panel["tract_geoid"].nunique()
    )

    census_loader = CensusDataLoader(state_fips="17", county_fips="031")
    census_df = census_loader.execute({})["census_data"]

    run_k = args.k_only or (not args.k_only and not args.percentile_only)
    run_pct = args.percentile_only or (not args.k_only and not args.percentile_only)

    if run_k:
        run_k_sweep(panel, census_df)
    if run_pct:
        run_percentile_sweep(panel, census_df)

    plot_robustness_sweeps.main()
    logger.info("Fast robustness sweeps complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
