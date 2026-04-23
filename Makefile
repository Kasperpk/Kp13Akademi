.DEFAULT_GOAL := help
.PHONY: help dev seed run-coach run-player test eval-epm generate-session clean lint

help: ## Show available targets
	@echo "KP13 Akademi — available make targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Install all dependencies (app + generator + dev tools)
	pip install -r app/requirements.txt -r generator/requirements.txt -r requirements-dev.txt

seed: ## Populate DB with Sofus and Felix
	python app/seed.py

run-coach: ## Start the Streamlit coach console
	streamlit run app/Home.py

run-player: ## Start the FastAPI player app on :8000
	cd app && python -m uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload

test: ## Run the pytest suite
	pytest

lint: ## Run ruff and mypy
	ruff check .
	mypy app

eval-epm: ## Run the EPM extraction eval (stub until >=10 cases exist)
	@count=$$(find skills/epm-extraction/evals/cases -name '*.json' 2>/dev/null | wc -l | tr -d ' '); \
	if [ "$$count" -lt 10 ]; then \
		echo "$$count/10 cases — waiting for more calibrated sessions before running eval."; \
	else \
		echo "Running eval on $$count cases..."; \
		echo "(harness runner not yet implemented — see issue #2)"; \
	fi

generate-session: ## Launch the interactive session generator
	python generator/generate.py

clean: ## Remove __pycache__ and *.pyc (prompts for confirmation)
	@read -p "Delete __pycache__ and *.pyc files? [y/N] " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
		find . -type d -name __pycache__ -prune -exec rm -rf {} +; \
		find . -type f -name '*.pyc' -delete; \
		echo "Cleaned."; \
	else \
		echo "Aborted."; \
	fi
