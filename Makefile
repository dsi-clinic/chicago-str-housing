
# Default target
.DEFAULT_GOAL := help

# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
project_name := "2025-autumn-city-of-chicago-housing"
project_dir := "$(current_abs_path)"

# environment variables (optional - .env may not exist)
-include .env

# Build Docker image 
# Optional data directory mount (if DATA_DIR is set)
mount_data := $(if $(DATA_DIR),-v $(DATA_DIR):/project/data,)

.PHONY: help build-only devcontainer run-interactive clean test run-generic-pipeline run-eda-pipeline run-clustering-pipeline run-clustering-analysis    

help: ## Show the help message
	@echo "Available commands:"
	@echo ""
	@echo "  help                   Show this help message"
	@echo "  build-only             Build Docker image only"
	@echo "  devcontainer           Build and prepare devcontainer for VS Code/Cursor"
	@echo "  run-interactive        Run interactive bash session in container"
	@echo "  clean                  Clean up Docker images and containers"
	@echo "  test                   Run all tests with pytest"
	@echo "  run-generic-pipeline     Run the generic pipeline demo"
	@echo "  run-eda-pipeline         Run the housing EDA pipeline"
	@echo "  run-clustering-pipeline  Prepare data for clustering"
	@echo "  run-clustering-analysis  Run clustering data exploration"
	@echo ""
	@echo "Optional environment variables (.env file):"
	@echo "  DATA_DIR - Custom data directory path (defaults to ./data)"
	@echo ""

build-only: ## Build Docker image only
	docker compose build

devcontainer: ## Build and prepare devcontainer (run this before opening in VS Code/Cursor)
	docker compose build
	@echo "Dev container ready! Open this folder in VS Code/Cursor and select 'Reopen in Container'"

run-interactive: build-only ## Run interactive bash session in container
	docker compose run -it --rm --service-ports $(mount_data) $(project_name) /bin/bash

clean: ## Clean up Docker images and containers
	docker compose down --rmi all --volumes --remove-orphans
	docker image prune -f

test: build-only ## Run all tests with pytest
	docker compose run --rm $(mount_data) $(project_name) uv run python -m pytest -v

run-generic-pipeline: build-only ## Run the generic pipeline demo
	docker compose run --rm $(mount_data) $(project_name) uv run python src/pipeline/scripts/pipeline_usage.py

run-eda-pipeline: build-only ## Run the housing EDA pipeline
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/housing_eda_pipeline.py

run-clustering-pipeline: build-only ## Prepare data for clustering
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/clustering_pipeline.py

run-clustering-analysis: build-only ## Run clustering data exploration
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/clustering_analysis.py
