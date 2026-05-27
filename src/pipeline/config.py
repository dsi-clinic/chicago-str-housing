"""Configuration management for data analysis pipelines.

This module provides configuration management capabilities including:
- YAML/JSON configuration loading
- Environment variable support
- Configuration validation
- Default configurations
"""

import logging
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _default_data_dir() -> Path:
    """Root folder for local CSV / shapefiles (override with ``DATA_DIR``)."""
    return Path(os.environ.get("DATA_DIR", "/project/data"))


class DataConfig(BaseModel):
    """Configuration for data sources.

    Declares the paths exercised by tests and default pipeline tutorials. Additional
    keys may be supplied via YAML thanks to ``extra="allow"``.
    """

    # Allow additional fields from YAML config
    model_config = ConfigDict(extra="allow")

    rental_data_path: Path = Field(
        default_factory=lambda: _default_data_dir()
        / "Zip_zori_uc_sfrcondomfr_sm_month.csv",
        description="Path to rental price data file",
    )
    zip_boundaries_path: Path | str = Field(
        default="https://data.cityofchicago.org/resource/unjd-c2ca.json",
        description="Path to ZIP code boundaries file or URL",
    )
    community_boundaries_path: Path | str = Field(
        default="https://data.cityofchicago.org/resource/igwz-8jzy.json",
        description="Path to community area boundaries file or URL",
    )
    tract_boundaries_path: Path = Field(
        default_factory=lambda: _default_data_dir()
        / "tl_2023_17_tract"
        / "tl_2023_17_tract.shp",
        description="Path to census tract boundaries shapefile",
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_paths(cls: type["DataConfig"], v: str | Path) -> Path | str:
        """Convert string paths to Path objects, but keep URLs as strings."""
        if isinstance(v, str):
            # Keep URLs as strings, convert file paths to Path
            if v.startswith("http://") or v.startswith("https://"):
                return v
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

    @field_validator("output_dir", mode="before")
    @classmethod
    def validate_output_dir(cls: type["OutputConfig"], v: str | Path) -> Path:
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


class PipelineConfig(BaseModel):
    """Main pipeline configuration."""

    name: str = Field(
        default="Data Analysis Pipeline", description="Name of the pipeline"
    )
    description: str = Field(
        default="Generic data analysis pipeline",
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

    model_config = ConfigDict(
        env_prefix="PIPELINE_",
        case_sensitive=False,
        validate_assignment=True,
        use_enum_values=True,
    )


class ConfigManager:
    """Manages pipeline configuration loading and validation."""

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the config manager.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path
        self.config: PipelineConfig | None = None

    def load_config(self, config_path: str | None = None) -> PipelineConfig | None:
        """Load configuration from file or use defaults."""
        if config_path:
            self.config_path = config_path

        try:
            if self.config_path and Path(self.config_path).exists():
                # Handle different file formats
                config_path = Path(self.config_path)
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    with config_path.open("r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f)
                    self.config = PipelineConfig(**config_data)
                else:
                    # Default to JSON
                    self.config = PipelineConfig.parse_file(self.config_path)
                logger.info("Loaded configuration from: %s", self.config_path)
            else:
                # Use defaults with environment variable support
                self.config = PipelineConfig()
                logger.info("Using default configuration with environment variables")

            # Validate data files exist
            self._validate_data_files()

            return self.config

        except Exception as e:
            logger.error("Error loading configuration: %s", e)
            logger.info("Falling back to default configuration")
            self.config = PipelineConfig()
            return self.config

    def _validate_data_files(self) -> None:
        """Validate that data files exist (defined + extra fields)."""
        if not self.config:
            return

        # Collect all data paths (defined fields + extra fields from YAML)
        all_paths = {}

        # Get defined fields
        all_paths.update(self.config.data.model_dump())

        # Get extra fields (added dynamically from YAML)
        if (
            hasattr(self.config.data, "__pydantic_extra__")
            and self.config.data.__pydantic_extra__
        ):
            all_paths.update(self.config.data.__pydantic_extra__)

        # Validate all paths
        for field_name, path in all_paths.items():
            if not field_name.endswith("_path"):
                continue

            # Clean name for logging (remove '_path' suffix)
            clean_name = field_name.replace("_path", "")

            # Skip validation for URLs
            if isinstance(path, str) and (
                path.startswith("http://") or path.startswith("https://")
            ):
                continue
            # Check file existence for local paths
            if isinstance(path, Path) and not path.exists():
                logger.warning("Data file not found: %s at %s", clean_name, path)

    def save_config(self, output_path: str) -> None:
        """Save current configuration to file."""
        if not self.config:
            logger.error("No configuration to save")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic handles serialization automatically!
        if output_path.suffix.lower() in [".yaml", ".yml"]:
            # Convert Path objects to strings for YAML serialization
            config_dict = self.config.model_dump()

            def convert_paths(obj: Any) -> Any:  # noqa: ANN001, ANN401
                if isinstance(obj, dict):
                    return {k: convert_paths(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_paths(item) for item in obj]
                elif hasattr(obj, "__fspath__"):  # Path objects
                    return str(obj)
                return obj

            config_dict = convert_paths(config_dict)
            with Path(output_path).open("w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, indent=2, default_flow_style=False)
        elif output_path.suffix.lower() == ".json":
            with Path(output_path).open("w", encoding="utf-8") as f:
                f.write(self.config.json(indent=2))
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")

        logger.info("Configuration saved to: %s", output_path)

    def get_config_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary."""
        if not self.config:
            return {}
        # Pydantic handles this automatically!
        return self.config.model_dump()


def create_default_config(output_path: str) -> None:
    """Create a default configuration file."""
    config_manager = ConfigManager()
    config_manager.load_config()  # This will use defaults
    config_manager.save_config(output_path)
    logger.info("Default configuration created at: %s", output_path)


def load_pipeline_config(config_path: str | None = None) -> PipelineConfig:
    """Convenience function to load pipeline configuration."""
    config_manager = ConfigManager(config_path)
    return config_manager.load_config()
