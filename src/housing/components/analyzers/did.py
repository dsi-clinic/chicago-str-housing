"""Docstring"""

import logging
from pathlib import Path
from typing import Any

from linearmodels.panel import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDAnalyzer(Analyzer):
    """Analyze DiD data prior to conducting experiment and check for the parallel trends assumption."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DiD descriptive analyzer."""
        super().__init__(
            "did_analyzer",
            "Analyze DiD dataset before experiment",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze DiD Descriptive Trends Before Conducting Experiment."""
        did_panel = context["did_panel"]

        # Set multi-index: (entity, time)
        panel = did_panel.set_index(["tract_geoid", "month"])

        # Ensure proper types
        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)

        # Run PanelOLS for DiD Results
        formula = "rental_price ~ 1 + treated + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=panel)
        results = model.fit(cov_type="clustered", cluster_entity=True)

        # Write summary to txt file in output folder
        summary_path = Path(self.output_dir) / "did_ols_summary.txt"

        with summary_path.open("w") as f:
            f.write(str(results.summary))

        logger.info("Wrote PanelOLS summary to %s", str(summary_path))

        return {"did_results_summary": str(summary_path)}
