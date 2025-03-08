"""
main.py

Purpose:
--------
Entry point for database construction and data insertion logic.
This script:

1) Configures logging via dictConfig, storing logs to both console and 'patent_errors.log'.
2) Defines file paths for the SQLite DB and the JSONL data (SerpAPI export).
3) Initializes a PatentService object to manage table creation and data insertion.
4) Creates all necessary tables.
5) Parses records from JSONL and inserts them into the database.
6) Demonstrates a quick verification query.

Usage:
------
From the project root:
    python database_constraction/main.py
or
    python -m database_constraction.main

Production-Level Notes:
-----------------------
- Logging:
  * The dictConfig approach allows granular control of formats, levels, handlers.
  * 'DEBUG' is set on the root logger, which may be too verbose for production. 
    Adjust if needed.
- File Paths:
  * Uses pathlib.Path for db_path and jsonl_path to improve cross-platform compatibility.
  * Ensure 'data/patent.db' and 'data/SerpAPI/patent_data.jsonl' are correct for your environment.
- Data Verification:
  * The final code snippet queries the first five records from 'patents' table 
    to confirm successful insertion.
"""

import logging
import logging.config
from pathlib import Path

from .patent_service import PatentService
from .db_context import db_connection


def setup_logging():
    """
    Configure Python logging via dictConfig, logging to both console and file.

    Why This Matters:
    -----------------
    - Logging can be toggled or refined for debugging vs. production usage.
    - Root logger is set to DEBUG for demonstration. In real deployments, 
      consider using INFO or WARN to reduce log noise.
    - 'patent_errors.log' logs all messages at INFO level or above. 
      If you need separate error vs. info logs, adjust accordingly.

    Production Tips:
    ---------------
    - You can rotate or archive logs using TimedRotatingFileHandler or similar.
    - Adjust 'disable_existing_loggers' if you have other loggers in your system.
    """
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "DEBUG"
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "patent_errors.log",
                "mode": "a",
                "formatter": "default",
                "level": "INFO"
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "DEBUG"
        }
    }

    logging.config.dictConfig(LOGGING_CONFIG)


def main():
    """
    Main function to:
    1) Set up logging.
    2) Define paths for DB and JSONL data.
    3) Initialize PatentService and set up the DB.
    4) Parse and insert records from JSONL.
    5) Verify insertion by querying 'patents' table.
    """
    # 1) Configure logging
    setup_logging()

    # 2) Build paths to DB and JSONL
    db_path = Path("data") / "patent.db"
    jsonl_path = Path("data") / "SerpAPI" / "patent_data.jsonl"

    # 3) Create a PatentService instance
    service = PatentService(str(db_path))

    # 4) Setup DB schema (tables)
    service.setup_database()

    # 5) Read and insert JSONL data
    service.parse_and_insert_from_jsonl(str(jsonl_path))

    # 6) Simple verification: log first 5 rows from 'patents' table
    with db_connection(str(db_path)) as conn:
        cursor = conn.execute("SELECT patent_id, title, priority_date FROM patents LIMIT 5;")
        rows = cursor.fetchall()
        logging.info("[INFO] First 5 patents in DB:")
        for row in rows:
            logging.info(f"  -> patent_id={row['patent_id']} | title={row['title']} | priority_date={row['priority_date']}")


if __name__ == "__main__":
    main()