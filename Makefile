
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

.PHONY: build-only run-interactive test-pipeline test clean help devcontainer

# Build Docker image 
build-only: ## Build Docker image only
	docker compose build

run-interactive: build-only ## Run interactive bash session in container
	docker compose run -it --rm --service-ports $(mount_data) $(project_name) /bin/bash

test-pipeline: build-only ## Run the pipeline example
	docker compose run --rm $(mount_data) $(project_name) uv run python src/pipeline/scripts/pipeline_usage.py

test: build-only ## Run all tests with pytest
	docker compose run --rm $(mount_data) $(project_name) uv run python -m pytest -v

clean: ## Clean up Docker images and containers
	docker compose down --rmi all --volumes --remove-orphans
	docker image prune -f

devcontainer: ## Build and prepare devcontainer (run this before opening in VS Code/Cursor)
	docker compose build
	@echo "Dev container ready! Open this folder in VS Code/Cursor and select 'Reopen in Container'"

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@echo "  build-only        Build Docker image only"
	@echo "  clean             Clean up Docker images and containers"
	@echo "  devcontainer      Build and prepare devcontainer for VS Code/Cursor"
	@echo "  help              Show this help message"
	@echo "  run-interactive   Run interactive bash session in container"
	@echo "  test              Run all tests with pytest"
	@echo "  test-pipeline     Run the pipeline example"
	@echo ""
	@echo "Optional environment variables (.env file):"
	@echo "  DATA_DIR - Custom data directory path (defaults to ./data)"
	@echo ""


