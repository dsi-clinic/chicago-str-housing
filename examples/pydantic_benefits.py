"""Demonstration of Pydantic benefits over dataclasses for pipeline configuration.

This example shows why Pydantic is superior for configuration management
in data pipelines.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

# ============================================================================
# PYDANTIC CONFIGURATION
# ============================================================================


class PydanticDataConfig(BaseModel):
    """Pydantic-based configuration with automatic validation."""

    rental_data_path: Path = Field(
        default=Path("/project/data/rental.csv"), description="Path to rental data file"
    )
    recent_months: int = Field(
        default=12,
        ge=1,  # Must be >= 1
        le=60,  # Must be <= 60
        description="Number of recent months to analyze",
    )
    correlation_threshold: float = Field(
        default=0.1,
        ge=0.0,  # Must be >= 0
        le=1.0,  # Must be <= 1
        description="Correlation threshold for significance",
    )
    plot_format: Literal["png", "pdf", "svg"] = Field(
        default="png", description="Output format for plots"
    )
    output_dir: Path = Field(
        default=Path("/project/output"), description="Output directory"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "PIPELINE_"  # Automatically reads PIPELINE_* env vars
        case_sensitive = False
        validate_assignment = True  # Validate on assignment

    @Field.validator("output_dir", pre=True)
    def create_output_dir(cls: type["PydanticDataConfig"], v: str | Path) -> Path:
        """Automatically create output directory if it doesn't exist."""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v


