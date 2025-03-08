"""
serpapi_fetch/config_manager.py

Purpose:
--------
This module handles loading non-secret configuration for the SerpAPI patent-fetching
process from a local config.yaml file, and ensures the SERPAPI_KEY is available
(either from .env or user prompt).

Why It's Needed:
---------------
- We want to keep environment-sensitive or runtime-adjustable parameters out of 
  the codebase, instead placing them in a config file.
- The SERPAPI_KEY remains secret, so it's handled via environment variables or .env.

Usage:
------
1) In your main script (e.g., serpapi_fetch/main.py), call `load_serpapi_config()` 
   to retrieve a SerpAPIConfig dataclass with relevant fields.
2) Call `ensure_serpapi_key()` to guarantee the user or environment has the 
   SERPAPI_KEY set.
3) Use these values to drive the fetching logic in fetch_manager.py.
"""

import os
import getpass
import yaml
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv


@dataclass
class SerpAPIConfig:
    """
    Non-secret config for fetching from SerpAPI.

    Fields:
    -------
    input_folder : str
        Path to the folder containing multiple CSV files, each requiring 
        reading/merging for patent retrieval.
    output_jsonl : str
        Path to the output JSONL file where SerpAPI results will be appended.
    filter_condition : str
        Substring used to filter CSV rows by certain columns (e.g., "Merck Sharp & Dohme").
        If empty, no filtering occurs.
    filter_columns : List[str]
        Names of columns in which we search filter_condition (logical OR across columns).
    sort_by : str
        Column name used for descending sorting. If empty, skip sorting.
    limit : int
        Maximum number of rows to keep after sorting. If <= 0, no limit.
    remove_spaces_column : str
        Name of a column (e.g. "Document ID") where spaces should be removed 
        from each cell's string.

    max_retries : int
        Number of retries to attempt if a fetch to SerpAPI fails (due to network or rate limit).
    sleep_seconds : int
        Seconds to wait between retries.
    skip_if_has_pdf : bool
        If True, skip re-fetching a patent if the existing record in JSONL has a 'pdf' key,
        indicating a successful prior fetch.

    Production Considerations:
    --------------------------
    - Keep expansions or changes here so the fetch_manager.py remains logic-focused.
    - If you have multiple environments (dev, staging, prod), 
      consider distinct config files or dynamic paths.
    """
    input_folder: str
    output_jsonl: str
    filter_condition: str
    filter_columns: List[str]
    sort_by: str
    limit: int
    remove_spaces_column: str

    max_retries: int
    sleep_seconds: int
    skip_if_has_pdf: bool


def load_serpapi_config(config_path: str = "config.yaml") -> SerpAPIConfig:
    """
    Reads a YAML file from the same directory as this script and maps it
    into a SerpAPIConfig dataclass instance.

    Parameters
    ----------
    config_path : str
        The filename of the config YAML (default: "config.yaml").

    Returns
    -------
    SerpAPIConfig
        A dataclass holding all relevant non-secret SerpAPI settings.

    Raises
    ------
    FileNotFoundError
        If the config_path is not found at runtime.

    Production-Level Details:
    -------------------------
    - This function uses os.path.dirname(__file__) to locate config.yaml 
      relative to the serpapi_fetch/ folder, avoiding collisions with 
      other config files in the repository.
    - For large or nested configs, you can expand or nest the YAML structure
      and parse accordingly.
    """
    full_path = os.path.join(os.path.dirname(__file__), config_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Config file not found at {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return SerpAPIConfig(
        input_folder=raw.get("input_folder", ""),
        output_jsonl=raw.get("output_jsonl", ""),
        filter_condition=raw.get("filter_condition", ""),
        filter_columns=raw.get("filter_columns", []),
        sort_by=raw.get("sort_by", ""),
        limit=raw.get("limit", 0),
        remove_spaces_column=raw.get("remove_spaces_column", ""),
        max_retries=raw.get("max_retries", 3),
        sleep_seconds=raw.get("sleep_seconds", 2),
        skip_if_has_pdf=raw.get("skip_if_has_pdf", True)
    )


def ensure_serpapi_key():
    """
    Ensures that the SERPAPI_KEY environment variable is set, 
    loading .env if available, otherwise prompting the user.

    Steps:
    ------
    1) load_dotenv() attempts to read a .env file in the project root.
    2) If SERPAPI_KEY is still not found in os.environ, 
       we ask the user interactively.

    Production-Level Details:
    -------------------------
    - For CI/CD or container deployments, prefer setting SERPAPI_KEY 
      in environment variables or a secure vault instead of prompting.
    - If .env is used, ensure it's .gitignored to avoid committing keys to source control.
    """
    load_dotenv()
    if not os.environ.get("SERPAPI_KEY"):
        key = getpass.getpass("Enter your SERPAPI_KEY: ")
        os.environ["SERPAPI_KEY"] = key