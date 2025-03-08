################################################################################
# Makefile for the "patents" project
# ----------------------------------
# This file provides a set of commands (targets) to streamline common tasks:
#   1) Create a Conda environment named "patent" with Python 3.12
#   2) Install dependencies from the root-level requirements.txt
#   3) Build/Update the local patent DB by calling database_constraction scripts
#   4) Run the text2sql CLI (interactive agent)
#   5) Fetch patent data from SerpAPI (serpapi_fetch/main.py)
#   6) Clean logs/pycache or show a help summary
#
# Instructions:
#   - From the project root (where this file resides), run:
#       make <target>
#   - For example:
#       make create-env
#       make install
#       make build-db
#       make run-text2sql
#       make fetch-serpapi
#       make clean
#       make help
#
# Production-Level Notes:
#   - 'create-env' uses conda for environment management. If you prefer virtualenv
#     or pipenv, adjust accordingly.
#   - The environment name is "patent", but you can rename it if desired.
#   - 'build-db' calls the Python module in database_constraction to populate
#     or update 'data/patent.db'.
#   - 'run-text2sql' starts the text2sql CLI from text2sql/main.py.
#   - 'fetch-serpapi' runs serpapi_fetch/main.py to retrieve patent details
#     from SerpAPI and write them to data/SerpAPI/patent_data.jsonl.
#   - Each target includes minimal error-handling. For robust CI/CD, consider
#     further checks or retrieving exit codes.
#   - 'clean' removes logs, cached Python artifacts, and other temporary files.
################################################################################

# Name of the Conda environment
ENV_NAME = patent

# Path to the Conda environment file
ENV_YML = environment.yml

.PHONY: create-env update-env install build-db run-text2sql fetch-serpapi clean help

create-env: ## Creates a Conda environment from environment.yml.
	@echo "==== Creating conda environment '$(ENV_NAME)' from $(ENV_YML) ===="
	conda env create -f $(ENV_YML)

update-env: ## Updates an existing Conda environment from environment.yml.
	@echo "==== Updating conda environment '$(ENV_NAME)' with latest dependencies ===="
	conda env update -f $(ENV_YML)

install: ## Ensures Conda environment is updated and installs additional pip dependencies if any.
	@echo "==== Ensuring conda env '$(ENV_NAME)' is up to date ===="
	conda env update -f $(ENV_YML)

build-db: ## Calls the database_constraction/main.py script to populate/update data/patent.db.
	@echo "==== Building database with database_constraction scripts ===="
	conda run -n $(ENV_NAME) python -m database_constraction.main

run-text2sql: ## Launches the text2sql CLI by running text2sql/main.py interactively
	@echo "==== Running text2sql main.py with live-stream ===="
	conda run --live-stream -n $(ENV_NAME) python text2sql/main.py

fetch-serpapi: ## Runs serpapi_fetch/main.py to retrieve patent details from SerpAPI.
	@echo "==== Fetching patents from SerpAPI ===="
	conda run --live-stream -n $(ENV_NAME) python -m serpapi_fetch.main

clean: ## Removes logs, cached Python artifacts, and any __pycache__ directories.
	@echo "==== Cleaning logs & pycache ===="
	rm -f text2sql/logs/app.log
	rm -f serpapi_fetch_errors.log
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true

help: ## Prints out a short usage summary for each target defined in this Makefile.
	@echo "Usage: make [target]"
	@echo
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_0-9-]+:.*##/ \
	{ printf "  \033[36m%-17s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)