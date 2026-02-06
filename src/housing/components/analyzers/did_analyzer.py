"""Difference-in-Differences TWFE model analyzer.

This module estimates a two–way fixed effects (TWFE) DiD model on the
`did_panel` data and returns key results for easy downstream use.
"""

import logging
from typing import Any

import pandas as pd
from linearmodels.panel import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDAnalyzer(Analyzer):
    """Estimate a TWFE DiD model on the prepared did_panel."""

    def __init__(self) -> None:
        super().__init__(
            "did_twfe_analyzer",
            "Estimate a two-way fixed effects DiD model on the did_panel",
        )
        # This component expects did_panel in the context
        self.required_data = ["did_panel"]
        self.output_data = ["did_twfe_results"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the TWFE DiD model and return key statistics."""
        did_panel = context["did_panel"].copy()

        # Set multi-index: (entity, time)
        panel = did_panel.set_index(["tract_geoid", "month"])

        # Ensure proper types
        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)

        logger.info(
            "Fitting TWFE DiD model with PanelOLS: "
            "rental_price ~ 1 + treated + entity and time fixed effects"
        )

        # Two–way fixed effects DiD using PanelOLS:
        # Build the model directly instead of using from_formula so we can
        # pass fixed effects via keyword arguments (compatible with our version).
        y = panel["rental_price"]
        x = panel[["treated"]]

        model = PanelOLS(y, x, entity_effects=True, time_effects=True)

        # Cluster-robust SEs at the entity (tract) level
        results = model.fit(cov_type="clustered", cluster_entity=True)

        # Extract key statistics for the treatment effect
        coef = float(results.params["treated"])
        std_err = float(results.std_errors["treated"])
        p_value = float(results.pvalues["treated"])
        ci_low, ci_high = results.conf_int().loc["treated"]
        ci_low = float(ci_low)
        ci_high = float(ci_high)

        # Log concise summary of findings
        logger.info("DiD TWFE results for treated indicator:")
        logger.info("  Coefficient: %.4f", coef)
        logger.info("  Std. Error: %.4f", std_err)
        logger.info("  p-value: %.4g", p_value)
        logger.info("  95%% CI: [%.4f, %.4f]", ci_low, ci_high)

        # Also log the standard regression summary at debug level
        logger.debug("\n%s", results.summary)

        extracted_stats = {
            "coef": coef,
            "std_err": std_err,
            "p_value": p_value,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "n_obs": int(results.nobs),
        }

        return {
            "did_twfe_results": {
                "results": results,
                "stats": extracted_stats,
            }
        }

