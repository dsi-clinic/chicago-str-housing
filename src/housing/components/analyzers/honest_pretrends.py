"""Lightweight TWFE pretrend heuristic inspired by sensitivity-to-violations frameworks.

This is **not** a full Rambachan & Roth (2023) implementation; it summarizes how large
purely pre-period TWFE event coefficients need to move to overturn conclusions.
Uses ``event_study_coefficients.csv`` / context ``event_study_coefficients``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class HonestPretrendsAnalyzer(Analyzer):
    """Summarize TWFE pretrend magnitudes from the housing event study table."""

    def __init__(self, output_dir: str | Path) -> None:
        super().__init__(
            "honest_pretrends_analysis",
            "TWFE pretrend heuristic summary for whitepaper narration",
        )
        self.output_dir = Path(output_dir)

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        coef_df = context.get("event_study_coefficients")
        if coef_df is None or (isinstance(coef_df, pd.DataFrame) and coef_df.empty):
            logger.warning("honest_pretrends: missing event_study_coefficients")
            return {}

        df = coef_df.copy()
        if "relative_time" in df.columns and "rel_time" not in df.columns:
            df = df.rename(columns={"relative_time": "rel_time"})
        if "coefficient" in df.columns and "coef" not in df.columns:
            df = df.rename(columns={"coefficient": "coef"})
        if "rel_time" not in df.columns or "coef" not in df.columns:
            logger.warning("honest_pretrends: expected rel_time and coef columns")
            return {}

        pre = df[df["rel_time"] < -1].sort_values("rel_time")
        if pre.empty:
            row = {"error": "No pre-period coefficients"}
        else:
            coefs = pre["coef"].astype(float).to_numpy()
            rel_times = pre["rel_time"].astype(float).to_numpy()
            abs_max_pre = float(max(abs(coefs)))
            deltas = coefs[1:] - coefs[:-1]
            second_diff = deltas[1:] - deltas[:-1] if len(deltas) > 1 else []
            smoothness_bound = float(max(abs(second_diff))) if len(second_diff) else 0.0

            violates_sign_restriction_negative = bool((coefs > 0).any())
            last_pre_rel_time = float(rel_times[-1])
            last_pre_coef = float(coefs[-1])

            row = {
                "max_abs_twfe_coef_pre": abs_max_pre,
                "smoothness_second_diff_abs_max": smoothness_bound,
                "violates_sign_restriction_all_nonpositive_pre": violates_sign_restriction_negative,
                "last_pre_rel_time": last_pre_rel_time,
                "last_pre_coef": last_pre_coef,
                "n_pre_periods": int(len(coefs)),
            }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_csv = self.output_dir / "honest_pretrends_summary.csv"
        pd.DataFrame([row]).to_csv(out_csv, index=False)
        logger.info("Wrote %s", out_csv)

        return {"honest_pretrends_summary": row, "honest_pretrends_csv": str(out_csv)}
