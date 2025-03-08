"""
managers/config_manager.py

Loads config from config.yaml, sets up logging, and defines dataclasses for configs.

Production Context:
-------------------
- This file encapsulates the core application configuration, including:
  * OpenAI model settings (excluding the API key),
  * Database path info,
  * Vectorstore collection naming.
- Logging is also initialized here, directing logs to both console and file.
- If OPENAI_API_KEY isn't found in environment variables or a .env file, the user is
  prompted for it interactively, preventing plaintext exposure of credentials in code.
"""

import os
import sys
import getpass
import logging
import yaml
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class OpenAIConfig:
    """
    Holds non-secret config for OpenAI, such as the model name.
    The actual API key is fetched from environment or .env at runtime.

    Production Considerations:
    - This approach prevents embedding secrets in YAML files,
      reducing the risk of accidental key exposure in version control.
    - If usage scales, consider secret management services or vaults.
    """
    model_name: str = "gpt-4"


@dataclass
class DBConfig:
    """
    Configuration for the SQLite database.
    Typically references the file path for the SQLite DB.

    Production Considerations:
    - Ensure the file path is valid and has proper read/write permissions.
    - For large or production-scale usage, a move to Postgres/MySQL might be warranted.
    """
    sqlite_db_path: str


@dataclass
class AppConfig:
    """
    Aggregates the overall application configuration, holding:
    - OpenAI parameters (OpenAIConfig)
    - Database path info (DBConfig)
    - The name of the vectorstore collection.

    Production Considerations:
    - Additional top-level fields can be added for advanced features (caching, concurrency, etc.).
    - Keep environment-agnostic configs here; keep secrets in environment variables.
    """
    openai: OpenAIConfig
    db: DBConfig
    collection_name: str = "schema_docs_collection"


def load_config(config_path: str) -> AppConfig:
    """
    Loads an AppConfig object from a YAML file at config_path.
    If the file is missing or invalid, FileNotFoundError is raised.

    Returns:
        An AppConfig object with model name, DB path, and vectorstore collection name.

    Production Notes:
    - You can add extra validation, e.g. checking if certain keys exist.
    - Keep the YAML minimal and environment-agnostic. If more advanced,
      consider merging environment-specific overrides.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    openai_conf = OpenAIConfig(**raw["openai"])
    db_conf = DBConfig(**raw["db"])
    coll_name = raw.get("collection_name", "schema_docs_collection")

    return AppConfig(
        openai=openai_conf,
        db=db_conf,
        collection_name=coll_name
    )


def setup_logging(level=logging.INFO) -> logging.Logger:
    """
    Sets up application logging, outputting to both console and logs/app.log.
    If called multiple times, won't re-add handlers due to logger.handlers check.

    Production Considerations:
    - For high-volume logs, consider rotating file handlers (e.g. TimedRotatingFileHandler).
    - In containerized environments, standard output logging might be preferred.
    - Adjust log levels or integrate with monitoring solutions (Splunk, ELK, etc.).
    """
    logger = logging.getLogger("text_sql_app")
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def ensure_openai_key():
    """
    Ensures OPENAI_API_KEY is in environment or .env.
    If not found, prompts the user (interactive).

    Production Considerations:
    - This approach is suitable for dev/test. For production, prefer
      an automated and secure key retrieval (CI/CD vault, secrets manager).
    - Loading .env is convenient, but ensure .env is .gitignored.
    """
    load_dotenv()  # Attempt to load from .env if present

    if not os.environ.get("OPENAI_API_KEY"):
        key = getpass.getpass("Enter your OPENAI_API_KEY: ")
        os.environ["OPENAI_API_KEY"] = key