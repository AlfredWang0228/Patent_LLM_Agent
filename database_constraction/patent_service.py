"""
patent_service.py

Purpose:
--------
Provides a central PatentService class that orchestrates:
1) Database setup (table creation) using multiple DAO objects.
2) Reading and parsing JSONL input, then inserting data into relevant tables.

Why This Matters (Production-Level Notes):
-----------------------------------------
- Combining all DAO interactions in one service class simplifies higher-level
  flow control (setup & insertion).
- This service logs errors both to a dedicated table (error_logs) and to Python’s
  standard logging system, ensuring issues can be debugged persistently.
- JSON lines are parsed incrementally, so large files can be handled line-by-line.
  If concurrency or multi-processing is desired, you could adapt parse_and_insert_from_jsonl
  into batches or workers.
- Each table’s insert logic is in the respective DAO, promoting single-responsibility.

"""

import os
import json
import traceback
import logging
from typing import Dict, Any, Generator, Tuple, Optional
from dataclasses import dataclass, field

from pathlib import Path  # for path handling

from .db_context import db_connection
from .daos import (
    PatentsDAO,
    InventorsDAO,
    AssigneesDAO,
    PriorArtKeywordsDAO,
    EventsDAO,
    ExternalLinksDAO,
    ImagesDAO,
    ClassificationsDAO,
    ClaimsDAO,
    ApplicationsClaimingPriorityDAO,
    WorldwideApplicationsDAO,
    PatentCitationsDAO,
    CitedByDAO,
    LegalEventsDAO,
    ConceptsDAO,
    ChildApplicationsDAO,
    ParentApplicationsDAO,
    PriorityApplicationsDAO,
    NonPatentCitationsDAO,
    SimilarDocumentsDAO,
    ErrorLogsDAO
)

logger = logging.getLogger(__name__)

def read_jsonl_records(file_path: Path) -> Generator[Tuple[int, Optional[Dict[str, Any]]], None, None]:
    """
    Generator that yields (line_num, record_dict) for each line in the JSONL file.
    If a line is empty or fails JSON parse, yields (line_num, None).

    Production Considerations:
    --------------------------
    - If the file is extremely large, line-by-line streaming helps memory usage.
    - If advanced error handling is needed (e.g., partial re-try), you can store
      line_num for reprocessing later.
    - Ensure your JSON lines are valid. If there's a risk of multi-line JSON, 
      consider a robust parser or check for potential line breaks in your data.
    """
    with file_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_num, json.loads(line)
            except json.JSONDecodeError:
                yield line_num, None

