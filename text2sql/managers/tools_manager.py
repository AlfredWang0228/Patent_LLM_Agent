"""
managers/tools_manager.py

Defines custom Tools for LangChain, such as:
- SchemaDocRAGTool for vector retrieval
- ExtendedSQLSchemaTool for merging real DB schema + extra docs

Production Context:
-------------------
- These tools extend the default LangChain tool interface (BaseTool),
  enabling an agent to retrieve doc-based schema information or merge
  real DB schema with additional reference docs.
- Ensure 'vectorstore' and 'doc_source' remain up to date if your database
  or schema docs change.
- For large/complex docs, consider caching or chunking for performance.
"""

import json
from typing import Any
from langchain.tools import BaseTool
from langchain_community.vectorstores import Chroma


class SchemaDocRAGTool(BaseTool):
    """
    Tool that uses a vectorstore to do RAG (Retrieval-Augmented Generation)
    for schema documentation queries.

    Usage:
    - The agent calls this tool with a user query about tables or columns,
      and receives top-k relevant schema snippets.
    - 'vectorstore' must be an initialized Chroma instance containing
      embedded schema docs.

    Production Remarks:
    - If schema_docs is large, chunk or partition it to avoid index blowout.
    - Typically invoked when the agent needs details about table structure,
      column definitions, or usage hints beyond simple DB schema statements.
    """
    name: str = "schema_doc_rag_tool"
    description: str = (
        "Do a semantic search over the large schema doc. "
        "Input: any question about tables or columns. Output: relevant snippet(s)."
    )

    vectorstore: Chroma  # Provided at initialization

    def _run(self, query: str) -> str:
        """
        Execute a similarity search in the vectorstore for the top 3 documents
        most relevant to 'query'.

        Returns:
            A string containing snippet(s) of doc text with similarity scores.
        """
        docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=3)
        if not docs_and_scores:
            return "No relevant schema snippet found."

        lines = []
        for doc, score in docs_and_scores:
            lines.append(
                f"score={score:.2f}, table_name={doc.metadata.get('table_name', '')}\nContent:\n{doc.page_content}"
            )
        return "\n\n".join(lines)

    async def _arun(self, query: str) -> str:
        """
        Async version of _run, if tool calls need to be awaited.
        """
        return self._run(query)


class ExtendedSQLSchemaTool(BaseTool):
    """
    Combines real DB schema (from 'sql_db_schema') with additional doc content
    from 'doc_source'. This is helpful when a user wants both technical CREATE TABLE
    details and business-level commentary for a given table name.

    Production Remarks:
    - Ensure 'doc_source' has an entry for each relevant table to provide
      meaningful "business usage info."
    - The 'sql_schema_tool' is typically the original 'sql_db_schema' tool
      from a SQLDatabaseToolkit. If missing or offline, calls will fail.
    """
    name: str = "extended_sql_db_schema"
    description: str = (
        "Call this tool to get the real DB schema + extra doc for a table. "
        "Input is a single table name, output is both CREATE TABLE info plus business usage info."
    )

    sql_schema_tool: BaseTool  # Typically the standard 'sql_db_schema' tool
    doc_source: dict           # Dictionary mapping table_name -> {table_comment, columns}

    def _run(self, table_name: str) -> str:
        """
        1) Use 'sql_schema_tool' to retrieve CREATE TABLE info + sample rows.
        2) Look up doc_source for the same table, merging in business or domain context.
        """
        table_name = table_name.strip()
        # 1) Query the DB schema from the underlying tool
        try:
            db_schema_str = self.sql_schema_tool.run(table_name)
        except Exception as e:
            raise Exception(f"Error calling sql_db_schema: {e}")

        # 2) Merge with doc_source business context
        if table_name in self.doc_source:
            info = self.doc_source[table_name]
            lines = [f"Table Explanation for {table_name}: {info.get('table_comment', '')}"]
            lines.append("Column meanings:")
            for col, desc in info["columns"].items():
                lines.append(f" - {col}: {desc}")
            doc_part = "\n".join(lines)
        else:
            doc_part = f"(No extended doc found for table '{table_name}')."

        # Return a combined string with both DB schema + doc commentary
        combined = f"{db_schema_str}\n\n=== Additional Business Doc ===\n{doc_part}"
        return combined

    async def _arun(self, table_name: str) -> str:
        """
        Async wrapper if the caller requires awaitable usage.
        """
        return self._run(table_name)