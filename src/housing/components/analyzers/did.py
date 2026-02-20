"""Difference-in-Differences analyzer using PanelOLS."""

import logging
from pathlib import Path
from typing import Any

from linearmodels.panel import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDAnalyzer(Analyzer):
    """Estimate a two-way fixed effects DiD model and save results."""

    def __init__(
        self,
        output_dir: str | None = None,
        panel: str | None = None,
        output_suffix: str | None = None,
    ) -> None:
        """Initialize analyzer with optional output directory.

        Args:
        output_dir: directory to store outputs
        panel: DiD panel dataset to fetch from context
        output_suffix: string to add to end of output file name
        """
        super().__init__(
            "did_analyzer",
            "Estimate a two-way fixed effects DiD model.",
        )
        self.output_dir = output_dir or "/project/output"
        self.panel = panel or "did_panel"
        self.output_name = "did_ols_summary" + (output_suffix or "") + ".txt"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run DiD regression and write summary report to output folder."""
        did_panel = context[self.panel]

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
        summary_path = Path(self.output_dir) / self.output_name

        with summary_path.open("w") as f:
            f.write(str(results.summary))

        logger.info("Wrote PanelOLS summary to %s", str(summary_path))

        return {"did_results_summary": str(summary_path)}
