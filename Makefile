# SignX-Studio Makefile
# Convenience targets for development, testing, and deployment

.PHONY: help install install-ml test test-ml lint lint-ml format clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install base dependencies
	pip install -r requirements.txt

install-ml:  ## Install ML/AI dependencies
	conda env create -f environment-ml.yml
	conda run -n signx-ml pip install torch-scatter torch-sparse torch-cluster torch-spline-conv -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

test:  ## Run core tests
	pytest services/api/tests/ -v

test-ml:  ## Run ML pipeline tests
	pytest services/ml/tests/ -v --cov=services/ml

lint:  ## Run linter on core code
	ruff check services/api/

lint-ml:  ## Run linter on ML code  
	ruff check services/ml/

format:  ## Format code with black
	black services/api/ services/ml/

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache

# ML-specific targets
extract-pdfs:  ## Extract cost data from PDFs
	python scripts/extract_pdfs.py --input data/pdfs/cost_summaries --output data/raw/extracted_costs.parquet --verbose

train-cost-model:  ## Train cost prediction model
	python scripts/train_cost_model.py --data data/raw/extracted_costs.parquet --output models/cost/v1

test-predictions:  ## Test AI predictions
	python scripts/test_ai_prediction.py

# Docker targets
up:  ## Start all services
	cd infra && docker-compose up -d

down:  ## Stop all services
	cd infra && docker-compose down

logs:  ## View service logs
	cd infra && docker-compose logs -f api

# Combined workflows
ml-pipeline: extract-pdfs train-cost-model test-predictions  ## Run full ML pipeline

all: lint test  ## Run linter and tests
