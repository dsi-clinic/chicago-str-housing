
# Default target
.DEFAULT_GOAL := help

# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
project_name := "chicago-str-housing"
project_dir := "$(current_abs_path)"

# environment variables (optional - .env may not exist)
-include .env

# Build Docker image 
# Optional data directory mount (if DATA_DIR is set)
mount_data := $(if $(DATA_DIR),-v $(DATA_DIR):/project/data,)

# Tract-cluster bootstrap defaults (override: `make run-did-pipeline-cs-bootstrap CS_BOOTSTRAP_REPS=199`)
CS_BOOTSTRAP_REPS ?= 399
CS_BOOTSTRAP_SEED ?= 42

.PHONY: help build-only devcontainer run-interactive clean test run-generic-pipeline run-eda-pipeline run-clustering-pipeline run-clustering-analysis run-did-pipeline run-did-pipeline-covariates run-did-pipeline-cs run-did-pipeline-cs-local run-did-pipeline-cs-whitepaper run-did-pipeline-cs-bootstrap run-did-pipeline-cs-covariates run-did-pipeline-cs-covariates-bootstrap run-did-pipeline-cs-heterogeneity run-did-pipeline-cs-spillover run-did-pipeline-cs-trajectory run-did-matched-pipeline sync-str-paper-figures run-robustness-sweeps white-paper whitepaper-deck

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
	@echo "  run-did-pipeline         Build DiD panel dataset for causal analysis"
	@echo "  run-did-pipeline-covariates  Run DiD analysis with covariate controls (local data)"
	@echo "  run-did-pipeline-cs         Run DiD with Callaway-Sant'Anna (2021) robust estimator"
	@echo "  run-did-pipeline-cs-local   Same, with data copied to /tmp (avoids sync drive I/O)"
	@echo "  run-did-pipeline-cs-whitepaper  CS pipeline → output/did-cs-whitepaper + whitepaper diagnostics"
	@echo "  run-did-pipeline-cs-bootstrap  Same, plus tract-cluster bootstrap (default $(CS_BOOTSTRAP_REPS) reps)"
	@echo "  run-did-pipeline-cs-covariates  Baseline CS pipeline plus Callaway-Sant'Anna with covariate controls"
	@echo "  run-did-pipeline-cs-covariates-bootstrap  Covariates pipeline + baseline CS bootstrap"
	@echo "  run-did-pipeline-cs-heterogeneity  Baseline CS + subgroup heterogeneity"
	@echo "  run-did-pipeline-cs-spillover  Baseline CS + spatial spillover panel"
	@echo "  run-did-pipeline-cs-trajectory  Baseline CS + post-treatment trajectory analysis"
	@echo "  run-did-matched-pipeline  Run DiD analysis on trend-matched sample"
	@echo "  sync-str-paper-figures  Copy DiD PNGs + CSV tables to docs/str-paper/"
	@echo "  white-paper              Build policy brief PDF (latexmk; host TeX required)"
	@echo "  whitepaper-deck          Build Beamer deck (latexmk + output/did-cs-whitepaper assets)"
	@echo ""
	@echo "Optional environment variables (.env file):"
	@echo "  DATA_DIR - Custom data directory path (defaults to ./data)"
	@echo "  CENSUS_API_KEY - Census Bureau API key for ACS (see .env.example)"
	@echo "  DID_TREATMENT_MODE - CS pipeline: threshold (default), binary, or both"
	@echo "  CS_BOOTSTRAP_REPS / CS_BOOTSTRAP_SEED - Defaults for *-bootstrap targets"
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

run-did-pipeline: build-only ## Build DiD panel dataset for causal analysis
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline.py

run-did-pipeline-covariates: build-only ## Run DiD with covariate controls (local data)
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_with_covariates.py

run-did-pipeline-cs: build-only ## Run DiD analysis with Callaway-Sant'Anna (2021) robust estimator
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py

run-did-pipeline-cs-local: build-only ## Copy data to /tmp and run Callaway-Sant'Anna pipeline (avoids Errno 35 on Box/synced drives)
	@mkdir -p /tmp/chicago_did_data && cp -r "$(current_abs_path)data/"* /tmp/chicago_did_data/ 2>/dev/null || true
	@echo "Running Callaway-Sant'Anna pipeline with /tmp/chicago_did_data (avoids sync drive I/O issues)..."
	docker compose run --rm -v "/tmp/chicago_did_data:/project/data" $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py

