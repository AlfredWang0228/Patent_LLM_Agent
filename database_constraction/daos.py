"""
daos.py

Purpose:
--------
Houses DAO (Data Access Object) classes for each table in the SQLite database.
Each class implements:
  1) create_table(conn): Create the table schema if it does not already exist.
  2) insert(...): Insert records into the table, reading from a SerpAPI "data" structure.

Why This Matters:
-----------------
- This module centralizes database logic for each table, improving maintainability.
- By subclassing AbstractTableDAO, we enforce a standard interface across all DAOs.

Usage Example:
--------------
from db_context import db_connection
from daos import PatentsDAO, InventorsDAO, ...

with db_connection("data/patent.db") as conn:
    dao_patents = PatentsDAO()
    dao_patents.create_table(conn)
    # Insert a patent record:
    record = {...}  # structure from SerpAPI
    patent_id_str = dao_patents.insert(conn, record)

Production-Level Considerations:
-------------------------------
- Each DAO focuses on a single table schema, with custom logic to parse the record dict.
- 'INSERT OR IGNORE' is used in some DAOs to prevent duplicates, but may need adjusting 
  depending on your deduplication strategy.
- The data structure from SerpAPI can be large and nested; ensure you handle missing/extra fields.
- Consider adding more CRUD operations (update/delete) if needed.
- For error logging, some DAO references "ErrorLogsDAO" or similar pattern to store error info 
  if the rest of the system lacks a robust error-capturing strategy.
"""

import sqlite3
import datetime
import json
from typing import Optional, Dict, Any, List

from .abstract_dao import AbstractTableDAO

def _parse_date_to_utc(date_str: Optional[str]) -> Optional[str]:
    """
    Convert a date string in YYYY-MM-DD format into 'YYYY-MM-DD 00:00:00' UTC format.

    Parameters
    ----------
    date_str : str or None
        The date string to parse, e.g. '2023-05-10'. If None or invalid, returns None.

    Returns
    -------
    Optional[str]
        A standardized date string or None if input was empty/invalid.

    Production Note:
    ---------------
    - This approach zeroes out the time component to '00:00:00'. For advanced 
      time-zone handling, you may want to store the offset or pass actual times.
    """
    if not date_str:
        return None
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d 00:00:00")
    except ValueError:
        return None


class PatentsDAO(AbstractTableDAO):
    """
    Manages the 'patents' table schema and insert logic.

    Table Schema:
    ------------
    patents(
        patent_id TEXT PRIMARY KEY,
        title TEXT,
        type TEXT,
        pdf_link TEXT,
        publication_number TEXT,
        country TEXT,
        application_number TEXT,
        priority_date DATETIME,
        filing_date DATETIME,
        publication_date DATETIME,
        prior_art_date DATETIME,
        family_id TEXT,
        abstract TEXT,
        description_link TEXT
    )
    """

    def create_table(self, conn: sqlite3.Connection) -> None:
        """
        Creates the patents table if it does not exist.
        """
        conn.execute("""
        CREATE TABLE IF NOT EXISTS patents (
            patent_id TEXT PRIMARY KEY,
            title TEXT,
            type TEXT,
            pdf_link TEXT,
            publication_number TEXT,
            country TEXT,
            application_number TEXT,
            priority_date DATETIME,
            filing_date DATETIME,
            publication_date DATETIME,
            prior_art_date DATETIME,
            family_id TEXT,
            abstract TEXT,
            description_link TEXT
        );
        """)

    def insert(self, conn: sqlite3.Connection, record: Dict[str, Any]) -> str:
        """
        Inserts a patent record into 'patents' table.

        Parameters
        ----------
        conn : sqlite3.Connection
            Active DB connection.
        record : dict
            A dictionary with keys 'patent_id', 'data' (the latter 
            holding patent info from SerpAPI).

        Returns
        -------
        str
            The 'patent_id' that was inserted or attempted to insert.

        Production Note:
        ---------------
        - INSERT OR IGNORE ensures that if the same 'patent_id' is re-inserted, 
          it will be ignored.
        """
        patent_id_str = record.get("patent_id", "")
        data_sub = record.get("data", {})

        title = data_sub.get("title")
        patent_type = data_sub.get("type")
        pdf_link = data_sub.get("pdf")
        publication_number = data_sub.get("publication_number")
        country = data_sub.get("country")
        application_number = data_sub.get("application_number")

        priority_date = _parse_date_to_utc(data_sub.get("priority_date"))
        filing_date = _parse_date_to_utc(data_sub.get("filing_date"))
        publication_date = _parse_date_to_utc(data_sub.get("publication_date"))
        prior_art_date = _parse_date_to_utc(data_sub.get("prior_art_date"))

        family_id = data_sub.get("family_id")
        abstract_ = data_sub.get("abstract")
        description_link = data_sub.get("description_link")

        sql = """
        INSERT OR IGNORE INTO patents (
            patent_id, title, type, pdf_link, publication_number, country,
            application_number, priority_date, filing_date, publication_date,
            prior_art_date, family_id, abstract, description_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn.execute(sql, (
            patent_id_str,
            title,
            patent_type,
            pdf_link,
            publication_number,
            country,
            application_number,
            priority_date,
            filing_date,
            publication_date,
            prior_art_date,
            family_id,
            abstract_,
            description_link
        ))
        return patent_id_str


class InventorsDAO(AbstractTableDAO):
    """
    Manages the 'inventors' table.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        """
        Creates 'inventors' table with a foreign key referencing 'patents'.
        """
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            inventor_name TEXT,
            link TEXT,
            serpapi_link TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        """
        Inserts multiple inventor records from 'inventors' array in the SerpAPI data.
        """
        data_sub = record.get("data", {})
        inventors_list = data_sub.get("inventors", [])
        sql = """
        INSERT INTO inventors (patent_id, inventor_name, link, serpapi_link)
        VALUES (?, ?, ?, ?)
        """
        for inv in inventors_list:
            name = inv.get("name")
            link = inv.get("link")
            serpapi = inv.get("serpapi_link")
            conn.execute(sql, (patent_id_str, name, link, serpapi))


