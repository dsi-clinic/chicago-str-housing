"""Difference-in-Differences analyzer."""

import logging
from typing import Any

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

        return {"did_results": results, "did_model": model}
