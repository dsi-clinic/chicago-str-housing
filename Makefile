
# Default target
.DEFAULT_GOAL := help

# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
# PROJECT_NAME
project_name := "2025-autumn-city-of-chicago-housing"
project_dir := "$(current_abs_path)"

# environment variables
include .env

# Check required environment variables
ifeq ($(DATA_DIR),)
    $(error DATA_DIR must be set in .env file)
endif


# Build Docker image 
# Global mount for data directory
mount_data := -v $(DATA_DIR):/project/data

.PHONY: build-only run-interactive test-pipeline test clean help devcontainer

# Build Docker image 
build-only: ## Build Docker image only
	docker compose build

run-interactive: build-only ## Run interactive bash session in container
	docker compose run -it --rm $(mount_data) $(project_name) /bin/bash

test-pipeline: build-only ## Run the pipeline example
	docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/pipeline_example.py

test: build-only ## Run all tests with pytest
	docker compose run --rm $(mount_data) $(project_name) uv run python -m pytest tests/ -v

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
	@echo "Environment variables required:"
	@echo "  DATA_DIR - Path to data directory (set in .env file)"
	@echo ""


