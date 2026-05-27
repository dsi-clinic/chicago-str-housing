"""Tests for tract-cluster block bootstrap around Callaway–Sant'Anna."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_tract_bootstrap import (
    parse_cs_bootstrap_cli,
    resample_panel_by_tract,
    tract_bootstrap_event_study_and_overall,
)


def _synthetic_staggered_panel(*, n_months: int = 30) -> pd.DataFrame:
    """Small staggered panel: 2 never-treated + 2 treated (one cohort)."""
    months = pd.date_range("2019-01-01", periods=n_months, freq="MS")
    treat_start = pd.Timestamp("2020-06-01")
    rows: list[dict] = []
    for tid in ("NEV1", "NEV2"):
        for m in months:
            rows.append(
                {
                    "tract_geoid": tid,
                    "month": m,
                    "rental_price": 1000.0 + 0.1 * (m - months[0]).days // 30,
                    "treated": 0,
                }
            )
    for tid in ("TR1", "TR2"):
        for m in months:
            tr = 1 if m >= treat_start else 0
            level = 1000.0 + 0.1 * (m - months[0]).days // 30 + (25.0 if tr else 0.0)
            rows.append(
                {
                    "tract_geoid": tid,
                    "month": m,
                    "rental_price": level,
                    "treated": tr,
                }
            )
    return pd.DataFrame(rows)


def test_resample_panel_by_tract_shape_and_rng() -> None:
    """Resampled panel concatenates full monthly series per sampled tract."""
    panel = _synthetic_staggered_panel()
    rng = np.random.default_rng(0)
    boot = resample_panel_by_tract(panel, rng)
    n_orig = panel["tract_geoid"].nunique()
    assert boot["tract_geoid"].nunique() <= n_orig
    assert len(boot) == len(panel)


def test_estimate_core_from_panel_matches_execute_shape() -> None:
    """Core CS path returns a non-empty event study on synthetic staggered data."""
    panel = _synthetic_staggered_panel()
    az = CallawaySantAnnaAnalyzer(
        comparison_group="nevertreated",
        min_cohort_size=2,
    )
    core = az.estimate_core_from_panel(panel, log_cohort_summary=False)
    assert not core["event_study"].empty
    assert "rel_time" in core["event_study"].columns
    assert "att" in core["event_study"].columns


def test_tract_bootstrap_produces_columns() -> None:
    """Bootstrap table includes SE, percentile CIs, and per-rel_time valid draw counts."""
    panel = _synthetic_staggered_panel()
    az = CallawaySantAnnaAnalyzer(
        comparison_group="nevertreated",
        min_cohort_size=2,
    )
    core = az.estimate_core_from_panel(panel, log_cohort_summary=False)
    es = core["event_study"]
    overall = core["overall_att"]
    out = tract_bootstrap_event_study_and_overall(
        az,
        panel,
        es,
        overall,
        n_reps=25,
        seed=42,
    )
    boot_df = out["event_study_bootstrap"]
    meta = out["meta"]
    assert not boot_df.empty
    assert "se_boot" in boot_df.columns
    assert "ci_low_boot" in boot_df.columns
    assert "n_valid_draws" in boot_df.columns
    assert meta["n_reps"] == 25
    assert meta["seed"] == 42
    assert meta["elapsed_sec"] >= 0
    # At least one rel_time should have multiple valid bootstrap draws
    assert (boot_df["n_valid_draws"] >= 2).any()


def test_parse_cs_bootstrap_cli_strips_leading_double_dash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading ``--`` (e.g. from Docker) must not hide bootstrap flags from argparse."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--", "--cs-bootstrap-reps", "12", "--cs-bootstrap-seed", "3"],
    )
    reps, seed = parse_cs_bootstrap_cli()
    assert reps == 12
    assert seed == 3


def test_parse_cs_bootstrap_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--cs-bootstrap-reps`` / ``--cs-bootstrap-seed`` override defaults; env optional."""
    monkeypatch.setattr(
        sys, "argv", ["prog", "--cs-bootstrap-reps", "50", "--cs-bootstrap-seed", "7"]
    )
    reps, seed = parse_cs_bootstrap_cli()
    assert reps == 50
    assert seed == 7

    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.delenv("CS_BOOTSTRAP_REPS", raising=False)
    reps2, seed2 = parse_cs_bootstrap_cli()
    assert reps2 is None
    assert seed2 == 0
