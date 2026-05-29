"""Run k-neighbors and threshold-percentile robustness sweeps for the DiD CS pipeline.

Writes summary CSVs under ``docs/robustness/`` (not gitignored ``output/`` trees).

Usage:
  export PYTHONPATH=src DATA_DIR=./data
  python src/housing/scripts/run_robustness_sweeps.py --k-only
  python src/housing/scripts/run_robustness_sweeps.py --percentile-only
  python src/housing/scripts/run_robustness_sweeps.py --all
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROBUSTNESS = REPO_ROOT / "docs" / "robustness"
K_VALUES = (1, 2, 3, 4, 5)
PERCENTILES = (0.10, 0.15, 0.25, 0.33, 0.50)


def _att_row(
    *,
    sweep: str,
    parameter: str,
    value: str,
    output_dir: Path,
    context: dict,
) -> dict[str, object]:
    """Extract headline CS ATTs and matching counts from pipeline context."""
    matching = context.get("matching_info")
    n_treated = (
        int(matching["treated_tract"].nunique())
        if isinstance(matching, pd.DataFrame) and not matching.empty
        else None
    )
    n_control = (
        int(matching["control_tract"].nunique())
        if isinstance(matching, pd.DataFrame) and not matching.empty
        else None
    )
    reuse = context.get("matching_diagnostics") or {}
    max_reuse = reuse.get("control_reuse_max")

    full = context.get("cs_overall_att_full_panel") or {}
    matched = context.get("cs_overall_att") or {}
    residual = context.get("cs_overall_att_with_controls") or {}

    return {
        "sweep": sweep,
        "parameter": parameter,
        "value": value,
        "output_dir": str(output_dir),
        "n_matched_treated_tracts": n_treated,
        "n_matched_control_tracts": n_control,
        "max_control_reuse": max_reuse,
        "cs_full_panel_att": full.get("att"),
        "cs_full_panel_se": full.get("se"),
        "cs_matched_att": matched.get("att"),
        "cs_matched_se": matched.get("se"),
        "cs_with_controls_att": residual.get("att"),
        "cs_with_controls_se": residual.get("se"),
    }


def run_k_sweep(base_out: Path) -> pd.DataFrame:
    """Loop ``k_neighbors`` 1–5 with ``DID_MATCH_K_NEIGHBORS`` env override."""
    rows: list[dict[str, object]] = []
    k_path = DOCS_ROBUSTNESS / "k_neighbors_sweep_summary.csv"
    for k in K_VALUES:
        out_dir = base_out / f"k{k}"
        os.environ["DID_MATCH_K_NEIGHBORS"] = str(k)
        # Reset percentile to preferred default for k sweep
        os.environ.pop("DID_THRESHOLD_PERCENTILE", None)
        logger.info("=== k_neighbors=%d → %s ===", k, out_dir)
        try:
            from housing.scripts.did_pipeline_callaway_santanna import (
                run_did_analysis_with_cs,
            )

            _, ctx = run_did_analysis_with_cs(
                treatment_mode="threshold",
                output_dir=str(out_dir),
            )
            rows.append(
                _att_row(
                    sweep="k_neighbors",
                    parameter="k_neighbors",
                    value=str(k),
                    output_dir=out_dir,
                    context=ctx,
                )
            )
        except Exception as exc:
            logger.exception("k=%d failed: %s", k, exc)
            rows.append(
                {
                    "sweep": "k_neighbors",
                    "parameter": "k_neighbors",
                    "value": str(k),
                    "output_dir": str(out_dir),
                    "error": str(exc),
                }
            )
        pd.DataFrame(rows).to_csv(k_path, index=False)
        logger.info("Checkpoint %s (%d rows)", k_path, len(rows))
    return pd.DataFrame(rows)


def run_percentile_sweep(base_out: Path) -> pd.DataFrame:
    """Loop threshold percentiles with ``DID_THRESHOLD_PERCENTILE`` env override."""
    rows: list[dict[str, object]] = []
    p_path = DOCS_ROBUSTNESS / "threshold_percentile_sweep_summary.csv"
    os.environ.pop("DID_MATCH_K_NEIGHBORS", None)
    for pct in PERCENTILES:
        tag = f"pct{int(pct * 100):02d}"
        out_dir = base_out / tag
        os.environ["DID_THRESHOLD_PERCENTILE"] = str(pct)
        logger.info("=== percentile=%.2f → %s ===", pct, out_dir)
        try:
            from housing.scripts.did_pipeline_callaway_santanna import (
                run_did_analysis_with_cs,
            )

            _, ctx = run_did_analysis_with_cs(
                treatment_mode="threshold",
                output_dir=str(out_dir),
            )
            panel = ctx.get("did_panel")
            n_treated = (
                int(panel.groupby("tract_geoid")["treated"].max().ge(1).sum())
                if isinstance(panel, pd.DataFrame)
                else None
            )
            row = _att_row(
                sweep="threshold_percentile",
                parameter="percentile",
                value=f"{pct:.2f}",
                output_dir=out_dir,
                context=ctx,
            )
            row["n_ever_treated_tracts"] = n_treated
            rows.append(row)
        except Exception as exc:
            logger.exception("percentile=%.2f failed: %s", pct, exc)
            rows.append(
                {
                    "sweep": "threshold_percentile",
                    "parameter": "percentile",
                    "value": f"{pct:.2f}",
                    "output_dir": str(out_dir),
                    "error": str(exc),
                }
            )
        pd.DataFrame(rows).to_csv(p_path, index=False)
        logger.info("Checkpoint %s (%d rows)", p_path, len(rows))
    return pd.DataFrame(rows)


def main() -> None:
    """Parse CLI flags and write sweep summary CSVs."""
    parser = argparse.ArgumentParser(description="DiD CS robustness sweeps")
    parser.add_argument("--k-only", action="store_true")
    parser.add_argument("--percentile-only", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--output-base",
        default=str(REPO_ROOT / "output" / "did-cs-robustness"),
        help="Root for per-run artefact directories",
    )
    args = parser.parse_args()
    run_k = args.all or args.k_only or (not args.k_only and not args.percentile_only)
    run_pct = (
        args.all
        or args.percentile_only
        or (not args.k_only and not args.percentile_only)
    )

    DOCS_ROBUSTNESS.mkdir(parents=True, exist_ok=True)
    base_out = Path(args.output_base)

    if run_k:
        k_df = run_k_sweep(base_out / "k-neighbors")
        logger.info("k sweep complete: %d rows", len(k_df))

    if run_pct:
        p_df = run_percentile_sweep(base_out / "threshold-percentile")
        logger.info("percentile sweep complete: %d rows", len(p_df))

    # Optional: plots if summaries exist
    try:
        from housing.scripts.plot_robustness_sweeps import main as plot_main

        plot_main()
    except FileNotFoundError:
        logger.warning("Plot step skipped — summary CSVs missing")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