@dataclass
class PatentService:
    """
    Manages table creation and JSONL-based insertion for all DAO objects.

    Main Responsibilities:
    -----------------------
    1) Setting up each DAO (one DAO per table).
    2) Creating all tables in a single step (setup_database).
    3) Parsing JSONL (parse_and_insert_from_jsonl), line by line:
       - Insert the main 'patent' record
       - Insert all child records (inventors, events, citations, etc.)
       - Log or store errors if insertion fails

    Production-Level Notes:
    -----------------------
    - 'INSERT OR IGNORE' is common in the DAOs to avoid duplicates, 
      but you can choose a different strategy if required.
    - For high-volume insertion, consider bulk inserts or disabling some constraints 
      then re-enabling them after insertion for performance. 
    - If JSON schema evolves, ensure the DAOs handle missing/extra fields gracefully.
    """

    db_path: str

    # DAO instances for each table
    patents_dao: PatentsDAO = field(default_factory=PatentsDAO)
    inventors_dao: InventorsDAO = field(default_factory=InventorsDAO)
    assignees_dao: AssigneesDAO = field(default_factory=AssigneesDAO)
    prior_art_keywords_dao: PriorArtKeywordsDAO = field(default_factory=PriorArtKeywordsDAO)
    events_dao: EventsDAO = field(default_factory=EventsDAO)
    external_links_dao: ExternalLinksDAO = field(default_factory=ExternalLinksDAO)
    images_dao: ImagesDAO = field(default_factory=ImagesDAO)
    classifications_dao: ClassificationsDAO = field(default_factory=ClassificationsDAO)
    claims_dao: ClaimsDAO = field(default_factory=ClaimsDAO)
    acp_dao: ApplicationsClaimingPriorityDAO = field(default_factory=ApplicationsClaimingPriorityDAO)
    wwa_dao: WorldwideApplicationsDAO = field(default_factory=WorldwideApplicationsDAO)
    patent_citations_dao: PatentCitationsDAO = field(default_factory=PatentCitationsDAO)
    cited_by_dao: CitedByDAO = field(default_factory=CitedByDAO)
    legal_events_dao: LegalEventsDAO = field(default_factory=LegalEventsDAO)
    concepts_dao: ConceptsDAO = field(default_factory=ConceptsDAO)
    child_apps_dao: ChildApplicationsDAO = field(default_factory=ChildApplicationsDAO)
    parent_apps_dao: ParentApplicationsDAO = field(default_factory=ParentApplicationsDAO)
    priority_apps_dao: PriorityApplicationsDAO = field(default_factory=PriorityApplicationsDAO)
    npc_dao: NonPatentCitationsDAO = field(default_factory=NonPatentCitationsDAO)
    similar_docs_dao: SimilarDocumentsDAO = field(default_factory=SimilarDocumentsDAO)
    error_logs_dao: ErrorLogsDAO = field(default_factory=ErrorLogsDAO)

    # Collect all DAOs here for one-pass table creation
    all_daos: list = field(init=False)

    def __post_init__(self):
        """
        After creation, compile all DAO objects into one list
        for easier iteration (e.g., table setup).
        """
        self.all_daos = [
            self.patents_dao,
            self.inventors_dao,
            self.assignees_dao,
            self.prior_art_keywords_dao,
            self.events_dao,
            self.external_links_dao,
            self.images_dao,
            self.classifications_dao,
            self.claims_dao,
            self.acp_dao,
            self.wwa_dao,
            self.patent_citations_dao,
            self.cited_by_dao,
            self.legal_events_dao,
            self.concepts_dao,
            self.child_apps_dao,
            self.parent_apps_dao,
            self.priority_apps_dao,
            self.npc_dao,
            self.similar_docs_dao,
            self.error_logs_dao
        ]
        logger.debug("PatentService initialized with all DAOs: %d daos total.", len(self.all_daos))

    def __repr__(self) -> str:
        """
        Custom string representation for debug/logging clarity.
        Example: PatentService(db_path='data/patent.db', total_daos=21)
        """
        return f"PatentService(db_path='{self.db_path}', total_daos={len(self.all_daos)})"

    def setup_database(self) -> None:
        """
        Create all tables in a single transaction. If tables already exist, 
        'CREATE TABLE IF NOT EXISTS' ensures no error is raised.

        Production-Level Considerations:
        --------------------------------
        - In a large-scale environment, you might prefer explicit migrations 
          or a versioned schema upgrade process.
        - Ensure foreign key constraints are turned ON at connection-level
          (db_context does this).
        """
        logger.info("Starting database setup for all tables.")
        with db_connection(self.db_path) as conn:
            for dao in self.all_daos:
                dao.create_table(conn)
        logger.info("All tables created or ensured to exist successfully.")

    def parse_and_insert_from_jsonl(self, jsonl_path: str) -> None:
        """
        Reads a JSONL file line by line, inserting each record's data 
        across the relevant DAO tables.

        Workflow:
        ---------
        1) read_jsonl_records -> yield line_num and record (dict or None)
        2) If record is None, log decode error
        3) Otherwise:
           - Insert into 'patents' (main)
           - Insert into child tables (inventors, citations, etc.)
           - On error, log to error_logs and the main logger

        Parameters
        ----------
        jsonl_path : str
            Path to the JSONL file containing records from SerpAPI.

        Production Warnings:
        --------------------
        - If a record references huge data, consider chunking or partial updates.
        - 'INSERT OR IGNORE' is used in many DAOs; if that policy changes, 
          you may need to detect conflicts or handle updates differently.
        - If line-based errors occur frequently, consider a more robust logging strategy
          with partial re-ingestion logic.
        """
        jsonl_path_obj = Path(jsonl_path)
        if not jsonl_path_obj.is_file():
            logger.error(f"File not found: {jsonl_path}")
            return

        logger.info(f"Starting to parse JSONL file: {jsonl_path}")
        for line_num, record in read_jsonl_records(jsonl_path_obj):
            if record is None:
                # JSON decode error
                logger.error(f"JSON decode error at line {line_num}")
                with db_connection(self.db_path) as conn:
                    stack = traceback.format_exc()
                    self.error_logs_dao.insert(conn, f"JSON decode error at line {line_num}", stack)
                continue

            try:
                with db_connection(self.db_path) as conn:
                    # Insert main patent record
                    patent_id_str = self.patents_dao.insert(conn, record)

                    # Insert sub-entities
                    self.inventors_dao.insert(conn, patent_id_str, record)
                    self.assignees_dao.insert(conn, patent_id_str, record)
                    self.prior_art_keywords_dao.insert(conn, patent_id_str, record)
                    self.events_dao.insert(conn, patent_id_str, record)
                    self.external_links_dao.insert(conn, patent_id_str, record)
                    self.images_dao.insert(conn, patent_id_str, record)
                    self.classifications_dao.insert(conn, patent_id_str, record)
                    self.claims_dao.insert(conn, patent_id_str, record)
                    self.acp_dao.insert(conn, patent_id_str, record)
                    self.wwa_dao.insert(conn, patent_id_str, record)
                    self.patent_citations_dao.insert(conn, patent_id_str, record)
                    self.cited_by_dao.insert(conn, patent_id_str, record)
                    self.legal_events_dao.insert(conn, patent_id_str, record)
                    self.concepts_dao.insert(conn, patent_id_str, record)
                    self.child_apps_dao.insert(conn, patent_id_str, record)
                    self.parent_apps_dao.insert(conn, patent_id_str, record)
                    self.priority_apps_dao.insert(conn, patent_id_str, record)
                    self.npc_dao.insert(conn, patent_id_str, record)
                    self.similar_docs_dao.insert(conn, patent_id_str, record)

            except Exception as e:
                # Log the exception to both standard logger and DB error_logs
                logger.exception(f"Error inserting record at line {line_num}")
                stack = traceback.format_exc()
                with db_connection(self.db_path) as conn:
                    err_msg = f"[Line {line_num}] {str(e)}"
                    self.error_logs_dao.insert(conn, err_msg, stack)

        logger.info("Finished parsing and inserting data from JSONL.")