run-did-pipeline-cs-whitepaper: ## Run CS pipeline → output/did-cs-whitepaper (host venv/DATA_DIR; no Docker unless you mirror this)
	mkdir -p "$(current_abs_path)output/did-cs-whitepaper"
	cd "$(current_abs_path)" && \
	  DID_CS_OUTPUT_DIR="$(current_abs_path)output/did-cs-whitepaper" \
	  DID_WHITEPAPER_MODE=1 \
	  DATA_DIR="$(or $(DATA_DIR),$(current_abs_path)data)" \
	  PYTHONPATH="$(current_abs_path)src" \
	  uv run python -m housing.scripts.did_pipeline_callaway_santanna

run-did-pipeline-cs-bootstrap: build-only ## DiD CS + tract-cluster bootstrap (default $(CS_BOOTSTRAP_REPS) reps)
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py --cs-bootstrap-reps $(CS_BOOTSTRAP_REPS) --cs-bootstrap-seed $(CS_BOOTSTRAP_SEED)

run-did-pipeline-cs-covariates: build-only ## Baseline CS pipeline plus Callaway-Sant'Anna with covariate controls
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna_with_controls.py

run-did-pipeline-cs-covariates-bootstrap: build-only ## Covariates pipeline + baseline CS tract-cluster bootstrap
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna_with_controls.py --cs-bootstrap-reps $(CS_BOOTSTRAP_REPS) --cs-bootstrap-seed $(CS_BOOTSTRAP_SEED)

run-did-pipeline-cs-heterogeneity: build-only ## Baseline CS + subgroup heterogeneity
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna_heterogeneity.py

run-did-pipeline-cs-spillover: build-only ## Baseline CS + Queen-contiguity spillover panel
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna_spillover.py

run-did-pipeline-cs-trajectory: build-only ## Baseline CS + post-treatment trajectory analysis
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna_trajectory.py

STR_PAPER_FIGURES := \
	did_callaway_santanna_event_study.png \
	did_callaway_santanna_event_study_with_controls.png \
	did_twfe_vs_cs_comparison.png \
	did_cs_twfe_difference.png \
	did_cohort_dynamics.png \
	did_cs_trajectory_fit.png \
	did_cs_trajectory_phases.png \
	did_cs_heterogeneity_income.png \
	did_cs_heterogeneity_renter_share.png \
	did_cs_heterogeneity_airbnb_density.png \
	did_cs_heterogeneity_dose.png \
	did_cs_cohort_early_vs_late.png \
	did_cs_spillover_event_study.png

STR_PAPER_CSVS := \
	did_twfe_cs_comparison_table.csv \
	cs_heterogeneity_summary.csv \
	cs_event_study_tract_bootstrap.csv \
	cs_tract_bootstrap_meta.csv \
	cs_spillover_summary.csv \
	cs_trajectory_summary.csv

sync-str-paper-figures: ## Copy DiD figures + CSV tables to docs/str-paper/ (for GitHub)
	@test -d output/did-cs || (echo "Missing output/did-cs — run DiD pipelines locally first (e.g. make run-did-pipeline-cs)." && exit 1)
	@mkdir -p docs/str-paper/figures docs/str-paper/csv
	@for f in $(STR_PAPER_FIGURES); do \
		test -f "output/did-cs/$$f" || (echo "Missing output/did-cs/$$f — run the pipelines that produce this figure." && exit 1); \
		cp "output/did-cs/$$f" "docs/str-paper/figures/$$f"; \
		echo "Copied figures/$$f"; \
	done
	@for f in $(STR_PAPER_CSVS); do \
		test -f "output/did-cs/$$f" || (echo "Missing output/did-cs/$$f — run the pipelines that produce this table." && exit 1); \
		cp "output/did-cs/$$f" "docs/str-paper/csv/$$f"; \
		echo "Copied csv/$$f"; \
	done
	@echo "Done. Commit docs/str-paper/figures/ and docs/str-paper/csv/ when outputs change."

whitepaper-deck: ## Build Beamer slides (needs pipeline outputs under output/did-cs-whitepaper)
	cd "$(current_abs_path)docs/white-paper/ppt" && latexmk -pdf -interaction=nonstopmode presentation.tex

run-did-matched-pipeline: build-only ## Run DiD analysis on trend-matched sample
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_matched_pipeline.py

white-paper: ## Build LaTeX policy brief (requires latexmk on host TeXLive/MacTeX)
	cd docs/white-paper && latexmk -pdf -interaction=nonstopmode main.tex

run-robustness-sweeps: ## k-neighbors + threshold percentile sweeps → docs/robustness/*.csv
	cd "$(current_abs_path)" && \
	  DATA_DIR="$(or $(DATA_DIR),$(current_abs_path)data)" \
	  PYTHONPATH="$(current_abs_path)src" \
	  uv run python src/housing/scripts/run_robustness_sweeps.py --all