class AssigneesDAO(AbstractTableDAO):
    """
    Manages the 'assignees' table.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS assignees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            name TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        assignees = data_sub.get("assignees", [])
        sql = "INSERT INTO assignees (patent_id, name) VALUES (?, ?)"
        for a in assignees:
            if isinstance(a, dict):
                name = a.get("name")
            else:
                name = a
            if name:
                conn.execute(sql, (patent_id_str, name))


class PriorArtKeywordsDAO(AbstractTableDAO):
    """
    Stores prior art keywords associated with a patent.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS prior_art_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            keyword TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        kw_list = data_sub.get("prior_art_keywords", [])
        sql = "INSERT INTO prior_art_keywords (patent_id, keyword) VALUES (?, ?)"
        for kw in kw_list:
            conn.execute(sql, (patent_id_str, kw))


class EventsDAO(AbstractTableDAO):
    """
    Manages 'events' table, storing event metadata from SerpAPI data.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            event_date DATETIME,
            title TEXT,
            type TEXT,
            critical INTEGER,
            assignee_search TEXT,
            description TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        events_list = data_sub.get("events", [])
        sql = """
        INSERT INTO events (
            patent_id, event_date, title, type, critical, assignee_search, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for ev in events_list:
            date_ = _parse_date_to_utc(ev.get("date"))
            etitle = ev.get("title")
            etype = ev.get("type")
            ecrit = 1 if ev.get("critical") else 0
            assignee_search = ev.get("assignee_search")

            desc_data = ev.get("description")
            if isinstance(desc_data, list):
                desc_str = "; ".join(desc_data)
            elif isinstance(desc_data, str):
                desc_str = desc_data
            else:
                desc_str = None

            conn.execute(sql, (
                patent_id_str, date_, etitle, etype, ecrit, assignee_search, desc_str
            ))


class ExternalLinksDAO(AbstractTableDAO):
    """
    Stores external links related to a patent (text + link).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS external_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            text TEXT,
            link TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        elist = data_sub.get("external_links", [])
        sql = "INSERT INTO external_links (patent_id, text, link) VALUES (?, ?, ?)"
        for e in elist:
            txt = e.get("text")
            lnk = e.get("link")
            conn.execute(sql, (patent_id_str, txt, lnk))


class ImagesDAO(AbstractTableDAO):
    """
    Stores image URLs associated with the patent.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            image_url TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        ilist = data_sub.get("images", [])
        sql = "INSERT INTO images (patent_id, image_url) VALUES (?, ?)"
        for url in ilist:
            conn.execute(sql, (patent_id_str, url))


class ClassificationsDAO(AbstractTableDAO):
    """
    Stores classification info for patents, possibly CPC or other codes.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            code TEXT,
            description TEXT,
            leaf INTEGER,
            first_code INTEGER,
            is_cpc INTEGER,
            additional INTEGER,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        c_list = data_sub.get("classifications", [])
        sql = """
        INSERT INTO classifications (
            patent_id, code, description, leaf, first_code, is_cpc, additional
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for c in c_list:
            code = c.get("code")
            desc = c.get("description")
            leaf = 1 if c.get("leaf") else 0
            first_code = 1 if c.get("first_code") else 0
            is_cpc = 1 if c.get("is_cpc") else 0
            additional = 1 if c.get("additional") else 0
            conn.execute(sql, (patent_id_str, code, desc, leaf, first_code, is_cpc, additional))


class ClaimsDAO(AbstractTableDAO):
    """
    Stores textual claims from the patent.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            claim_no INTEGER,
            claim_txt TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        c_list = data_sub.get("claims", [])
        sql = "INSERT INTO claims (patent_id, claim_no, claim_txt) VALUES (?, ?, ?)"
        for i, claim_txt in enumerate(c_list, start=1):
            conn.execute(sql, (patent_id_str, i, claim_txt))


class ApplicationsClaimingPriorityDAO(AbstractTableDAO):
    """
    Manages 'applications_claiming_priority' table, referencing future continuations or expansions.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS applications_claiming_priority (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            application_number TEXT,
            priority_date DATETIME,
            filing_date DATETIME,
            representative_publication TEXT,
            primary_language TEXT,
            title TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        acp_list = data_sub.get("applications_claiming_priority", [])
        sql = """
        INSERT INTO applications_claiming_priority (
            patent_id, application_number, priority_date, filing_date,
            representative_publication, primary_language, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for acp in acp_list:
            app_no = acp.get("application_number")
            pd = _parse_date_to_utc(acp.get("priority_date"))
            fd = _parse_date_to_utc(acp.get("filing_date"))
            repub = acp.get("representative_publication")
            lang = acp.get("primary_language")
            ttl = acp.get("title")
            conn.execute(sql, (patent_id_str, app_no, pd, fd, repub, lang, ttl))


class WorldwideApplicationsDAO(AbstractTableDAO):
    """
    Manages 'worldwide_applications', which can hold multi-year app data by region or year.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS worldwide_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            year INTEGER,
            application_number TEXT,
            country_code TEXT,
            document_id TEXT,
            filing_date DATETIME,
            legal_status TEXT,
            legal_status_cat TEXT,
            this_app INTEGER,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        wwa = data_sub.get("worldwide_applications", {})
        sql = """
        INSERT INTO worldwide_applications (
            patent_id, year, application_number, country_code, document_id,
            filing_date, legal_status, legal_status_cat, this_app
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for year_str, wlist in wwa.items():
            try:
                year_int = int(year_str)
            except ValueError:
                year_int = None
            if not isinstance(wlist, list):
                continue
            for wapp in wlist:
                app_no = wapp.get("application_number")
                ccode = wapp.get("country_code")
                doc_id = wapp.get("document_id")
                fd = _parse_date_to_utc(wapp.get("filing_date"))
                ls = wapp.get("legal_status")
                lsc = wapp.get("legal_status_cat")
                tapp = 1 if wapp.get("this_app") else 0
                conn.execute(sql, (
                    patent_id_str, year_int, app_no, ccode, doc_id,
                    fd, ls, lsc, tapp
                ))


class PatentCitationsDAO(AbstractTableDAO):
    """
    Manages 'patent_citations' table, storing references to other patents cited.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS patent_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            is_family_to_family INTEGER,
            publication_number TEXT,
            primary_language TEXT,
            examiner_cited INTEGER,
            priority_date DATETIME,
            publication_date DATETIME,
            assignee_original TEXT,
            title TEXT,
            serpapi_link TEXT,
            patent_id_ref TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        """
        For each 'original' or 'family_to_family' list, insert references to other patents.
        """
        data_sub = record.get("data", {})
        pc = data_sub.get("patent_citations", {})
        sql = """
        INSERT INTO patent_citations (
            patent_id, is_family_to_family, publication_number, primary_language, examiner_cited,
            priority_date, publication_date, assignee_original, title, serpapi_link, patent_id_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for key in ["original", "family_to_family"]:
            cit_list = pc.get(key, [])
            is_ftf = 1 if key == "family_to_family" else 0
            for c in cit_list:
                pub_no = c.get("publication_number")
                plang = c.get("primary_language")
                exam_cited = 1 if c.get("examiner_cited") else 0
                pdate = _parse_date_to_utc(c.get("priority_date"))
                pub_date = _parse_date_to_utc(c.get("publication_date"))
                assign_orig = c.get("assignee_original")
                ttl = c.get("title")
                link = c.get("serpapi_link")
                pid_ref = c.get("patent_id")
                conn.execute(sql, (
                    patent_id_str, is_ftf, pub_no, plang, exam_cited,
                    pdate, pub_date, assign_orig, ttl, link, pid_ref
                ))


class CitedByDAO(AbstractTableDAO):
    """
    Stores patents that cite the current patent (the inverse of patent_citations).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cited_by (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            is_family_to_family INTEGER,
            publication_number TEXT,
            primary_language TEXT,
            examiner_cited INTEGER,
            priority_date DATETIME,
            publication_date DATETIME,
            assignee_original TEXT,
            title TEXT,
            serpapi_link TEXT,
            patent_id_ref TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        cb = data_sub.get("cited_by", {})
        sql = """
        INSERT INTO cited_by (
            patent_id, is_family_to_family, publication_number, primary_language, examiner_cited,
            priority_date, publication_date, assignee_original, title, serpapi_link, patent_id_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for key in ["original", "family_to_family"]:
            cit_list = cb.get(key, [])
            is_ftf = 1 if key == "family_to_family" else 0
            for c in cit_list:
                pub_no = c.get("publication_number")
                plang = c.get("primary_language")
                exam_cited = 1 if c.get("examiner_cited") else 0
                pdate = _parse_date_to_utc(c.get("priority_date"))
                pub_date = _parse_date_to_utc(c.get("publication_date"))
                assign_orig = c.get("assignee_original")
                ttl = c.get("title")
                link = c.get("serpapi_link")
                pid_ref = c.get("patent_id")
                conn.execute(sql, (
                    patent_id_str, is_ftf, pub_no, plang, exam_cited,
                    pdate, pub_date, assign_orig, ttl, link, pid_ref
                ))


class LegalEventsDAO(AbstractTableDAO):
    """
    Stores legal event data (like assignments, status changes).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS legal_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            date DATETIME,
            code TEXT,
            title TEXT,
            attributes_json TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        le_list = data_sub.get("legal_events", [])
        sql = """
        INSERT INTO legal_events (
            patent_id, date, code, title, attributes_json
        ) VALUES (?, ?, ?, ?, ?)
        """
        for le in le_list:
            date_ = _parse_date_to_utc(le.get("date"))
            code = le.get("code")
            ttl = le.get("title")
            attrs = le.get("attributes", [])
            attrs_str = json.dumps(attrs, ensure_ascii=False) if attrs else None

            conn.execute(sql, (patent_id_str, date_, code, ttl, attrs_str))


class ConceptsDAO(AbstractTableDAO):
    """
    Stores entity or concept matches (chemical, domain-specific, etc.).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            concept_id TEXT,
            domain TEXT,
            name TEXT,
            similarity REAL,
            sections TEXT,
            count INTEGER,
            inchi_key TEXT,
            smiles TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        c_dict = data_sub.get("concepts", {})
        match_list = c_dict.get("match", [])

        if isinstance(match_list, dict):
            match_list = [match_list]

        sql = """
        INSERT INTO concepts (
            patent_id, concept_id, domain, name, similarity, sections,
            count, inchi_key, smiles
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for m in match_list:
            cid = m.get("id")
            domain = m.get("domain")
            name_ = m.get("name")
            sim = m.get("similarity")
            sections_list = m.get("sections", [])
            sections_str = ";".join(sections_list) if isinstance(sections_list, list) else None
            cnt = m.get("count")
            ikey = m.get("inchi_key")
            sm = m.get("smiles")

            conn.execute(sql, (
                patent_id_str, cid, domain, name_, sim, sections_str,
                cnt, ikey, sm
            ))


class ChildApplicationsDAO(AbstractTableDAO):
    """
    Child applications that reference this patent (continuations).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS child_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            application_number TEXT,
            relation_type TEXT,
            representative_publication TEXT,
            primary_language TEXT,
            priority_date DATETIME,
            filing_date DATETIME,
            title TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        child_apps = data_sub.get("child_applications", [])
        sql = """
        INSERT INTO child_applications (
            patent_id, application_number, relation_type,
            representative_publication, primary_language,
            priority_date, filing_date, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for ch in child_apps:
            app_no = ch.get("application_number")
            relation = ch.get("relation_type")
            repub = ch.get("representative_publication")
            lang = ch.get("primary_language")
            pd = _parse_date_to_utc(ch.get("priority_date"))
            fd = _parse_date_to_utc(ch.get("filing_date"))
            tl = ch.get("title")
            conn.execute(sql, (patent_id_str, app_no, relation, repub, lang, pd, fd, tl))


class ParentApplicationsDAO(AbstractTableDAO):
    """
    Parent applications from which this patent claims priority or is derived.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS parent_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            application_number TEXT,
            relation_type TEXT,
            representative_publication TEXT,
            primary_language TEXT,
            priority_date DATETIME,
            filing_date DATETIME,
            title TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        parent_apps = data_sub.get("parent_applications", [])
        sql = """
        INSERT INTO parent_applications (
            patent_id, application_number, relation_type,
            representative_publication, primary_language,
            priority_date, filing_date, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for pa in parent_apps:
            app_no = pa.get("application_number")
            relation = pa.get("relation_type")
            repub = pa.get("representative_publication")
            lang = pa.get("primary_language")
            pd = _parse_date_to_utc(pa.get("priority_date"))
            fd = _parse_date_to_utc(pa.get("filing_date"))
            ttl = pa.get("title")
            conn.execute(sql, (patent_id_str, app_no, relation, repub, lang, pd, fd, ttl))


class PriorityApplicationsDAO(AbstractTableDAO):
    """
    Priority applications which established the earliest priority date for the patent.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS priority_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            application_number TEXT,
            representative_publication TEXT,
            primary_language TEXT,
            priority_date DATETIME,
            filing_date DATETIME,
            title TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        pa_list = data_sub.get("priority_applications", [])
        sql = """
        INSERT INTO priority_applications (
            patent_id, application_number, representative_publication, primary_language,
            priority_date, filing_date, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for pa in pa_list:
            app_no = pa.get("application_number")
            repub = pa.get("representative_publication")
            lang = pa.get("primary_language")
            pd = _parse_date_to_utc(pa.get("priority_date"))
            fd = _parse_date_to_utc(pa.get("filing_date"))
            ttl = pa.get("title")
            conn.execute(sql, (patent_id_str, app_no, repub, lang, pd, fd, ttl))


class NonPatentCitationsDAO(AbstractTableDAO):
    """
    Stores references to non-patent literature cited in the application.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS non_patent_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            citation_title TEXT,
            examiner_cited INTEGER,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        npc_list = data_sub.get("non_patent_citations", [])
        sql = """
        INSERT INTO non_patent_citations (
            patent_id, citation_title, examiner_cited
        ) VALUES (?, ?, ?)
        """
        for c in npc_list:
            ttl = c.get("title")
            exam_cited = 1 if c.get("examiner_cited") else 0
            conn.execute(sql, (patent_id_str, ttl, exam_cited))


class SimilarDocumentsDAO(AbstractTableDAO):
    """
    Similar documents or references found by the search engine (not strictly citations).
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS similar_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id TEXT NOT NULL,
            is_patent INTEGER,
            doc_patent_id TEXT,
            serpapi_link TEXT,
            publication_number TEXT,
            primary_language TEXT,
            publication_date DATETIME,
            title TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents (patent_id) ON DELETE CASCADE
        );
        """)

    def insert(self, conn: sqlite3.Connection, patent_id_str: str, record: Dict[str, Any]) -> None:
        data_sub = record.get("data", {})
        sd_list = data_sub.get("similar_documents", [])
        sql = """
        INSERT INTO similar_documents (
            patent_id, is_patent, doc_patent_id, serpapi_link,
            publication_number, primary_language, publication_date, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for sd in sd_list:
            is_pt = 1 if sd.get("is_patent") else 0
            doc_pid = sd.get("patent_id")
            link = sd.get("serpapi_link")
            pub_no = sd.get("publication_number")
            plang = sd.get("primary_language")
            pub_date = _parse_date_to_utc(sd.get("publication_date"))
            ttl = sd.get("title")
            conn.execute(sql, (
                patent_id_str, is_pt, doc_pid, link, pub_no, plang, pub_date, ttl
            ))


class ErrorLogsDAO(AbstractTableDAO):
    """
    Stores error messages and stack traces for troubleshooting database operations.
    """
    def create_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_message TEXT,
            stack_trace TEXT,
            created_at DATETIME
        );
        """)

    def insert(self, conn: sqlite3.Connection, error_message: str, stack: str) -> None:
        """
        Logs an error message and stack trace with a UTC timestamp.
        """
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sql = """
        INSERT INTO error_logs (error_message, stack_trace, created_at)
        VALUES (?, ?, ?)
        """
        conn.execute(sql, (error_message, stack, now_str))