"""Joint pre-trend tests for Callaway–Sant'Anna event-study ATTs.

Tests H0: all pre-treatment event-study ATTs are jointly zero, using a Wald
statistic with a diagonal variance matrix (treating relative-time estimates as
independent). Pre-period ATTs at different ``rel_time`` are positively
correlated in practice; this test can be anti-conservative. Prefer wild
cluster bootstrap at the tract level when a full covariance is available.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# Match ``MAX_PRE_TIME`` in ``callaway_santanna.py`` (months of pre window)
DEFAULT_REL_TIME_MIN = -12
DEFAULT_REL_TIME_MAX = -1

METHOD_DIAGONAL_WALD = "Wald_chi2_diagonal_V_independence_across_rel_time_approximation"


def compute_pre_trend_joint_test_from_cs_event_study(
    event_study: pd.DataFrame | None,
    *,
    rel_time_min: int = DEFAULT_REL_TIME_MIN,
    rel_time_max: int = DEFAULT_REL_TIME_MAX,
    att_col: str = "att",
    se_col: str = "se",
    rel_time_col: str = "rel_time",
) -> dict[str, Any]:
    """Joint Wald test that pre-treatment CS ATTs are all zero.

    Uses W = Σ (ATT_e / SE_e)² with SE_e from the event-study table, compared to
    a chi-squared(k) reference where k is the number of pre-periods used.
    Independence across ``rel_time`` is assumed for that reference distribution.

    Returns:
        ``summary``: JSON-serializable dict (wald, df, p_value, method, counts).
        ``periods``: DataFrame of rows used (rel_time, att, se, z, z_squared).
    """
    empty_periods = pd.DataFrame(
        columns=[rel_time_col, att_col, se_col, "z", "z_squared"]
    )
    base_summary: dict[str, Any] = {
        "wald_statistic": float("nan"),
        "degrees_of_freedom": 0,
        "p_value": float("nan"),
        "rel_time_min": rel_time_min,
        "rel_time_max": rel_time_max,
        "method": METHOD_DIAGONAL_WALD,
        "n_periods_used": 0,
        "n_periods_dropped_se": 0,
        "note": "",
    }

    if event_study is None or event_study.empty:
        base_summary["note"] = "empty_event_study"
        return {"summary": base_summary, "periods": empty_periods}

    for col in (rel_time_col, att_col, se_col):
        if col not in event_study.columns:
            base_summary["note"] = f"missing_column:{col}"
            return {"summary": base_summary, "periods": empty_periods}

    sub = event_study[
        (event_study[rel_time_col] >= rel_time_min)
        & (event_study[rel_time_col] <= rel_time_max)
    ].copy()
    sub = sub.sort_values(rel_time_col)

    if sub.empty:
        base_summary["note"] = "no_rows_in_rel_time_window"
        return {"summary": base_summary, "periods": empty_periods}

    se_bad = sub[se_col].isna() | (sub[se_col] <= 0) | np.isinf(sub[se_col])
    n_dropped = int(se_bad.sum())
    if n_dropped:
        logger.warning(
            "Pre-trend joint test: dropping %d pre-period rows with missing or "
            "non-positive SE.",
            n_dropped,
        )
    sub = sub.loc[~se_bad].copy()

    if sub.empty:
        base_summary["note"] = "all_pre_periods_dropped_bad_se"
        base_summary["n_periods_dropped_se"] = n_dropped
        return {"summary": base_summary, "periods": empty_periods}

    att = sub[att_col].to_numpy(dtype=float)
    se = sub[se_col].to_numpy(dtype=float)
    z = att / se
    z2 = z * z
    wald = float(np.nansum(z2))
    k = int(len(z))
    dof_chi2 = k
    p_value = (
        float(1.0 - stats.chi2.cdf(wald, dof_chi2)) if dof_chi2 > 0 else float("nan")
    )

    periods = pd.DataFrame(
        {
            rel_time_col: sub[rel_time_col].to_numpy(),
            att_col: att,
            se_col: se,
            "z": z,
            "z_squared": z2,
        }
    )

    summary = {
        "wald_statistic": wald,
        "degrees_of_freedom": dof_chi2,
        "p_value": p_value,
        "rel_time_min": rel_time_min,
        "rel_time_max": rel_time_max,
        "method": METHOD_DIAGONAL_WALD,
        "n_periods_used": k,
        "n_periods_dropped_se": n_dropped,
        "note": "",
    }
    return {"summary": summary, "periods": periods}


def write_pre_trend_joint_test_outputs(
    output_dir: str,
    summary: dict[str, Any],
    periods: pd.DataFrame,
    *,
    aggregate_basename: str = "cs_pre_trend_joint_test_aggregate",
    periods_basename: str = "cs_pre_trend_joint_test_periods",
) -> tuple[str, str | None]:
    """Write aggregate summary and per-period table to CSV under ``output_dir``."""
    from pathlib import Path

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    agg_path = out / f"{aggregate_basename}.csv"
    pd.DataFrame([summary]).to_csv(agg_path, index=False)

    per_path_f: Path | None = out / f"{periods_basename}.csv"
    if periods is not None and not periods.empty:
        periods.to_csv(per_path_f, index=False)
    else:
        per_path_f = None

    return str(agg_path), str(per_path_f) if per_path_f else None


def log_and_export_pre_trend_joint_test(
    results: dict[str, Any],
    output_dir: str,
    *,
    summary_key: str = "cs_pre_trend_joint_test",
    periods_key: str = "cs_pre_trend_joint_test_periods",
    aggregate_basename: str = "cs_pre_trend_joint_test_aggregate",
    periods_basename: str = "cs_pre_trend_joint_test_periods",
    label: str = "Callaway–Sant'Anna (baseline)",
) -> None:
    """Log joint pre-trend test and write CSVs if results are present."""
    summary = results.get(summary_key)
    if not summary or not isinstance(summary, dict):
        return

    periods = results.get(periods_key)
    if not isinstance(periods, pd.DataFrame):
        periods = pd.DataFrame()

    w = summary.get("wald_statistic", float("nan"))
    df_ = summary.get("degrees_of_freedom", 0)
    p = summary.get("p_value", float("nan"))
    rmin = summary.get("rel_time_min", DEFAULT_REL_TIME_MIN)
    rmax = summary.get("rel_time_max", DEFAULT_REL_TIME_MAX)
    n_used = summary.get("n_periods_used", 0)
    note = summary.get("note", "")

    if df_ > 0 and np.isfinite(p):
        logger.info(
            "\n%s — pre-treatment joint test (H0: ATTs = 0 for rel_time in [%d, %d]):",
            label,
            rmin,
            rmax,
        )
        logger.info("  Wald statistic: %.4f", w)
        logger.info("  Degrees of freedom: %d", int(df_))
        logger.info("  P-value (chi-squared reference, diagonal V): %.4f", p)
        logger.info("  Pre-periods used: %d", int(n_used))
        if note:
            logger.info("  Note: %s", note)
    else:
        logger.warning(
            "%s — pre-treatment joint test not computed (%s).",
            label,
            note or "insufficient_data",
        )

    agg_p, per_p = write_pre_trend_joint_test_outputs(
        output_dir,
        summary,
        periods,
        aggregate_basename=aggregate_basename,
        periods_basename=periods_basename,
    )
    logger.info("  Wrote aggregate: %s", agg_p)
    if per_p:
        logger.info("  Wrote per-period contributions: %s", per_p)
