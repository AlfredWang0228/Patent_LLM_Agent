"""
serpapi_fetch/fetch_manager.py

Overview:
---------
This module defines the SerpAPIFetchManager class, responsible for:
1) Reading and merging multiple CSV files from a specified folder (input_folder).
2) Optionally filtering or limiting rows based on user-defined config:
   - Searching for a condition in specified columns,
   - Sorting by a certain column (descending),
   - Taking the top N rows.
   - Stripping spaces in a designated column (e.g., 'Document ID').
3) Checking existing JSONL data to skip patents already fetched (especially if 'pdf' is found).
4) Fetching patent details from SerpAPI (via serpapi library) with automatic retries on errors.
5) Appending new records to the output JSONL file.

Usage in the System:
--------------------
- An instance of SerpAPIFetchManager is created in serpapi_fetch/main.py, 
  pulling in configuration from config_manager.py.
- The main script calls fetch_patents_in_bulk(), which orchestrates the entire pipeline 
  from reading CSV -> filtering -> fetching -> writing JSONL.

Key Functions:
-------------
- load_patent_ids() : returns a list of 'Document ID' values after reading all CSVs 
  and applying filter/sort/limit logic.
- load_existing_records() : loads the existing JSONL to identify which patent_ids 
  are already fetched (and possibly skip them).
- fetch_patents_in_bulk() : the main entry point to run the entire process.

Production-Level Considerations:
-------------------------------
- Logging: errors are recorded in serpapi_fetch_errors.log at ERROR level.
- If you plan to handle extremely large CSV files, consider chunked reads.
- If the volume of patents or the concurrency is high, coordinate with 
  SerpAPI rate limits or schedule the fetch.
- For advanced usage, you may want to store partial results in a DB or handle 
  more sophisticated deduplication or PDF checks.
"""

import os
import glob
import json
import time
import logging
import pandas as pd
from typing import List
from dataclasses import dataclass, field
from tqdm.auto import tqdm
from serpapi import GoogleSearch


