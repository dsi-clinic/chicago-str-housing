"""Difference-in-Differences analyzer."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from linearmodels import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDAnalyzer(Analyzer):
    """Difference-in-Differences analyzer."""

    def __init__(self) -> None:
        """Initialize the Difference-in-Differences analyzer."""
        super().__init__("did_analyzer", "Difference-in-Differences analyzer")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the Difference-in-Differences analyzer."""
        did_panel = context["did_panel"]
        panel = did_panel.set_index(["tract_geoid", "month"])
        logger.info("Panel shape: %s", panel.shape)

        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)

        model = PanelOLS.from_formula(
            "rental_price ~ 1 + treated + EntityEffects + TimeEffects",
            data=panel,
        )
        logger.info("Model: %s", model)

        results = model.fit(cov_type="clustered", cluster_entity=True)
        logger.info("Summary of results: %s", results.summary)

        # Optionally save key DiD estimation results to CSV
        output_dir = Path(context.get("output_dir", "/project/output"))
        output_suffix = context.get("output_suffix", "")
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_df = pd.DataFrame(
            {
                "parameter": results.params.index,
                "estimate": results.params.values,
                "std_error": results.std_errors.values,
                "p_value": results.pvalues.values,
            }
        )

        output_path = output_dir / f"did_estimation_results{output_suffix}.csv"
        summary_df.to_csv(output_path, index=False)
        logger.info("DiD estimation results saved to: %s", output_path)

        return {"did_results": results, "did_model": model}
