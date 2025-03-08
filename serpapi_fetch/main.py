"""
serpapi_fetch/main.py

Purpose:
--------
This script serves as the main entry point for fetching patent data from SerpAPI.
It coordinates the configuration loading, SERPAPI_KEY checking, and the bulk fetch process.

Usage:
------
From the project root:
    python -m serpapi_fetch.main

Behavior:
---------
1. Reads non-secret configuration from serpapi_fetch/config.yaml (via load_serpapi_config).
2. Ensures a valid SERPAPI_KEY is present in the environment or .env (via ensure_serpapi_key).
3. Constructs a SerpAPIFetchManager, passing in config-driven parameters (folder paths, 
   filtering options, retry settings, etc.).
4. Invokes fetch_patents_in_bulk(), which:
   - Reads/merges CSV files
   - Optionally filters and sorts
   - Skips already-fetched patents if "pdf" is detected
   - Calls SerpAPI with retry logic, appending results to a JSONL file

Error Handling:
---------------
- If any exception occurs, it's logged via logger.exception, and we exit the script with code 1.
- The console should now show both debug/info messages (see configure_fetch_logging),
  while 'serpapi_fetch_errors.log' stores only error-level logs.

Production Considerations:
--------------------------
- For large-scale usage, ensure your SERPAPI_KEY has sufficient rate limits or consider
  scheduling or throttling.
- If you have multiple input folders or drastically different columns, 
  you can expand the config or pass extra arguments to SerpAPIFetchManager.
- If 'SERPAPI_KEY' is missing, we prompt the user or raise an error, returning exit code 1.
"""

import sys
import logging

from .config_manager import load_serpapi_config, ensure_serpapi_key
from .fetch_manager import SerpAPIFetchManager


def configure_fetch_logging():
    """
    Sets up a logger named 'serpapi_fetch' that:
      - Logs DEBUG+ messages to the console
      - Logs ERROR+ messages to a file named 'serpapi_fetch_errors.log'
    Returns the configured logger.
    """
    logger = logging.getLogger("serpapi_fetch")
    logger.setLevel(logging.DEBUG)  # Or INFO if you prefer less verbosity in console

    # Console handler (to see debug/info/warn/error on terminal)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(name)s - %(message)s")
    ch.setFormatter(formatter)

    # File handler (to capture errors only)
    fh = logging.FileHandler("serpapi_fetch_errors.log", mode="a", encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


def main():
    """
    Main function orchestrating the SerpAPI fetch process.

    Steps:
    ------
    1) Load serpapi_fetch/config.yaml
    2) Ensure SERPAPI_KEY is present in environment
    3) Construct SerpAPIFetchManager with config-driven parameters
    4) Run fetch_patents_in_bulk() to read CSV files, filter, and fetch from SerpAPI
    """
    # Use the custom logger for serpapi_fetch
    logger = configure_fetch_logging()
    logger.info("Starting serpapi_fetch main script...")

    try:
        # 1) Load serpapi_fetch/config.yaml
        config = load_serpapi_config("config.yaml")
        logger.debug(f"Loaded config: {config}")

        # 2) Verify SERPAPI_KEY is set (prompts if missing)
        ensure_serpapi_key()
        logger.debug("SERPAPI_KEY verified/prompted as needed.")

        # 3) Build the fetch manager with all config parameters
        fetch_mgr = SerpAPIFetchManager(
            input_folder=config.input_folder,
            output_jsonl=config.output_jsonl,
            filter_condition=config.filter_condition,
            filter_columns=config.filter_columns,
            sort_by=config.sort_by,
            limit=config.limit,
            remove_spaces_column=config.remove_spaces_column,
            max_retries=config.max_retries,
            sleep_seconds=config.sleep_seconds,
            skip_if_has_pdf=config.skip_if_has_pdf,
            logger=logger  # pass the same logger
        )

        # 4) Execute the bulk fetch process
        fetch_mgr.fetch_patents_in_bulk()
        logger.info("Finished SerpAPI fetching process successfully.")

    except Exception as e:
        logger.exception(f"Error in serpapi_fetch main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()