"""
abstract_dao.py

Purpose:
--------
Defines an abstract base class (ABC) for Table DAOs (Data Access Objects).
Each concrete DAO class in this system should inherit from AbstractTableDAO
and implement its own table-specific create/insert logic.

Why This Matters:
-----------------
- Enforces a consistent interface among various table DAOs.
- Encourages clean separation of database schema creation and data insertion 
  from higher-level application logic.

Usage:
------
1) Inherit from AbstractTableDAO:
    class SomeTableDAO(AbstractTableDAO):
        def create_table(self, conn):
            # CREATE TABLE IF NOT EXISTS ...
        def insert(self, conn, data):
            # INSERT INTO ...
2) `create_table(conn)` can be called to ensure the table schema is created.
3) `insert(conn, *args, **kwargs)` handles inserting row(s) specific to that table.

Production-Level Considerations:
-------------------------------
- Additional CRUD methods (delete, update, select) can be added if needed.
- The abstract approach helps maintain consistency if you have multiple DAO classes 
  each corresponding to a different table schema.
- You may want to catch and log any sqlite3 operational errors or handle transactions 
  for robust error handling in production.
"""

from abc import ABC, abstractmethod
import sqlite3
from typing import Any


class AbstractTableDAO(ABC):
    """
    Abstract base class for a Table DAO (Data Access Object).

    Methods to Implement:
    ---------------------
    create_table(conn: sqlite3.Connection) -> None
        Create the corresponding database table if it does not already exist.
    insert(conn: sqlite3.Connection, *args: Any, **kwargs: Any) -> None
        Insert data into the table. Method signature can be flexible for 
        different table schemas.

    Example:
    --------
    class PatentTableDAO(AbstractTableDAO):
        def create_table(self, conn):
            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS patents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patent_id TEXT NOT NULL,
                    title TEXT
                    -- ... other columns ...
                )
            \"\"\")

        def insert(self, conn, patent_id, title):
            conn.execute(
                "INSERT INTO patents (patent_id, title) VALUES (?, ?)",
                (patent_id, title)
            )

    Production Recommendations:
    ---------------------------
    - Wrap operations in transactions or context managers for atomicity.
    - Consider unique constraints or indexes if needed.
    - Add additional error handling/logging as appropriate.
    """

    @abstractmethod
    def create_table(self, conn: sqlite3.Connection) -> None:
        """
        Create the table if it does not already exist.

        Parameters
        ----------
        conn : sqlite3.Connection
            The database connection to use for executing SQL statements.

        Raises
        ------
        sqlite3.Error
            If any SQL execution fails during table creation.
        """
        pass

    @abstractmethod
    def insert(self, conn: sqlite3.Connection, *args: Any, **kwargs: Any) -> None:
        """
        Insert data into the table.

        Parameters
        ----------
        conn : sqlite3.Connection
            The database connection to use for inserting records.
        *args, **kwargs : Any
            Flexible parameters depending on the specific DAO/table fields.

        Raises
        ------
        sqlite3.Error
            If SQL insertion fails.
        """
        pass