@dataclass
class SerpAPIFetchManager:
    """
    Manages the SerpAPI fetching process. 
    Each instance is created with the relevant configuration fields.

    Attributes:
    -----------
    input_folder : str
        Directory path containing CSV files to merge.
    output_jsonl : str
        Path to JSONL file where new fetch results are appended.
    filter_condition : str
        Substring used to filter rows in certain columns (case-insensitive).
    filter_columns : List[str]
        Columns to apply filter_condition to (OR logic across them).
    sort_by : str
        Column name to sort on descending. If empty or not found, skip sorting.
    limit : int
        If >0, limit the final rows after sorting/filtering.
    remove_spaces_column : str
        If non-empty, remove all spaces in this column's string values.
    max_retries : int
        Number of retry attempts if SerpAPI call fails.
    sleep_seconds : int
        Delay (in seconds) between retries.
    skip_if_has_pdf : bool
        If True, skip re-fetch if existing data in JSONL includes a 'pdf' key.
    logger : logging.Logger
        Logger instance to record errors into serpapi_fetch_errors.log.
    api_key : str (initialized post-init)
        SERPAPI_KEY from environment, validated in __post_init__.

    Methods:
    --------
    fetch_patents_in_bulk():
        The main flow to read CSV(s), filter, check existing JSONL, fetch each 
        patent from SerpAPI, and append to JSONL.
    """
    input_folder: str
    output_jsonl: str

    filter_condition: str
    filter_columns: List[str]
    sort_by: str
    limit: int
    remove_spaces_column: str

    max_retries: int
    sleep_seconds: int
    skip_if_has_pdf: bool

    logger: logging.Logger = field(default_factory=logging.getLogger)
    api_key: str = field(init=False)

    def __post_init__(self):
        """
        Ensures SERPAPI_KEY is present in the environment and 
        sets up an ERROR-level logger to record fetch errors 
        to 'serpapi_fetch_errors.log'.
        """
        self.logger.setLevel(logging.ERROR)
        err_handler = logging.FileHandler("serpapi_fetch_errors.log", mode="a", encoding="utf-8")
        err_handler.setLevel(logging.ERROR)
        self.logger.addHandler(err_handler)

        key = os.environ.get("SERPAPI_KEY")
        if not key:
            raise ValueError("No SERPAPI_KEY found in environment.")
        self.api_key = key

    def _read_and_concat_csvs(self) -> pd.DataFrame:
        """
        Gathers all CSV files in self.input_folder, concatenates them into a single DataFrame.

        Raises
        ------
        NotADirectoryError
            If input_folder is not a valid directory.
        FileNotFoundError
            If no CSV files are found in that folder.
        ValueError
            If we somehow read zero CSV data.
        """
        if not os.path.isdir(self.input_folder):
            raise NotADirectoryError(f"input_folder '{self.input_folder}' is not a valid directory.")

        csv_files = glob.glob(os.path.join(self.input_folder, "*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in '{self.input_folder}'")

        dfs = []
        for fpath in csv_files:
            df = pd.read_csv(fpath)
            dfs.append(df)

        if not dfs:
            raise ValueError("No CSV data read.")

        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df

    def _filter_and_limit_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies optional filtering, sorting, and limiting on the merged DataFrame.

        Steps:
        ------
        1) If filter_condition is set, keep rows where filter_columns have 
           case-insensitive substring matches.
        2) If sort_by is set and valid, sort descending.
        3) If limit > 0, take the top 'limit' rows.
        4) If remove_spaces_column is set, remove spaces in that column.

        Returns
        -------
        pd.DataFrame
            The processed DataFrame after applying all steps.
        """
        # (1) Filter
        if self.filter_condition and self.filter_columns:
            mask = False
            for col in self.filter_columns:
                if col in df.columns:
                    col_mask = df[col].str.contains(self.filter_condition, case=False, na=False)
                    mask = mask | col_mask
            df = df[mask]

        # (2) Sort descending if requested
        if self.sort_by and self.sort_by in df.columns:
            df = df.sort_values(by=self.sort_by, ascending=False)

        # (3) Limit
        if self.limit > 0:
            df = df.head(self.limit)

        # (4) Remove spaces
        if self.remove_spaces_column and self.remove_spaces_column in df.columns:
            df[self.remove_spaces_column] = (
                df[self.remove_spaces_column].str.replace(' ', '', regex=False)
            )

        return df

    def load_patent_ids(self) -> List[str]:
        """
        Reads & merges CSV files, then filters, sorts, limits, and returns a list of patent IDs.

        Assumes the final column for patent IDs is "Document ID". If that column
        doesn't exist after filtering, raises a ValueError.

        Returns
        -------
        List[str]
            A list of patent ID strings to be fetched from SerpAPI.
        """
        combined_df = self._read_and_concat_csvs()
        processed_df = self._filter_and_limit_data(combined_df)

        if "Document ID" not in processed_df.columns:
            raise ValueError("No 'Document ID' column found in the final DataFrame.")

        return processed_df["Document ID"].tolist()

    def load_existing_records(self) -> dict:
        """
        Loads existing JSONL data to identify which patent IDs we've already fetched.

        Returns
        -------
        dict
            A dictionary mapping patent_id -> existing data (dict).
            Used to skip re-fetching if skip_if_has_pdf is True and 'pdf' is in data.

        Production Note:
        ---------------
        - For extremely large JSONL, consider a more scalable approach
          (e.g., a DB or partial load).
        """
        records = {}
        if os.path.exists(self.output_jsonl):
            with open(self.output_jsonl, "r", encoding="utf-8") as f_in:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        pid = record.get("patent_id", "")
                        data = record.get("data", {})
                        records[pid] = data
                    except Exception as e:
                        self.logger.error(f"Failed to parse line: {e}")
        return records

    def _fetch_patent_details(self, raw_id: str) -> dict:
        """
        Calls SerpAPI for one patent, returning a dictionary of results.

        Parameters
        ----------
        raw_id : str
            The local patent ID (e.g., "US11734097B1") 
            which we transform into 'patent/US11734097B1/en'.

        Raises
        ------
        Exception
            If the SerpAPI call fails (network error, rate limit, etc.).

        Returns
        -------
        dict
            The parsed JSON response from SerpAPI. 
            Typically includes fields like 'title', 'pdf', 'claims', etc.
        """
        full_id = f"patent/{raw_id}/en"
        params = {
            "engine": "google_patents_details",
            "patent_id": full_id,
            "api_key": self.api_key
        }
        search = GoogleSearch(params)
        result = search.get_dict()
        return result

    def fetch_patents_in_bulk(self):
        """
        Main logic to orchestrate the entire fetch flow:

        1) Gather patent IDs from CSV(s) via load_patent_ids().
        2) Load existing records from output_jsonl (if any).
        3) For each patent_id:
           - If skip_if_has_pdf=True and 'pdf' is present in existing record, skip fetch.
           - Otherwise, attempt up to max_retries calls to _fetch_patent_details().
           - Append each successful result to output_jsonl in JSON Lines format.
        4) Provide progress updates via tqdm, 
           logging error details to serpapi_fetch_errors.log on failure.
        """
        patent_list = self.load_patent_ids()
        num_patents = len(patent_list)
        existing = self.load_existing_records()

        start_time = time.time()
        total_success = 0
        total_fail = 0
        cumulative_time = 0.0

        mode = "a"  # append to JSONL
        with open(self.output_jsonl, mode=mode, encoding="utf-8") as f_out:
            for i, raw_id in enumerate(tqdm(patent_list, total=num_patents, desc="Fetching Patent Data")):
                iter_start = time.time()

                # If we already have data, skip if skip_if_has_pdf and 'pdf' in existing record
                if raw_id in existing:
                    if self.skip_if_has_pdf and "pdf" in existing[raw_id]:
                        tqdm.write(f"Skipping {raw_id} (found 'pdf' in data).")
                        continue

                # Attempt up to max_retries
                success = False
                for attempt in range(self.max_retries):
                    try:
                        response = self._fetch_patent_details(raw_id)
                        record = {
                            "patent_id": raw_id,
                            "data": response
                        }
                        f_out.write(json.dumps(record) + "\n")
                        success = True
                        total_success += 1
                        break
                    except Exception as e:
                        self.logger.error(f"Error fetching {raw_id}, attempt {attempt+1}/{self.max_retries}: {e}")
                        time.sleep(self.sleep_seconds)

                if not success:
                    total_fail += 1

                # Timing updates
                iter_time = time.time() - iter_start
                cumulative_time += iter_time
                avg_time = cumulative_time / (i + 1)
                tqdm.write(f"Patent {raw_id} took {iter_time:.2f}s, avg {avg_time:.2f}s")

        total_time = time.time() - start_time
        print(f"\nDone! Patents: {num_patents}, success={total_success}, fail={total_fail}")
        if num_patents:
            print(f"Avg time/patent: {cumulative_time / num_patents:.2f}s")
        print(f"Total time: {total_time:.2f}s")