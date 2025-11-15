.PHONY: help install setup setup-fresh run run-cpu clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt
	python -m nltk.downloader stopwords

setup: ## Complete setup: create venv (if needed), install deps, download NLTK data
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	else \
		echo "Virtual environment already exists, skipping creation..."; \
	fi
	. venv/bin/activate && pip install --upgrade pip setuptools wheel
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && python -m nltk.downloader stopwords
	@echo "Setup complete! Activate virtual environment with: source venv/bin/activate"

setup-fresh: ## Recreate venv from scratch (removes existing venv)
	@echo "Removing existing virtual environment..."
	rm -rf venv
	@echo "Creating fresh virtual environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip setuptools wheel
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && python -m nltk.downloader stopwords
	@echo "Fresh setup complete! Activate virtual environment with: source venv/bin/activate"

run: ## Run the FastAPI application
	@echo "Checking for existing server on port 8000..."
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@sleep 1
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@if [ ! -f "data/postings_list.json" ]; then \
		echo "❌ postings_list.json not found in data/ directory."; \
		echo "   Please run 'make index' to generate it first."; \
		exit 1; \
	fi
	@echo "🚀 Starting FastAPI server..."
	. venv/bin/activate && uvicorn app:app --reload --host 0.0.0.0 --port 8000

run-cpu: ## Run the FastAPI application in CPU-only mode
	@echo "Checking for existing server on port 8000..."
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@sleep 1
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@if [ ! -f "data/postings_list.json" ]; then \
		echo "❌ postings_list.json not found in data/ directory."; \
		echo "   Please run 'make index' to generate it first."; \
		exit 1; \
	fi
	@echo "🚀 Starting FastAPI server (CPU-only mode)..."
	. venv/bin/activate && FORCE_CPU=1 uvicorn app:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run the application in production mode
	gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000

scrape: ## Run the Wikipedia scraper
	python scraper.py

index: ## Build the inverted index
	python indexer.py

map-docs: ## Generate document ID to URL mapping
	python doc_mapper.py

build-data: scrape index map-docs ## Build all data files (scrape, index, map)

clean: ## Remove cache files and __pycache__ directories
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "Cleanup complete!"

test: ## Run tests (placeholder)
	@echo "Tests not yet implemented"

lint: ## Run pylint on all Python files
	@echo "🔍 Running pylint..."
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	. venv/bin/activate && pylint --rcfile=.pylintrc *.py || true

format: ## Format code with black
	@echo "🎨 Formatting code with black..."
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	. venv/bin/activate && black --line-length 100 *.py

format-check: ## Check code formatting without making changes
	@echo "🔍 Checking code formatting..."
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	. venv/bin/activate && black --check --line-length 100 *.py

