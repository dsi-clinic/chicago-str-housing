"""Configuration management for the Chicago Housing Analysis Pipeline.

This module provides configuration management capabilities including:
- YAML/JSON configuration loading
- Environment variable support
- Configuration validation
- Default configurations
"""

import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class DataConfig(BaseModel):
    """Configuration for data sources."""

    rental_data_path: Path = Field(
        default=Path("/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv"),
        description="Path to rental price data file",
    )
    zip_boundaries_path: Path = Field(
        default=Path("/project/data/Boundaries_ZIP_Codes.csv"),
        description="Path to ZIP code boundaries file",
    )
    community_boundaries_path: Path = Field(
        default=Path("/project/data/Boundaries_Community_Areas.csv"),
        description="Path to community area boundaries file",
    )

    @validator("*", pre=True)
    def validate_paths(cls: type["DataConfig"], v: str | Path) -> Path:  # noqa: N805
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v


class OutputConfig(BaseModel):
    """Configuration for output settings."""

    output_dir: Path = Field(
        default=Path("/project/output"), description="Directory for output files"
    )
    save_intermediate_results: bool = Field(
        default=True, description="Whether to save intermediate processing results"
    )
    save_plots: bool = Field(
        default=True, description="Whether to save generated plots"
    )
    plot_format: Literal["png", "pdf", "svg", "jpg"] = Field(
        default="png", description="Format for saved plots"
    )
    plot_dpi: int = Field(
        default=300, ge=72, le=600, description="DPI for saved plots (72-600)"
    )
    results_format: Literal["json", "yaml", "csv"] = Field(
        default="json", description="Format for results output"
    )

    @validator("output_dir", pre=True)
    def validate_output_dir(cls: type["OutputConfig"], v: str | Path) -> Path:  # noqa: N805
        """Convert string to Path and create directory if needed."""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v


class AnalysisConfig(BaseModel):
    """Configuration for analysis parameters."""

    correlation_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum correlation threshold for significance",
    )
    min_zip_codes_per_community: int = Field(
        default=1, ge=1, description="Minimum ZIP codes required per community area"
    )
    recent_months: int = Field(
        default=12,
        ge=1,
        le=60,
        description="Number of recent months to include in analysis",
    )
    spatial_join_predicate: Literal["intersects", "within", "contains", "overlaps"] = (
        Field(
            default="intersects",
            description="Spatial join predicate for ZIP-community mapping",
        )
    )


class PipelineConfig(BaseModel):
    """Main pipeline configuration."""

    name: str = Field(
        default="Chicago Housing Analysis", description="Name of the pipeline"
    )
    description: str = Field(
        default="Analyze rental prices and house share prohibitions in Chicago",
        description="Description of the pipeline",
    )
    data: DataConfig = Field(
        default_factory=DataConfig, description="Data source configuration"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig, description="Output configuration"
    )
    analysis: AnalysisConfig = Field(
        default_factory=AnalysisConfig, description="Analysis parameters"
    )
    components: list[str] = Field(
        default_factory=list, description="List of components to include (empty = all)"
    )
    execution_order: list[str] = Field(
        default_factory=list,
        description="Custom execution order (empty = auto-determine)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "PIPELINE_"
        case_sensitive = False
        validate_assignment = True
        use_enum_values = True


class ConfigManager:
    """Manages pipeline configuration loading and validation."""

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path
        self.config: PipelineConfig | None = None

    def load_config(self, config_path: str | None = None) -> PipelineConfig | None:
        """Load configuration from file or use defaults."""
        if config_path:
            self.config_path = config_path

        try:
            if self.config_path and Path(self.config_path).exists():
                # Pydantic handles file loading automatically!
                self.config = PipelineConfig.parse_file(self.config_path)
                logger.info(f"Loaded configuration from: {self.config_path}")
            else:
                # Use defaults with environment variable support
                self.config = PipelineConfig()
                logger.info("Using default configuration with environment variables")

            # Validate data files exist
            self._validate_data_files()

            return self.config

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Falling back to default configuration")
            self.config = PipelineConfig()
            return self.config

    def _validate_data_files(self) -> None:
        """Validate that data files exist."""
        if not self.config:
            return

        data_paths = [
            ("rental_data", self.config.data.rental_data_path),
            ("zip_boundaries", self.config.data.zip_boundaries_path),
            ("community_boundaries", self.config.data.community_boundaries_path),
        ]

        for name, path in data_paths:
            if not path.exists():
                logger.warning(f"Data file not found: {name} at {path}")

    def save_config(self, output_path: str) -> None:
        """Save current configuration to file."""
        if not self.config:
            logger.error("No configuration to save")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic handles serialization automatically!
        if output_path.suffix.lower() in [".yaml", ".yml"]:
            with Path(output_path).open("w") as f:
                f.write(self.config.yaml(indent=2))
        elif output_path.suffix.lower() == ".json":
            with Path(output_path).open("w") as f:
                f.write(self.config.json(indent=2))
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")

        logger.info(f"Configuration saved to: {output_path}")

    def get_config_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary."""
        if not self.config:
            return {}
        # Pydantic handles this automatically!
        return self.config.dict()


def create_default_config(output_path: str) -> None:
    """Create a default configuration file."""
    config_manager = ConfigManager()
    # config = config_manager.load_config()  # This will use defaults
    config_manager.save_config(output_path)
    logger.info(f"Default configuration created at: {output_path}")


def load_pipeline_config(config_path: str | None = None) -> PipelineConfig:
    """Convenience function to load pipeline configuration."""
    config_manager = ConfigManager(config_path)
    return config_manager.load_config()
