"""Tract-level cluster block bootstrap for Callaway–Sant'Anna inference.

Resamples census tracts with replacement (same number of clusters as the original
panel), concatenates all months for each sampled tract, and re-runs the CS
estimator on each bootstrap replicate. Produces bootstrap SEs and percentile CIs
for the aggregated event-study curve and for the overall post-treatment ATT.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer

logger = logging.getLogger(__name__)


def resample_panel_by_tract(
    panel: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Build a bootstrap panel by sampling tract clusters with replacement."""
    tract_ids = panel["tract_geoid"].unique()
    n = len(tract_ids)
    if n == 0:
        return panel.iloc[0:0].copy()
    chosen = rng.choice(tract_ids, size=n, replace=True)
    return pd.concat(
        [panel.loc[panel["tract_geoid"] == t].copy() for t in chosen],
        ignore_index=True,
    )


def tract_bootstrap_event_study_and_overall(
    analyzer: CallawaySantAnnaAnalyzer,
    panel: pd.DataFrame,
    event_study_point: pd.DataFrame,
    overall_att_point: dict[str, float],
    *,
    n_reps: int,
    seed: int,
) -> dict[str, Any]:
    """Run ``n_reps`` tract-cluster bootstrap replicates; return tables and metadata.

    For each relative time on the point-estimate grid, bootstrap ATTs that are
    missing in a draw contribute NaN; ``n_valid_draws`` counts finite values.
    Percentile CIs use 2.5 and 97.5 percentiles of the bootstrap distribution of
    the ATT (no bias correction).
    """
    from housing.components.analyzers import callaway_santanna as cs_mod

    cs_log = logging.getLogger(cs_mod.__name__)
    prev_level = cs_log.level

    if event_study_point.empty or "rel_time" not in event_study_point.columns:
        return {
            "event_study_bootstrap": pd.DataFrame(),
            "meta": {
                "n_reps": n_reps,
                "seed": seed,
                "elapsed_sec": 0.0,
                "sec_per_rep": float("nan"),
                "overall_att_point": overall_att_point.get("att"),
                "overall_se_boot": float("nan"),
                "overall_ci_low_boot": float("nan"),
                "overall_ci_high_boot": float("nan"),
                "overall_n_valid_draws": 0,
            },
        }

    rel_grid = event_study_point["rel_time"].to_numpy()
    att_point = event_study_point.set_index("rel_time")["att"]
    se_point = (
        event_study_point.set_index("rel_time")["se"]
        if "se" in event_study_point.columns
        else None
    )

    n_rel = len(rel_grid)
    att_draws = np.full((n_reps, n_rel), np.nan)
    overall_draws = np.full(n_reps, np.nan)

    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()

    try:
        cs_log.setLevel(logging.WARNING)
        for b in range(n_reps):
            panel_b = resample_panel_by_tract(panel, rng)
            core = analyzer.estimate_core_from_panel(panel_b, log_cohort_summary=False)
            es = core["event_study"]
            if not es.empty and "rel_time" in es.columns and "att" in es.columns:
                es_idx = es.drop_duplicates(subset=["rel_time"]).set_index("rel_time")[
                    "att"
                ]
                for j, e in enumerate(rel_grid):
                    if e in es_idx.index:
                        att_draws[b, j] = float(es_idx.loc[e])
            ov = core["overall_att"]
            att_ov = ov.get("att")
            if att_ov is not None and pd.notna(att_ov):
                try:
                    fv = float(att_ov)
                    if np.isfinite(fv):
                        overall_draws[b] = fv
                except (TypeError, ValueError):
                    pass
    finally:
        cs_log.setLevel(prev_level)

    elapsed = time.perf_counter() - t0

    rows: list[dict[str, Any]] = []
    for j, e in enumerate(rel_grid):
        col = att_draws[:, j]
        valid = np.isfinite(col)
        n_valid = int(valid.sum())
        if n_valid > 1:
            se_boot = float(np.nanstd(col, ddof=1))
            ci_lo = float(np.nanpercentile(col[valid], 2.5))
            ci_hi = float(np.nanpercentile(col[valid], 97.5))
            mean_b = float(np.nanmean(col))
        elif n_valid == 1:
            se_boot = float("nan")
            ci_lo = ci_hi = mean_b = float(col[valid][0])
        else:
            se_boot = ci_lo = ci_hi = mean_b = float("nan")
        row: dict[str, Any] = {
            "rel_time": e,
            "att_point": float(att_point.loc[e])
            if e in att_point.index
            else float("nan"),
            "se_boot": se_boot,
            "ci_low_boot": ci_lo,
            "ci_high_boot": ci_hi,
            "mean_att_boot": mean_b,
            "n_valid_draws": n_valid,
        }
        if se_point is not None and e in se_point.index:
            row["se_analytic"] = float(se_point.loc[e])
        rows.append(row)

    boot_df = pd.DataFrame(rows)

    ov_valid = np.isfinite(overall_draws)
    ov_n = int(ov_valid.sum())
    if ov_n > 1:
        ov_se = float(np.nanstd(overall_draws, ddof=1))
        ov_ci_lo = float(np.nanpercentile(overall_draws[ov_valid], 2.5))
        ov_ci_hi = float(np.nanpercentile(overall_draws[ov_valid], 97.5))
    elif ov_n == 1:
        ov_se = float("nan")
        v = float(overall_draws[ov_valid][0])
        ov_ci_lo = ov_ci_hi = v
    else:
        ov_se = ov_ci_lo = ov_ci_hi = float("nan")

    meta = {
        "n_reps": n_reps,
        "seed": seed,
        "elapsed_sec": float(elapsed),
        "sec_per_rep": float(elapsed / n_reps) if n_reps > 0 else float("nan"),
        "overall_att_point": overall_att_point.get("att"),
        "overall_se_analytic": overall_att_point.get("se"),
        "overall_se_boot": ov_se,
        "overall_ci_low_boot": ov_ci_lo,
        "overall_ci_high_boot": ov_ci_hi,
        "overall_n_valid_draws": ov_n,
    }

    logger.info(
        "Tract bootstrap complete: %d reps, %.1fs (%.2fs/rep), overall valid draws=%d",
        n_reps,
        elapsed,
        elapsed / n_reps if n_reps else float("nan"),
        ov_n,
    )

    return {"event_study_bootstrap": boot_df, "meta": meta}


