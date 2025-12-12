.PHONY: help install validate deploy destroy status dev clean

help:
	@echo "Tagsonomy Databricks App Deployment"
	@echo "===================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install databricks CLI and dependencies"
	@echo "  make validate   - Validate the bundle configuration"
	@echo "  make deploy     - Deploy the app to Databricks (dev)"
	@echo "  make deploy-prod - Deploy the app to Databricks (production)"
	@echo "  make destroy    - Destroy the deployed app"
	@echo "  make status     - Check the status of the deployed app"
	@echo "  make dev        - Run the app locally for development"
	@echo "  make clean      - Clean up local artifacts"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Run 'databricks auth login' to authenticate"

install:
	pip install -r requirements.txt

validate:
	databricks bundle validate

deploy:
	databricks bundle deploy --target dev

run: deploy
	databricks bundle run tagsonomy-app --target dev

destroy:
	databricks bundle destroy --target dev

status:
	databricks apps get tagsonomy-app

dev:
	@echo "Starting local development server..."
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Creating one..."; \
		python3 -m venv venv; \
	fi
	. venv/bin/activate && pip install -r requirements.txt && python tagso/app.py

clean:
	@echo "Cleaning up local artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .databricks
	@echo "Cleanup complete!"

