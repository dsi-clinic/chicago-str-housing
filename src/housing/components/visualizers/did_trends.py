
import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from housing.components.utils import setup_figure_and_save, add_statistical_summary_to_plot
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Visualize DiD trends and checks."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DiD trends visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "did_trends_visualizer",
            "Visualize DiD trends and checks",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create DiD visualizations."""
        logger.info("Creating DiD visualizations...")

        # Get data from context (populated by DIDDescriptiveAnalyzer)
        treated_by_month = context.get("did_adoption_curve")
        avg_by_group = context.get("did_avg_by_group")
        first_treatment = context.get("did_first_treatment_date")
        pre_balance = context.get("did_pre_balance")
        summary_table = context.get("did_summary_table")
        t_test = context.get("did_balance_t_test")

        if treated_by_month is None or avg_by_group is None:
            logger.warning(
                "Missing DiD analysis results in context. Skipping visualization."
            )
            return {}

        # Create one large figure with subplots
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. Adoption Curve
        ax1 = fig.add_subplot(gs[0, 0])
        treated_by_month.plot(ax=ax1)
        ax1.set_ylabel("Number of Treated Tracts")
        ax1.set_xlabel("Month")
        ax1.set_title("STR Prohibition Adoption Over Time")
        ax1.grid(True, alpha=0.3)

        # 2. Parallel Trends Check
        ax2 = fig.add_subplot(gs[0, 1])
        avg_by_group.plot(ax=ax2, alpha=0.7)
        if first_treatment:
            ax2.axvline(
                first_treatment, color="red", linestyle="--", label="First Treatment"
            )

        ax2.set_ylabel("Average Rental Price ($)")
        ax2.set_xlabel("Month")
        ax2.set_title("Parallel Trends Check: Treated vs. Control Tracts")
        ax2.legend(title="Group")
        ax2.grid(True, alpha=0.3)
        
        # 3. Pre-Treatment Balance Table (Visual)
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.axis('tight')
        ax3.axis('off')
        ax3.set_title("Pre-Treatment Balance Stats", y=1.0)
        
        if pre_balance is not None:
             # Formatting for the table
            table_data = pre_balance.round(2)
            table = ax3.table(
                cellText=table_data.values,
                rowLabels=table_data.index,
                colLabels=table_data.columns,
                cellLoc='center',
                loc='center',
                bbox=[0.1, 0.4, 0.8, 0.4] # centering
            )
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.2)
            
            # Add T-Test Results below
            if t_test:
                t_stat = t_test.get('t_stat')
                p_val = t_test.get('p_value')
                if t_stat is not None and p_val is not None:
                    ax3.text(0.5, 0.2, 
                             f"Pre-treatment Difference Test:\nt-stat: {t_stat:.2f}, p-value: {p_val:.4f}",
                             ha='center', va='center', transform=ax3.transAxes, fontsize=11)

        # 4. Summary Stats Overview
        ax4 = fig.add_subplot(gs[1, 1])
        if summary_table is not None:
             data_sections = [
                {
                    "section_title": "SUMMARY STATISTICS",
                    "stats": []
                }
            ]
             
             # Extract some key stats for the summary box
             # summary_table index is ["Never Treated", "Eventually Treated"]
             # Columns: ["N Tracts", "Mean Rent", "Std Dev", "Min Rent", "Max Rent", "Treated Obs"]
             
             for idx in summary_table.index:
                 row = summary_table.loc[idx]
                 n_tracts = row["N Tracts"]
                 mean_rent = row["Mean Rent"]
                 data_sections[0]["stats"].append((f"{idx} (N={int(n_tracts)})", f"${mean_rent:,.0f}"))
            
             add_statistical_summary_to_plot(
                ax4,
                "Group Comparison Summary",
                data_sections,
                bgcolor="lightgray",
            )
        else:
            ax4.text(0.5, 0.5, "No Summary Data", ha='center')
            ax4.axis('off')

        # Save the plot
        output_path = Path(self.output_dir) / "did_descriptive_analysis.png"
        setup_figure_and_save(
            fig,
            output_path,
            "DiD Descriptive Analysis",
            logger=logger,
        )

        return {"did_visualization_path": str(output_path)}
