"""
text2sql/main.py

Application entry point. Instantiates configs, managers, and runs the agent in a loop (CLI mode).

Production Context:
-------------------
- This script sets up tracing to LangSmith (if desired) and orchestrates the 
  entire Text2SQL pipeline from reading config to interacting with the user in a CLI loop.
- For real deployments, you might replace the CLI loop with a REST or WebSocket server, 
  or integrate this agent into a bigger application.
- Logging is initialized here to ensure we catch errors from config, database initialization, etc.
"""

import os

# Enable LangSmith (LangChain) tracing
os.environ["LANGSMITH_TRACING"] = "true"

# Optionally specify a project name (makes it easier to filter runs in the UI)
# https://www.langchain.com/langsmith
os.environ["LANGSMITH_PROJECT"] = "Patent_Project_Local_Text2Sql_Test"

import sys

from managers.config_manager import load_config, setup_logging
from managers.db_manager import DatabaseManager
from managers.agent_manager import Text2SQLAgent


def main():
    """
    CLI-based main function.
    1) Loads configuration from config.yaml
    2) Initializes the DatabaseManager (SQLite) 
    3) Constructs a Text2SQLAgent that knows how to use local SQL tools + schema RAG
    4) Enters a loop where the user can type queries. 
       Type "exit" to quit.

    Production Considerations:
    - If running in Docker or another environment, ensure config.yaml 
      and schema_docs.json are mounted/packaged properly.
    - If a web/GUI interface is required, you’d embed this agent logic 
      in a server framework (Flask, FastAPI, etc.) rather than a CLI loop.
    - Because we set LANGSMITH_TRACING = "true", intermediate chain-of-thought data 
      can be viewed in your LangSmith dashboard, aiding in debugging and optimization.
    """
    logger = setup_logging()
    logger.info("Starting Text-to-SQL App")

    # 1) Locate the config.yaml file relative to this script
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # 2) Create and verify the DatabaseManager
    try:
        db_manager = DatabaseManager(db_config=config.db)
    except Exception as e:
        logger.error(f"Failed to init DatabaseManager: {e}")
        sys.exit(1)

    # 3) Create Text2SQLAgent with references to config, DB manager, and schema docs
    schema_docs_path = os.path.join(os.path.dirname(__file__), "schema_docs.json")
    try:
        agent = Text2SQLAgent(
            config=config,
            db_manager=db_manager,
            schema_docs_path=schema_docs_path
        )
    except Exception as e:
        logger.error(f"Failed to create Text2SQLAgent: {e}")
        sys.exit(1)

    # 4) Simple CLI loop
    # In production, consider replacing with a server-based or event-driven approach.
    while True:
        user_input = input("\nEnter your query (or 'exit' to quit): ")
        if user_input.strip().lower() == "exit":
            logger.info("Exiting application.")
            break

        response = agent.query_text(user_input)
        print(f"\nAgent response:\n{response}\n")


if __name__ == "__main__":
    main()