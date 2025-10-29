import logging
from typing import Any

from housing.components.constants import (
    CORRELATION_MODERATE_THRESHOLD,
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_WEAK_THRESHOLD,
)
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

class AffordableDevelopmentOutlierAnalyzer(Analyzer):
    def __init__(self, density_columns: list, output_dir: str | None = None) -> None:
        """Initialize the outlier analyzer."""
        super().__init__(
            "affordable_development_outlier_analysis",
            """Identify the tracts with extreme unit density and development density values 
            
            and pull points for research
            """,
        )

        self.output_dir = output_dir or "/project/output"
        self.density_columns = density_columns

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform outlier identification for analysis"""

        tract_data = context["affordable_developments_tract_data"]
        point_data = context["affordable_developments_data"]
        text_to_write = ""

        for col in self.density_columns:
            text_to_write += f"COLUMN NAME: {col}\n"
            upper_bound = tract_data[col].quantile(0.99)
            tracts = tract_data.loc[tract_data[col] > upper_bound]["tract_geoid"].tolist()
            text_to_write += f"{len(tracts)} Outliers\n\n"
            for tract in tracts:
                text_to_write += f"\n\tTRACT GEOID: {tract}\n"
                target_tract = tract_data.loc[tract_data["tract_geoid"] == tract]
                idx = point_data.sindex.query(target_tract.geometry, predicate="intersects")[1].tolist()
                cand = point_data.iloc[idx]
                points_in_tract = cand[cand.within(target_tract.iloc[0].geometry)]
                for _, point in points_in_tract.iterrows():
                    text_to_write += f"\t\tProperty: {point["property_name"]}, Address: {point["address"]},"
                    text_to_write += f" Mgmt: {point["management_company"]}, Units: {point["units"]}\n"
            text_to_write += "\n\n"

        with open(f"{self.output_dir}/affordable_development_outliers.txt", "w") as f:
            f.write(text_to_write)

        return {"affordable_outliers_output": f"{self.output_dir}/affordable_development_outliers.txt"}


