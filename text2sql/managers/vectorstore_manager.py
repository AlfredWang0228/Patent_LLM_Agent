"""
managers/vectorstore_manager.py

Builds a Chroma vector store from schema_docs.json for RAG usage.

Explanation:
-----------
This module defines a VectorStoreManager class responsible for:
1. Reading local schema documentation from a JSON file (schema_docs.json).
2. Converting each table's metadata into a Document object.
3. Building a Chroma vector store using OpenAIEmbeddings for semantic search.

In a production setting, this pattern is useful when you want to retrieve
structured knowledge (like table schemas) by semantic similarity queries.
For example, an AI agent could ask, "What columns does the 'patents' table have?"
and the agent can perform a similarity search on your schema docs to retrieve
the relevant snippet without building an extremely large context prompt.
"""

import os
import getpass
import json
from dataclasses import dataclass, field
from typing import Any

from langchain.docstore.document import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings


@dataclass
class VectorStoreManager:
    """
    Creates a Chroma vector store from a schema_docs.json file.

    Production-level considerations:
    - Error handling around missing or invalid JSON ensures robust behavior.
    - If the JSON is extremely large, you may need streaming or chunking 
      to keep memory usage feasible.
    - For security, OPENAI_API_KEY is retrieved from environment or interactive prompt
      rather than hard-coded in any config.
    """
    schema_docs_path: str
    collection_name: str
    vectorstore: Chroma = field(init=False)

    def __post_init__(self):
        """
        Builds the vectorstore upon initialization.
        This ensures that as soon as VectorStoreManager is constructed, 
        the vectorstore attribute is ready to use.
        """
        self.vectorstore = self._build_vectorstore()

    def _build_vectorstore(self) -> Chroma:
        """
        Reads schema_docs_path JSON, then builds a Chroma vectorstore using OpenAIEmbeddings.

        Returns:
            A Chroma instance populated with embeddings for each table's metadata.

        Production-level notes:
        - If performance is critical, consider caching the Chroma index on disk.
        - If schema_docs.json is updated frequently, you may need an update mechanism.
        - If you have large amounts of text, consider chunking or partial loading.
        """
        # Confirm the presence of schema_docs.json
        if not os.path.exists(self.schema_docs_path):
            raise FileNotFoundError(f"schema_docs.json not found at {self.schema_docs_path}")

        # Load the schema documentation as a Python dictionary
        with open(self.schema_docs_path, "r", encoding="utf-8") as f:
            schema_docs = json.load(f)

        # Build a list of Document objects, each representing a table's schema info
        doc_list = []
        for table_name, info in schema_docs.items():
            table_comment = info.get("table_comment", "")
            cols = info.get("columns", {})
            col_texts = []
            for col, desc in cols.items():
                col_texts.append(f"{col}: {desc}")
            col_section = "\n".join(col_texts)

            # Create a text block that includes table name, comment, and columns
            text_chunk = (
                f"Table: {table_name}\n"
                f"Comment: {table_comment}\n"
                f"Columns:\n{col_section}"
            )
            # Convert the combined text into a Document for embedding
            doc_list.append(
                Document(page_content=text_chunk, metadata={"table_name": table_name})
            )

        # Ensure we have an OpenAI API key. If not set, prompt the user for it.
        _api_key = os.environ.get("OPENAI_API_KEY")
        if not _api_key:
            _api_key = getpass.getpass("Enter your OPENAI_API_KEY: ")
            os.environ["OPENAI_API_KEY"] = _api_key

        # Create the embeddings object. In production, you might customize 
        # model_name or other parameters in OpenAIEmbeddings.
        embeddings = OpenAIEmbeddings(openai_api_key=_api_key)

        # Build a Chroma instance from the documents
        # 'collection_name' logically groups these embeddings for semantic queries.
        return Chroma.from_documents(
            documents=doc_list,
            embedding=embeddings,
            collection_name=self.collection_name
        )