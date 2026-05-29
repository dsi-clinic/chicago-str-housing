"""Long-format tables for sample / matching / covariate storytelling (slides + appendices)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

_MIN_OBS_FOR_VAR = 2

# Tract-level covariates often present after DIDCovariateProcessor
_COVARIATE_NUMERIC = (
    "median_income",
    "median_house_value",
    "median_age",
    "pct_bachelor",
    "pct_rented",
    "total_population",
    "baseline_rent",
)


def _pooled_smd(treated: pd.Series, control: pd.Series) -> float:
    t = treated.dropna()
    c = control.dropna()
    if len(t) < _MIN_OBS_FOR_VAR or len(c) < _MIN_OBS_FOR_VAR:
        return float("nan")
    tv = t.var(ddof=1)
    cv = c.var(ddof=1)
    pooled = ((tv + cv) / 2) ** 0.5
    if pooled == 0 or pd.isna(pooled):
        return float("nan")
    return float((t.mean() - c.mean()) / pooled)


class DIDStoryTablesAnalyzer(Analyzer):
    """Write CSVs that feed ``DIDStoryGraphicsVisualizer`` and external plotting tools."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the story-tables analyzer.

        Args:
            output_dir: Directory for ``did_story_*.csv`` tables.
        """
        super().__init__(
            "did_story_tables",
            "Build long-format DiD story tables (matching balance, pre-period covariates)",
        )
        self.output_dir = output_dir
        self.required_data = ["did_panel"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Emit long-format CSVs from ``did_panel`` and optional matching diagnostics."""
        if not self.output_dir:
            logger.info("did_story_tables: no output_dir; skipping CSV writes")
            return {}

        out = Path(self.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        did_panel = context["did_panel"].copy()
        if "ever_treated" not in did_panel.columns:
            did_panel["ever_treated"] = (
                did_panel.groupby("tract_geoid")["treated"].transform("max").astype(int)
            )

        matching_diag = context.get("matching_diagnostics")
        love_long = self._love_plot_long(matching_diag)
        if love_long is not None and not love_long.empty:
            path = out / "did_story_matching_balance_long.csv"
            love_long.to_csv(path, index=False)
            logger.info("Wrote %s", path)

        cov_long = self._covariate_smd_pre_match(did_panel)
        if cov_long is not None and not cov_long.empty:
            path = out / "did_story_covariate_smd_pre.csv"
            cov_long.to_csv(path, index=False)
            logger.info("Wrote %s", path)

        treat_profile = self._treatment_tract_profile(did_panel)
        if treat_profile is not None and not treat_profile.empty:
            path = out / "did_story_treatment_tract_profile.csv"
            treat_profile.to_csv(path, index=False)
            logger.info("Wrote %s", path)

        return {
            "did_story_matching_balance_long": love_long,
            "did_story_covariate_smd_pre": cov_long,
            "did_story_treatment_tract_profile": treat_profile,
        }

    @staticmethod
    def _love_plot_long(matching_diag: dict[str, Any] | None) -> pd.DataFrame | None:
        if not matching_diag or not isinstance(matching_diag, dict):
            return None
        raw_features = matching_diag.get("matching_features") or ""
        features = [f.strip() for f in str(raw_features).split(",") if f.strip()]
        rows: list[dict[str, Any]] = []
        for feat in features:
            b = matching_diag.get(f"smd_{feat}_before")
            a = matching_diag.get(f"smd_{feat}_after")
            if b is None and a is None:
                continue
            label = feat.replace("_", " ").title()
            rows.append(
                {
                    "feature": feat,
                    "feature_label": label,
                    "smd_before": b,
                    "smd_after": a,
                },
            )
        return pd.DataFrame(rows) if rows else None

    def _covariate_smd_pre_match(self, did_panel: pd.DataFrame) -> pd.DataFrame | None:
        first_t = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        if pd.isna(first_t):
            return None
        did_panel["month"] = pd.to_datetime(did_panel["month"])
        pre = did_panel[did_panel["month"] < first_t].copy()
        rows: list[dict[str, Any]] = []
        for col in _COVARIATE_NUMERIC:
            if col not in pre.columns:
                continue
            tser = pre.loc[pre["ever_treated"] == 1, col]
            cser = pre.loc[pre["ever_treated"] == 0, col]
            rows.append(
                {
                    "variable": col,
                    "label": col.replace("_", " ").title(),
                    "smd_pooled": _pooled_smd(tser, cser),
                    "mean_treated": float(tser.mean(skipna=True)),
                    "mean_control": float(cser.mean(skipna=True)),
                    "n_treated_tract_months": int(tser.notna().sum()),
                    "n_control_tract_months": int(cser.notna().sum()),
                },
            )
        return pd.DataFrame(rows) if rows else None

    @staticmethod
    def _treatment_tract_profile(did_panel: pd.DataFrame) -> pd.DataFrame:
        """One row per tract: treatment role + span (matched_* if present)."""
        d = did_panel.sort_values(["tract_geoid", "month"])
        specs: dict[str, Any] = {
            "ever_treated": ("ever_treated", "max"),
            "n_months": ("month", "nunique"),
            "n_rent_obs": ("rental_price", lambda s: int(s.notna().sum())),
            "first_month": ("month", "min"),
            "last_month": ("month", "max"),
        }
        if "matched_treated" in d.columns:
            specs["matched_treated"] = ("matched_treated", "max")
        if "matched_control" in d.columns:
            specs["matched_control"] = ("matched_control", "max")
        tract = d.groupby("tract_geoid", as_index=False).agg(**specs)
        tract["role"] = tract["ever_treated"].map(
            {0: "never_treated", 1: "ever_treated"},
        )
        if "matched_treated" in tract.columns:
            tract.loc[tract["matched_treated"] == 1, "role"] = "matched_treated"
        if "matched_control" in tract.columns:
            tract.loc[tract["matched_control"] == 1, "role"] = "matched_control"
        return tract