def parse_cs_bootstrap_cli() -> tuple[int | None, int]:
    """Parse ``--cs-bootstrap-reps`` / ``--cs-bootstrap-seed`` and env ``CS_BOOTSTRAP_REPS``.

    Strips a single leading ``--`` from argv (e.g. from ``docker compose run ... --
    --cs-bootstrap-reps N``) so argparse still sees the bootstrap flags.
    """
    import argparse
    import os
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cs-bootstrap-reps",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Tract-cluster block bootstrap replicates for baseline CS (default: "
            "env CS_BOOTSTRAP_REPS if set, else off)"
        ),
    )
    parser.add_argument(
        "--cs-bootstrap-seed",
        type=int,
        default=0,
        help="RNG seed for tract bootstrap",
    )
    args, _unknown = parser.parse_known_args(argv)
    reps = args.cs_bootstrap_reps
    if reps is not None and reps <= 0:
        reps = None
    if reps is None:
        env = os.environ.get("CS_BOOTSTRAP_REPS", "").strip()
        if env:
            ev = int(env)
            reps = ev if ev > 0 else None
    return reps, int(args.cs_bootstrap_seed)


def write_cs_bootstrap_csv(
    boot_df: pd.DataFrame, meta: dict[str, Any], out_dir: str
) -> str:
    """Write ``cs_event_study_tract_bootstrap.csv``; return path."""
    path = f"{out_dir.rstrip('/')}/cs_event_study_tract_bootstrap.csv"
    boot_df.to_csv(path, index=False)
    meta_path = f"{out_dir.rstrip('/')}/cs_tract_bootstrap_meta.csv"
    pd.DataFrame([meta]).to_csv(meta_path, index=False)
    logger.info("Wrote %s and %s", path, meta_path)
    return path
