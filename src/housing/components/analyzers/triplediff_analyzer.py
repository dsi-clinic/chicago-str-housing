"""Triple-difference (DDD) analyzer.

Estimates the differential effect of treatment across a census-defined group
(e.g. high vs low income) using panel regression with entity and time fixed effects.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from linearmodels import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class TripleDiffAnalyzer(Analyzer):
    """Run triple-difference regression: outcome ~ treated * group + FEs."""

    def __init__(self) -> None:
        """Initialize the triple-difference analyzer."""
        super().__init__(
            "triplediff_analyzer",
            "Triple-difference regression with census group",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run DDD regression and return results."""
        ddd_panel = context["ddd_panel"]
        group_name = context.get("ddd_group_name", "high_income")

        if group_name not in ddd_panel.columns:
            raise ValueError(
                f"Group column '{group_name}' not in ddd_panel. "
                "Run TripleDiffGroupProcessor first."
            )

        panel = ddd_panel.set_index(["tract_geoid", "month"]).copy()
        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)
        panel[group_name] = panel[group_name].astype(float)

        # DDD: interaction of treated and group (third difference)
        formula = (
            f"rental_price ~ 1 + treated * {group_name} "
            "+ EntityEffects + TimeEffects"
        )
        logger.info("DDD formula: %s", formula)

        model = PanelOLS.from_formula(formula, data=panel)
        results = model.fit(cov_type="clustered", cluster_entity=True)
        logger.info("Triple-diff results: %s", results.summary)

        # Save coefficient table
        output_dir = Path(context.get("output_dir", "/project/output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_df = pd.DataFrame(
            {
                "parameter": results.params.index,
                "estimate": results.params.to_numpy(),
                "std_error": results.std_errors.to_numpy(),
                "p_value": results.pvalues.to_numpy(),
            }
        )
        out_path = output_dir / "triplediff_estimation_results.csv"
        summary_df.to_csv(out_path, index=False)
        logger.info("DDD results saved to: %s", out_path)

        return {
            "triplediff_results": results,
            "triplediff_model": model,
            "triplediff_group_name": group_name,
        }