def demonstrate_pydantic_benefits() -> None:
    """Demonstrate the benefits of Pydantic over dataclasses."""
    print("=" * 60)
    print("PYDANTIC vs DATACLASSES COMPARISON")
    print("=" * 60)

    # ========================================================================
    # 1. AUTOMATIC VALIDATION
    # ========================================================================
    print("\n1. AUTOMATIC VALIDATION")
    print("-" * 30)

    try:
        # This will fail validation
        config = PydanticDataConfig(
            recent_months=-5,  # Invalid: must be >= 1
            correlation_threshold=1.5,  # Invalid: must be <= 1
            plot_format="invalid_format",  # Invalid: must be png/pdf/svg
        )
    except ValidationError as e:
        print("✓ Pydantic caught validation errors:")
        for error in e.errors():
            field = error["loc"][0]
            message = error["msg"]
            print(f"  - {field}: {message}")

    # Valid configuration
    config = PydanticDataConfig(
        recent_months=6, correlation_threshold=0.3, plot_format="pdf"
    )
    print(
        f"✓ Valid configuration created: {config.recent_months} months, {config.correlation_threshold} threshold"
    )

    # ========================================================================
    # 2. ENVIRONMENT VARIABLE SUPPORT
    # ========================================================================
    print("\n2. ENVIRONMENT VARIABLE SUPPORT")
    print("-" * 30)

    # Set environment variables
    os.environ["PIPELINE_RECENT_MONTHS"] = "18"
    os.environ["PIPELINE_CORRELATION_THRESHOLD"] = "0.25"
    os.environ["PIPELINE_PLOT_FORMAT"] = "svg"

    # Pydantic automatically reads these!
    config_with_env = PydanticDataConfig()
    print("✓ Environment variables automatically loaded:")
    print(
        f"  - recent_months: {config_with_env.recent_months} (from PIPELINE_RECENT_MONTHS)"
    )
    print(
        f"  - correlation_threshold: {config_with_env.correlation_threshold} (from PIPELINE_CORRELATION_THRESHOLD)"
    )
    print(f"  - plot_format: {config_with_env.plot_format} (from PIPELINE_PLOT_FORMAT)")

    # ========================================================================
    # 3. AUTOMATIC FILE LOADING
    # ========================================================================
    print("\n3. AUTOMATIC FILE LOADING")
    print("-" * 30)

    # Create a sample config file
    import tempfile

    config_file = Path(tempfile.mkdtemp()) / "sample_config.json"
    config_file.write_text("""
    {
        "recent_months": 24,
        "correlation_threshold": 0.15,
        "plot_format": "pdf",
        "output_dir": "/tmp/pipeline_output"
    }
    """)

    # Pydantic loads it automatically!
    config_from_file = PydanticDataConfig.parse_file(config_file)
    print("✓ Configuration loaded from file:")
    print(f"  - recent_months: {config_from_file.recent_months}")
    print(f"  - correlation_threshold: {config_from_file.correlation_threshold}")
    print(f"  - plot_format: {config_from_file.plot_format}")
    print(f"  - output_dir: {config_from_file.output_dir}")

    # ========================================================================
    # 4. AUTOMATIC SERIALIZATION
    # ========================================================================
    print("\n4. AUTOMATIC SERIALIZATION")
    print("-" * 30)

    # JSON serialization
    json_output = config.json(indent=2)
    print("✓ JSON serialization:")
    print(json_output[:200] + "...")

    # YAML serialization (if pyyaml is installed)
    try:
        yaml_output = config.yaml(indent=2)
        print("✓ YAML serialization:")
        print(yaml_output[:200] + "...")
    except ImportError:
        print("⚠ YAML serialization requires pyyaml package")

    # Dictionary conversion
    config_dict = config.dict()
    print(f"✓ Dictionary conversion: {list(config_dict.keys())}")

    # ========================================================================
    # 5. TYPE SAFETY AND IDE SUPPORT
    # ========================================================================
    print("\n5. TYPE SAFETY AND IDE SUPPORT")
    print("-" * 30)

    # IDE will provide autocomplete and type checking
    print("✓ Type-safe access:")
    print(f"  - config.recent_months: {config.recent_months} (int)")
    print(f"  - config.rental_data_path: {config.rental_data_path} (Path)")
    print(f"  - config.plot_format: {config.plot_format} (Literal)")

    # Assignment validation
    try:
        config.recent_months = -1  # This will fail!
    except ValidationError as e:
        print(f"✓ Assignment validation caught: {e}")

    # ========================================================================
    # 6. COMPLEX VALIDATION
    # ========================================================================
    print("\n6. COMPLEX VALIDATION")
    print("-" * 30)

    class AdvancedConfig(BaseModel):
        """Advanced configuration with complex validation."""

        data_paths: list[Path] = Field(
            default_factory=list, description="List of data file paths"
        )
        processing_cores: int = Field(
            default=1,
            ge=1,
            le=os.cpu_count() or 1,
            description="Number of processing cores to use",
        )

        @Field.validator("data_paths")
        def validate_data_paths(
            cls: type["AdvancedConfig"], v: list[Path]
        ) -> list[Path]:
            """Validate that all data paths exist."""
            for path in v:
                if not path.exists():
                    raise ValueError(f"Data file not found: {path}")
            return v

    # This will work
    advanced_config = AdvancedConfig(
        data_paths=[Path("/project/data/rental.csv")],  # Assuming this exists
        processing_cores=4,
    )
    print(f"✓ Advanced validation passed: {len(advanced_config.data_paths)} data paths")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY: WHY PYDANTIC IS BETTER FOR PIPELINES")
    print("=" * 60)

    benefits = [
        "✓ Automatic validation with detailed error messages",
        "✓ Built-in environment variable support",
        "✓ Automatic file loading (JSON/YAML)",
        "✓ Automatic serialization (JSON/YAML)",
        "✓ Type safety and IDE support",
        "✓ Complex validation with custom validators",
        "✓ Better error messages and debugging",
        "✓ Less boilerplate code",
        "✓ Built-in documentation generation",
        "✓ Integration with FastAPI, SQLModel, etc.",
    ]

    for benefit in benefits:
        print(benefit)

    print("\nWith dataclasses, you'd need to implement all of this manually!")
    print(
        "Pydantic gives you enterprise-grade configuration management out of the box."
    )


if __name__ == "__main__":
    demonstrate_pydantic_benefits()
