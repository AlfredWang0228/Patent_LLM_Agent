"""
managers/agent_manager.py

Defines the Text2SQLAgent that orchestrates the LLM, Tools, and final query interface
with thread-level memory persistence via LangGraph.

Explanation:
-----------
This module demonstrates how to build a text-to-SQL agent capable of:
1. Working with a local SQLite database for patent data.
2. Providing a conversation-driven interface using an LLM (ChatOpenAI).
3. Automatically calling SQL tools to answer queries about patents.
4. Maintaining multi-turn memory via LangGraph's MemorySaver, keyed by thread_id.

In a production environment:
- Make sure to handle errors (e.g., network timeouts to OpenAI, DB access failures).
- Carefully tune the system prompt to encourage the agent to use SQL tools rather
  than returning generic "I don't have external access" responses.
- Consider rate-limits and token usage, as ChatGPT or GPT-4 usage scales in cost.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.callbacks.manager import get_openai_callback

# LangGraph is used for building a ReAct-like agent that can call tools.
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .config_manager import AppConfig, ensure_openai_key
from .db_manager import DatabaseManager
from .vectorstore_manager import VectorStoreManager
from .tools_manager import SchemaDocRAGTool, ExtendedSQLSchemaTool


@dataclass
class Text2SQLAgent:
    """
    High-level agent that:
    - Leverages DatabaseManager for local SQLite patent data
    - Builds a VectorStore for schema docs (see VectorStoreManager)
    - Uses ChatOpenAI for LLM calls
    - Wires in custom Tools (RAG + Extended Schema)
    - Persists conversation state with MemorySaver

    Production Notes:
    - 'schema_docs_path' should always point to up-to-date schema docs, if the DB schema changes.
    - If performance or concurrency is critical, consider multi-threading or queue-based architecture.
    - Provide clear instructions in the system prompt to ensure the agent calls SQL tools appropriately.
    """

    config: AppConfig
    db_manager: DatabaseManager
    schema_docs_path: str

    llm: ChatOpenAI = field(init=False)
    agent_executor: Any = field(init=False)

    def __post_init__(self):
        """
        Initializes the LLM, toolkits, vectorstore, and sets up 
        a ReAct agent with thread-level memory.

        Steps (Production Rationale):
        1) ensure_openai_key -> Secures the OpenAI API Key from env or prompt.
        2) ChatOpenAI       -> Low temperature for deterministic SQL calls.
        3) SQLDatabaseToolkit -> Tools for listing/querying schema.
        4) VectorStoreManager -> Builds a local Chroma vectorstore for doc retrieval.
        5) Merges custom tools -> RAG + ExtendedSQLSchemaTool for schema doc usage.
        6) create_react_agent -> Provides a chain-of-thought capable agent 
           with MemorySaver for conversation continuity by thread_id.
        """
        # 1) Ensure the OPENAI_API_KEY environment variable is set
        ensure_openai_key()

        # 2) Create the ChatOpenAI LLM object
        self.llm = ChatOpenAI(
            model_name=self.config.openai.model_name,
            temperature=0.0
        )

        # 3) Build the SQL toolkit from the LangChain-Community library
        toolkit = SQLDatabaseToolkit(
            db=self.db_manager.langchain_db,
            llm=self.llm
        )
        base_tools = toolkit.get_tools()

        # Find and validate the presence of the 'sql_db_schema' tool
        sql_schema_tool = None
        for t in base_tools:
            if t.name == "sql_db_schema":
                sql_schema_tool = t
                break
        if not sql_schema_tool:
            raise RuntimeError("Unable to find tool 'sql_db_schema' in the SQLDatabaseToolkit")

        # 4) Build the vectorstore for RAG
        vs_manager = VectorStoreManager(
            schema_docs_path=self.schema_docs_path,
            collection_name=self.config.collection_name
        )
        vectorstore = vs_manager.vectorstore

        # 5) Create custom tools for schema docs RAG and extended schema
        with open(self.schema_docs_path, "r", encoding="utf-8") as f:
            doc_source = json.load(f)

        rag_tool = SchemaDocRAGTool(vectorstore=vectorstore)
        extended_tool = ExtendedSQLSchemaTool(
            sql_schema_tool=sql_schema_tool,
            doc_source=doc_source
        )
        all_tools = base_tools + [rag_tool, extended_tool]

        # 6) Provide a system message to guide the agent to use local SQL tools
        system_message = """
        You are an advanced SQL agent with knowledge of a local SQLite database containing patent data.
        You can retrieve patent information by calling the following tools:
        - 'sql_db_list_tables': to see the available tables
        - 'sql_db_schema': to get schema details
        - 'sql_db_query': to run queries and retrieve data
        - 'schema_doc_rag_tool': to do semantic search over the schema docs
        - 'extended_sql_db_schema': to combine the real schema with additional doc info
        
        Any time a user asks about specifics of a patent, or wants data that might be in the database,
        you should use these tools to query the local database. If the user is asking for patent info
        (abstract, claims, etc.) that might exist in the local DB, do not say 'I cannot access it.'
        Instead, call the appropriate SQL or RAG tool to find it.
        """

        # Create a ReAct agent with memory for multi-turn dialogue.
        self.agent_executor = create_react_agent(
            model=self.llm,
            tools=all_tools,
            prompt=system_message,
            checkpointer=MemorySaver()  # Use a memory checkpointer for thread-level conversation state
        )

    def query_text(self, query: str, thread_id: str = "default") -> str:
        """
        Provides the final interface for user queries.
        Arguments:
            query: The user's question or request.
            thread_id: An identifier for conversation continuity. 
                       If multiple queries share the same thread_id,
                       they share memory context.

        Returns:
            The final agent response as a string.

        Production Considerations:
        - If the conversation is long, you may want a unique thread_id per user session.
        - If you anticipate heavy concurrency, ensure get_openai_callback() usage 
          or other telemetry is efficient and does not block. 
        - Handle potential exceptions around network or token-limit errors gracefully.
        """
        logger = logging.getLogger("text_sql_app")
        logger.info(f"Received query: {query}")

        # Include the thread_id in config so memory can persist across calls
        config = {"configurable": {"thread_id": thread_id}}

        try:
            with get_openai_callback() as cb:
                events = self.agent_executor.stream(
                    {"messages": [("user", query)]},
                    config=config,
                    stream_mode="values"
                )
                final_msg = ""
                for event in events:
                    msg_obj = event["messages"][-1]
                    final_msg = msg_obj.content

                logger.info(
                    f"Token usage: prompt={cb.prompt_tokens}, "
                    f"completion={cb.completion_tokens}, total={cb.total_tokens}, "
                    f"cost={cb.total_cost:.5f} USD"
                )
            return final_msg

        except Exception as e:
            logger.exception("Error during agent execution")
            return f"[ERROR] {str(e)}"