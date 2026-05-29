"""Tests for CS post-treatment trajectory analyzer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from housing.components.analyzers.callaway_santanna_trajectory import (
    CallawaySantAnnaTrajectoryAnalyzer,
    _wls_beta_cov,
    predicted_trajectory,
)


def test_wls_linear_recover_coefficients() -> None:
    """WLS recovers intercept and slope on noiseless linear data."""
    n = 20
    e = np.arange(n, dtype=float)
    y = 2.0 + 0.5 * e
    w = np.ones(n)
    X = np.column_stack([np.ones(n), e])
    beta, _, rss = _wls_beta_cov(X, y, w)
    assert np.allclose(beta, [2.0, 0.5], rtol=1e-5)
    assert rss < 1e-8


def test_trajectory_growing_synthetic() -> None:
    """Strong upward linear path → growing classification."""
    rel = np.arange(0, 25)
    att = 0.3 * rel.astype(float)
    se = np.full_like(att, 0.05, dtype=float)
    es = pd.DataFrame({"rel_time": rel, "att": att, "se": se})
    ctx = {"cs_event_study": es}
    out = CallawaySantAnnaTrajectoryAnalyzer().execute(ctx)["cs_trajectory_results"]
    assert out["classification"] == "growing"
    assert (
        "linear_slope_positive" in out["classification_detail"]
        or "late_gt_early" in out["classification_detail"]
    )
    fits = out["fits"]
    assert fits["linear"]["coefficients"]["slope_e"] > 0
    yhat = predicted_trajectory(np.array([0.0, 10.0, 20.0]), "linear", fits)
    assert yhat[2] > yhat[0]


def test_predicted_trajectory_unknown_model() -> None:
    """``predicted_trajectory`` raises for an unsupported model name."""
    with pytest.raises(ValueError, match="unknown model"):
        predicted_trajectory([0.0], "cubic", {})
