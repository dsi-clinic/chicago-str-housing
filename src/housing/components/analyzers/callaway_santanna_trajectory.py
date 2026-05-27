"""Post-treatment dynamic trajectory from CS event-study ATTs (growth vs. plateau).

Fits weighted least squares (weights 1 / SE^2) to the post-treatment path
(``rel_time`` >= 0), compares linear / log / quadratic specifications, and
classifies the trajectory. Optional bootstrap SEs from
``cs_event_study_tract_bootstrap`` improve phase-average inference when present.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from housing.did_spec import (
    DID_CS_TRAJECTORY_PHASE_BOUNDARIES,
    DID_CS_TRAJECTORY_PHASE_LABELS,
)
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

# Minimum post-treatment rows with finite SE for WLS
_MIN_POST_ROWS = 5

_TRAJECTORY_PLATEAU_CURVATURE_ALPHA = 0.10
_TRAJECTORY_GROWING_SLOPE_ALPHA = 0.05
_TRAJECTORY_GROWING_PHASE_ALPHA = 0.05
_TRAJECTORY_AMBIGUOUS_SLOPE_ALPHA = 0.15
_TRAJECTORY_LOG_AIC_IMPROVEMENT = 2.0
_TRAJECTORY_LOG_VS_QUAD_BAND = 2.0


def _wls_beta_cov(
    X: np.ndarray, y: np.ndarray, w: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float]:
    """Weighted least squares: minimize sum w_i (y_i - x_i' beta)^2.

    Returns (beta, cov_beta, rss_weighted).
    """
    n, k = X.shape
    XtW = X.T * w
    XtWX = XtW @ X
    XtWy = XtW @ y
    try:
        beta = np.linalg.solve(XtWX, XtWy)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(XtWX, XtWy, rcond=None)[0]
    resid = y - X @ beta
    rss = float(np.sum(w * resid**2))
    dof = max(n - k, 1)
    sigma2 = rss / dof
    try:
        cov = sigma2 * np.linalg.inv(XtWX)
    except np.linalg.LinAlgError:
        cov = np.full((k, k), np.nan)
    return beta, cov, rss


def _phase_inverse_variance_mean(
    df: pd.DataFrame,
    lo: int,
    hi: int,
    *,
    att_col: str = "att",
    se_col: str = "se",
) -> dict[str, float]:
    """Inverse-variance weighted mean of ``att`` over ``rel_time`` in [lo, hi]."""
    sub = df[(df["rel_time"] >= lo) & (df["rel_time"] <= hi)].copy()
    if sub.empty or att_col not in sub.columns or se_col not in sub.columns:
        return {
            "att": float("nan"),
            "se": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "n_periods": 0.0,
        }
    att = sub[att_col].to_numpy(dtype=float)
    se = sub[se_col].to_numpy(dtype=float)
    ok = np.isfinite(att) & np.isfinite(se) & (se > 0)
    if ok.sum() == 0:
        return {
            "att": float("nan"),
            "se": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "n_periods": float(len(sub)),
        }
    att, se = att[ok], se[ok]
    w = 1.0 / (se**2)
    num = float(np.sum(w * att))
    den = float(np.sum(w))
    m = num / den
    m_se = math.sqrt(1.0 / den) if den > 0 else float("nan")
    return {
        "att": m,
        "se": m_se,
        "ci_low": m - 1.96 * m_se,
        "ci_high": m + 1.96 * m_se,
        "n_periods": float(ok.sum()),
    }


def _aic_wls(n: int, rss: float, k: int) -> float:
    """Gaussian AIC on weighted RSS (same n for comparison across nested models)."""
    if n <= 0 or rss <= 0 or not math.isfinite(rss):
        return float("nan")
    return float(n * math.log(rss / n) + 2 * k)


def _f_test_nested(
    rss_small: float, rss_big: float, n: int, k_small: int, k_big: int
) -> tuple[float, float]:
    """F-test: does the bigger model significantly reduce RSS vs nested smaller?"""
    df1 = k_big - k_small
    df2 = n - k_big
    if df1 <= 0 or df2 <= 0 or rss_big <= 0:
        return float("nan"), float("nan")
    num = (rss_small - rss_big) / df1
    den = rss_big / df2
    if den <= 0:
        return float("nan"), float("nan")
    f_stat = num / den
    p_val = float(stats.f.sf(f_stat, df1, df2))
    return float(f_stat), p_val


class CallawaySantAnnaTrajectoryAnalyzer(Analyzer):
    """Characterize CS post-treatment ATT path (linear growth vs. plateau)."""

    def __init__(
        self,
        phase_boundaries: tuple[tuple[int, int], ...] | None = None,
        phase_labels: tuple[str, ...] | None = None,
    ) -> None:
        """Use defaults from :mod:`housing.did_spec` when boundaries/labels are omitted."""
        super().__init__(
            "callaway_santanna_trajectory_analysis",
            "CS event-study post-treatment trajectory (WLS fits, phase averages)",
        )
        self.phase_boundaries = phase_boundaries or DID_CS_TRAJECTORY_PHASE_BOUNDARIES
        self.phase_labels = phase_labels or DID_CS_TRAJECTORY_PHASE_LABELS
        if len(self.phase_boundaries) != len(self.phase_labels):
            raise ValueError("phase_boundaries and phase_labels must have same length")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Build ``cs_trajectory_results`` from ``cs_event_study`` and optional bootstrap table."""
        es = context.get("cs_event_study")
        if es is None or not isinstance(es, pd.DataFrame) or es.empty:
            raise ValueError("cs_event_study missing or empty")
        if (
            "rel_time" not in es.columns
            or "att" not in es.columns
            or "se" not in es.columns
        ):
            raise ValueError("cs_event_study must have rel_time, att, se")

        post = es[es["rel_time"] >= 0].sort_values("rel_time").copy()
        post = post[
            np.isfinite(post["att"]) & np.isfinite(post["se"]) & (post["se"] > 0)
        ]

        boot_df = context.get("cs_event_study_tract_bootstrap")
        phase_se_column = "se"
        boot_meta: dict[str, Any] = {}
        if (
            isinstance(boot_df, pd.DataFrame)
            and not boot_df.empty
            and "se_boot" in boot_df.columns
        ):
            phase_se_column = "se_boot"
            post = post.merge(
                boot_df[["rel_time", "se_boot"]],
                on="rel_time",
                how="left",
            )
            if post["se_boot"].notna().any():
                post["se_phase"] = post["se_boot"].where(
                    post["se_boot"].notna() & (post["se_boot"] > 0), post["se"]
                )
            else:
                post["se_phase"] = post["se"]
            boot_meta["used_bootstrap_se_for_phases"] = True
        else:
            post["se_phase"] = post["se"]
            boot_meta["used_bootstrap_se_for_phases"] = False

        # Phase averages (analytic SE for WLS path; se_phase for descriptive phases)
        phases_rows: list[dict[str, Any]] = []
        for label, (lo, hi) in zip(self.phase_labels, self.phase_boundaries):
            iv = _phase_inverse_variance_mean(
                post, lo, hi, att_col="att", se_col="se_phase"
            )
            phases_rows.append({"phase": label, "rel_lo": lo, "rel_hi": hi, **iv})
        phases_df = pd.DataFrame(phases_rows)

        # Late vs early (for classification)
        early_att = phases_df.loc[phases_df["phase"] == "early", "att"]
        late_att = phases_df.loc[phases_df["phase"] == "late", "att"]
        early_se = phases_df.loc[phases_df["phase"] == "early", "se"]
        late_se = phases_df.loc[phases_df["phase"] == "late", "se"]
        late_minus_early = float("nan")
        late_minus_early_se = float("nan")
        late_minus_early_z = float("nan")
        late_minus_early_p = float("nan")
        if (
            len(early_att) == 1
            and len(late_att) == 1
            and early_se.iloc[0] > 0
            and late_se.iloc[0] > 0
        ):
            late_minus_early = float(late_att.iloc[0] - early_att.iloc[0])
            late_minus_early_se = math.sqrt(
                early_se.iloc[0] ** 2 + late_se.iloc[0] ** 2
            )
            if late_minus_early_se > 0:
                late_minus_early_z = late_minus_early / late_minus_early_se
                late_minus_early_p = float(
                    2 * (1 - stats.norm.cdf(abs(late_minus_early_z)))
                )

        n = len(post)
        if n < _MIN_POST_ROWS:
            logger.warning(
                "Too few post-treatment event-study points (%d) for trajectory WLS",
                n,
            )
            out = {
                "post_event_study": post,
                "phases": phases_df,
                "fits": {},
                "curvature_test": {},
                "classification": "insufficient_data",
                "classification_detail": f"n_post={n} < {_MIN_POST_ROWS}",
                "late_minus_early": {
                    "estimate": late_minus_early,
                    "se": late_minus_early_se,
                    "z": late_minus_early_z,
                    "p_value": late_minus_early_p,
                },
                "bootstrap_meta": boot_meta,
            }
            return {"cs_trajectory_results": out}

        e = post["rel_time"].to_numpy(dtype=float)
        y = post["att"].to_numpy(dtype=float)
        w = 1.0 / (post["se"].to_numpy(dtype=float) ** 2)

        # Linear: y = b0 + b1 * e
        X1 = np.column_stack([np.ones(n), e])
        b1, cov1, rss1 = _wls_beta_cov(X1, y, w)
        se_b1 = math.sqrt(cov1[1, 1]) if cov1.shape == (2, 2) else float("nan")
        p_b1 = (
            float(2 * (1 - stats.norm.cdf(abs(b1[1] / se_b1))))
            if se_b1 > 0 and math.isfinite(se_b1)
            else float("nan")
        )

        # Log: y = b0 + b1 * log(1+e)
        loge = np.log1p(e)
        Xlog = np.column_stack([np.ones(n), loge])
        blog, covlog, rsslog = _wls_beta_cov(Xlog, y, w)

        # Quadratic: y = b0 + b1*e + b2*e^2
        Xq = np.column_stack([np.ones(n), e, e**2])
        bq, covq, rssq = _wls_beta_cov(Xq, y, w)
        se_b2 = math.sqrt(covq[2, 2]) if covq.shape == (3, 3) else float("nan")
        p_b2 = (
            float(2 * (1 - stats.norm.cdf(abs(bq[2] / se_b2))))
            if se_b2 > 0 and math.isfinite(se_b2)
            else float("nan")
        )

        f_quad_vs_lin, p_quad_vs_lin = _f_test_nested(rss1, rssq, n, 2, 3)

        aic_lin = _aic_wls(n, rss1, 2)
        aic_log = _aic_wls(n, rsslog, 2)
        aic_quad = _aic_wls(n, rssq, 3)

        fits = {
            "linear": {
                "coefficients": {"intercept": float(b1[0]), "slope_e": float(b1[1])},
                "coefficient_se": {
                    "intercept": float(math.sqrt(cov1[0, 0])),
                    "slope_e": se_b1,
                },
                "slope_e_p_value": p_b1,
                "rss_weighted": rss1,
                "aic": aic_lin,
                "n": n,
            },
            "log": {
                "coefficients": {
                    "intercept": float(blog[0]),
                    "slope_log1p_e": float(blog[1]),
                },
                "rss_weighted": rsslog,
                "aic": aic_log,
                "n": n,
            },
            "quadratic": {
                "coefficients": {
                    "intercept": float(bq[0]),
                    "slope_e": float(bq[1]),
                    "curvature_e2": float(bq[2]),
                },
                "curvature_se": se_b2,
                "curvature_p_value": p_b2,
                "rss_weighted": rssq,
                "aic": aic_quad,
                "n": n,
            },
        }

        curvature_test = {
            "f_statistic_quadratic_vs_linear": f_quad_vs_lin,
            "p_value_quadratic_vs_linear": p_quad_vs_lin,
            "quadratic_curvature_coef": float(bq[2]),
        }

        classification, detail = self._classify(
            fits=fits,
            curvature_test=curvature_test,
            late_minus_early_p=late_minus_early_p,
            late_minus_early=late_minus_early,
        )

        out = {
            "post_event_study": post,
            "phases": phases_df,
            "fits": fits,
            "curvature_test": curvature_test,
            "classification": classification,
            "classification_detail": detail,
            "late_minus_early": {
                "estimate": late_minus_early,
                "se": late_minus_early_se,
                "z": late_minus_early_z,
                "p_value": late_minus_early_p,
            },
            "bootstrap_meta": {**boot_meta, "phase_se_column": phase_se_column},
        }
        logger.info(
            "CS trajectory: %s (%s); linear slope=%.4f (p=%.4g); quad vs lin p=%.4g",
            classification,
            detail,
            float(b1[1]),
            p_b1,
            p_quad_vs_lin,
        )
        return {"cs_trajectory_results": out}

    def _classify(
        self,
        *,
        fits: dict[str, Any],
        curvature_test: dict[str, Any],
        late_minus_early_p: float,
        late_minus_early: float,
    ) -> tuple[str, str]:
        """Return (classification, short rationale)."""
        lin = fits["linear"]
        quad = fits["quadratic"]
        log = fits["log"]
        slope = lin["coefficients"]["slope_e"]
        p_slope = lin["slope_e_p_value"]
        p_f = curvature_test["p_value_quadratic_vs_linear"]
        c2 = curvature_test["quadratic_curvature_coef"]

        aic_lin = lin["aic"]
        aic_log = log["aic"]
        aic_quad = quad["aic"]

        # Plateau: significant negative curvature OR log clearly beats linear (concave)
        plateau_curvature = (
            math.isfinite(p_f)
            and p_f < _TRAJECTORY_PLATEAU_CURVATURE_ALPHA
            and math.isfinite(c2)
            and c2 < 0
        )
        plateau_aic_log = (
            math.isfinite(aic_lin)
            and math.isfinite(aic_log)
            and (aic_log < aic_lin - _TRAJECTORY_LOG_AIC_IMPROVEMENT)
            and (
                aic_log <= aic_quad + _TRAJECTORY_LOG_VS_QUAD_BAND
                or not math.isfinite(aic_quad)
            )
        )
        if plateau_curvature or plateau_aic_log:
            reason = []
            if plateau_curvature:
                reason.append("quad_curvature_negative_or_f_test")
            if plateau_aic_log:
                reason.append("log_AIC_beats_linear")
            return "plateau", "; ".join(reason)

        # Growing: positive slope, significant at 5%, and late > early consistent
        growing_slope = (
            math.isfinite(slope)
            and math.isfinite(p_slope)
            and slope > 0
            and p_slope < _TRAJECTORY_GROWING_SLOPE_ALPHA
        )
        growing_phases = (
            math.isfinite(late_minus_early)
            and late_minus_early > 0
            and math.isfinite(late_minus_early_p)
            and late_minus_early_p < _TRAJECTORY_GROWING_PHASE_ALPHA
        )
        if growing_slope or growing_phases:
            reason = []
            if growing_slope:
                reason.append("linear_slope_positive")
            if growing_phases:
                reason.append("late_gt_early")
            return "growing", "; ".join(reason)

        # Weak growth signal
        if (
            math.isfinite(slope)
            and slope > 0
            and math.isfinite(p_slope)
            and p_slope < _TRAJECTORY_AMBIGUOUS_SLOPE_ALPHA
        ):
            return "ambiguous", "positive_slope_marginal"

        return "ambiguous", "no_clear_growth_or_plateau"


def predicted_trajectory(
    rel_times: np.ndarray | list[float],
    model: str,
    fits: dict[str, Any],
) -> np.ndarray:
    """Evaluate fitted ``model`` ('linear', 'log', 'quadratic') on ``rel_times``."""
    t = np.asarray(rel_times, dtype=float)
    if model == "linear":
        b = fits["linear"]["coefficients"]
        return b["intercept"] + b["slope_e"] * t
    if model == "log":
        b = fits["log"]["coefficients"]
        return b["intercept"] + b["slope_log1p_e"] * np.log1p(t)
    if model == "quadratic":
        b = fits["quadratic"]["coefficients"]
        return b["intercept"] + b["slope_e"] * t + b["curvature_e2"] * (t**2)
    raise ValueError(f"unknown model: {model}")
