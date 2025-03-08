"""
db_context.py

Purpose:
--------
Provides a context manager for SQLite database connections, enabling clean,
transactional usage via `with db_connection(db_path) as conn:` syntax.

Why This Matters:
-----------------
- Automatically handles creation of the database folder (if it doesn't exist).
- Ensures foreign key support is enabled for SQLite.
- Commits changes upon normal completion or rolls back on exceptions.
- Closes the connection in a finally block, preventing resource leaks.

Usage:
------
Example:
    from db_context import db_connection

    with db_connection("path/to/patent.db") as conn:
        # Perform SQL operations:
        conn.execute("INSERT INTO table_name(...) VALUES(...)")
        # If an exception is raised, changes are rolled back automatically.

Production-Level Notes:
-----------------------
- If your environment has concurrency or transaction complexity, consider 
  separate transaction blocks or more granular commit control.
- For large-scale usage, be mindful of connection overhead. 
  Typically, a single connection can be used across multiple operations.
- Make sure foreign_keys=ON is required for correct relational integrity 
  (otherwise, SQLite won't enforce foreign keys).

"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator


@contextmanager
def db_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    A context manager for managing an SQLite database connection lifecycle.

    Steps Performed:
    ---------------
    1) Ensures the directory for `db_path` exists, creating it if necessary.
    2) Opens a connection to the specified SQLite database file.
    3) Enables foreign key constraints via PRAGMA foreign_keys=ON.
    4) Uses sqlite3.Row for row_factory to enable dictionary-like access to columns.
    5) Yields the connection object for use within the `with` block.
    6) Commits all changes if the block exits without exception; 
       otherwise rolls them back and re-raises the exception.
    7) Closes the connection in a finally block.

    Parameters
    ----------
    db_path : str
        The filepath to the SQLite database. Parent directories are created if absent.

    Yields
    ------
    sqlite3.Connection
        An active, ready-to-use SQLite connection object.

    Raises
    ------
    Exception
        Any exception raised inside the `with` block triggers a rollback.
    """
    # 1) Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 2) Open the connection
    conn = sqlite3.connect(db_path)

    # 3) Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")

    # 4) Use Row factory for more convenient row access
    conn.row_factory = sqlite3.Row

    try:
        # 5) Yield the connection for usage
        yield conn
        # 6) Commit changes if no exception
        conn.commit()
    except Exception:
        # Rollback on exception
        conn.rollback()
        raise
    finally:
        # 7) Close connection
        conn.close()