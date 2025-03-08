"""
managers/db_manager.py

Database Manager using SQLAlchemy & LangChain's SQLDatabase.

Explanation:
-----------
This module defines a DatabaseManager class that:
1. Validates a local SQLite DB file path.
2. Initializes a SQLAlchemy engine with a StaticPool to allow multi-thread access
   without "check_same_thread" issues.
3. Wraps the engine in a LangChain SQLDatabase for easy agent-based SQL queries.

In a production environment, you may:
- Integrate connection pooling for larger scale usage.
- Catch and log database exceptions (e.g., connection timeouts).
- Optionally switch to another relational DB (Postgres, MySQL) with minimal code changes.
"""

import os
from dataclasses import dataclass, field
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from typing import List, Any

from langchain_community.utilities.sql_database import SQLDatabase

from .config_manager import DBConfig


@dataclass
class DatabaseManager:
    """
    Manages the creation of a SQLAlchemy engine and a LangChain SQLDatabase object.
    Provides an interface to list tables or execute direct SQL if needed.

    Production Considerations:
    - Ensure db_config points to a valid SQLite DB file.
    - For concurrency, StaticPool plus check_same_thread=False is used
      to avoid threading issues. For actual production, you might consider
      a more robust pool class if using advanced features.
    - If running in containerized environments, confirm that the file path
      is mounted properly and has the correct permissions.
    """
    db_config: DBConfig
    engine: Any = field(init=False)
    langchain_db: SQLDatabase = field(init=False)

    def __post_init__(self):
        """
        Initialize the SQLite engine and wrap it in a LangChain SQLDatabase.

        Raises:
            FileNotFoundError: if the SQLite file does not exist.

        Production Notes:
        - If the DB file is large or under heavy load, monitor performance
          and consider a more advanced DB engine.
        - Additional error-handling logic can be added if file corruption
          or permission issues occur.
        """
        if not os.path.exists(self.db_config.sqlite_db_path):
            raise FileNotFoundError(
                f"SQLite DB not found at path: {self.db_config.sqlite_db_path}"
            )

        # Create a SQLite engine with a static pool to avoid concurrency issues
        # across threads while ignoring 'check_same_thread'.
        self.engine = create_engine(
            f"sqlite:///{self.db_config.sqlite_db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )

        # Wrap the engine in a LangChain SQLDatabase for agent-friendly usage
        self.langchain_db = SQLDatabase(self.engine)

    def list_tables(self) -> List[str]:
        """
        Return a list of table names in the SQLite database.

        Returns:
            A list of table names found in the connected SQLite DB.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';")
            ).fetchall()
        return [r[0] for r in rows]