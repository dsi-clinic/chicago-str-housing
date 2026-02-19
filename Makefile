
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

.PHONY: help build-only devcontainer run-interactive clean test run-generic-pipeline run-eda-pipeline run-clustering-pipeline run-clustering-analysis run-did-pipeline run-did-pipeline-covariates run-did-pipeline-cs run-did-pipeline-local run-did-pipeline-covariates-local run-did-pipeline-cs-local run-did-diagnostic run-did-deep-diagnostic

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
	@echo "  run-clustering-analysis  Run clustering data exploration (ARGS=\"--scatter-matrix\" to include scatter matrix)"
	@echo "  run-did-pipeline         Run DiD analysis (descriptive + event study)"
	@echo "  run-did-pipeline-covariates  Run enhanced DiD with covariate controls + diagnostics"
	@echo "  run-did-pipeline-cs      Run DiD with Callaway-Sant'Anna (2020) robust estimator"
	@echo "  run-did-diagnostic       Run DiD data diagnostic (panel, treatment, rental prices)"
	@echo "  run-did-deep-diagnostic  Run deep diagnostic (cohorts, trends, STR dates, CS feasibility)"
	@echo "  run-did-pipeline-local   Copy data to /tmp and run DiD (use if Errno 35 on Box/synced drive)"
	@echo "  run-did-pipeline-covariates-local  Same for DiD with covariates"
	@echo "  run-did-pipeline-cs-local  Same for Callaway-Sant'Anna pipeline"
	@echo ""
	@echo "Optional environment variables (.env file):"
	@echo "  DATA_DIR - Custom data directory path (defaults to ./data when not set)"
	@echo "  If you see 'Resource deadlock avoided' (Errno 35) or GDAL errors with Docker,"
	@echo "  run: DATA_DIR=/tmp/chicago_data make run-did-pipeline (after copying data to /tmp/chicago_data)"
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
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/clustering_analysis.py $(ARGS)

run-did-pipeline: build-only ## Run DiD analysis (descriptive + event study)
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline.py

run-did-pipeline-covariates: build-only ## Run enhanced DiD with covariate controls + diagnostics
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_with_covariates.py

run-did-pipeline-local: build-only ## Copy data to /tmp and run DiD (avoids Errno 35 on Box/synced drives)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	@echo "Running DiD pipeline with DATA_DIR=/tmp/chicago_did_data (avoids sync drive I/O issues)..."
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_pipeline.py

run-did-pipeline-covariates-local: build-only ## Copy data to /tmp and run DiD with covariates (avoids Errno 35 on Box/synced drives)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	@echo "Running DiD covariates pipeline with /tmp/chicago_did_data (avoids sync drive I/O issues)..."
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_pipeline_with_covariates.py

run-did-pipeline-cs: build-only ## Run DiD analysis with Callaway-Sant'Anna (2020) robust estimator
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py

run-did-pipeline-cs-local: build-only ## Copy data to /tmp and run Callaway-Sant'Anna pipeline (avoids Errno 35 on Box/synced drives)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	@echo "Running Callaway-Sant'Anna pipeline with /tmp/chicago_did_data (avoids sync drive I/O issues)..."
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py

run-did-diagnostic: build-only ## Run DiD data diagnostic (checks panel, treatment, rental prices)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_data_diagnostic.py

run-did-deep-diagnostic: build-only ## Run deep diagnostic (cohorts, trends, STR dates, CS feasibility)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	@echo "Running deep diagnostic with /tmp/chicago_did_data (avoids sync drive I/O issues)..."
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_deep_diagnostic.py
