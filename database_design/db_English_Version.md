# Database Design Description (Using `patent_id` as a Text Primary Key)

## Overall Overview

This database is used to store **patents and related information** obtained from SerpApi. Unlike the traditional approach, this design uses the **`patent_id`** (e.g., `"US20180044418A1"`) as the primary key, rather than an additional auto-increment integer ID. Therefore, all child tables that reference a patent will also use the `patent_id` field, making queries and understanding more intuitive.

1. **Database Engine**: Uses **SQLite** as an example (only minor modifications are needed for MySQL, PostgreSQL, etc.).  
2. **Data Source**: Usually JSON(L) files, each record has a structure like `{"patent_id": ..., "data": {...}}`.  
3. **Core Concepts**:
   - In the main table `patents`, use `patent_id` (TEXT) as the **Primary Key**.
   - Each child table references `patent_id` (TEXT) as a foreign key, maintaining a one-to-many relationship with the main table.
   - If the same `patent_id` is inserted more than once, a unique constraint error will be triggered (or you may use `INSERT OR IGNORE` to handle duplicates as needed).

---

## 1. Main Patent Table: `patents`

Stores the core patent data most frequently queried, using the text primary key `patent_id` as the identifier.

| Field Name             | Type       | Description                                                                       |
|------------------------|-----------|-----------------------------------------------------------------------------------|
| `patent_id`            | TEXT PK   | Text primary key, directly uses the top-level `patent_id` from JSON (e.g., `US20180044418A1`)  |
| `title`                | TEXT      | Patent title                                                                       |
| `type`                 | TEXT      | Patent type (e.g., `"patent"`)                                                    |
| `pdf_link`             | TEXT      | Patent PDF link (e.g., derived from SerpApi’s `pdf`)                              |
| `publication_number`   | TEXT      | Publication number (e.g., `US20180044418A1`)                                      |
| `country`              | TEXT      | Country/region (e.g., `"United States"`)                                          |
| `application_number`   | TEXT      | Application number                                                                |
| `priority_date`        | DATETIME  | Priority date (strings like `"2016-05-23"` converted to `YYYY-MM-DD 00:00:00`)    |
| `filing_date`          | DATETIME  | Filing date                                                                       |
| `publication_date`     | DATETIME  | Publication date                                                                  |
| `prior_art_date`       | DATETIME  | **Prior art date** (if applicable)                                               |
| `family_id`            | TEXT      | Family ID (if provided in JSON)                                                  |
| `abstract`             | TEXT      | Abstract                                                                           |
| `description_link`     | TEXT      | Link to the detailed description                                                 |

---

## 2. Inventors Table: `inventors`

Records the list of inventors for each patent.

| Field Name      | Type                      | Description                                                        |
|-----------------|--------------------------|--------------------------------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment primary key                                        |
| `patent_id`     | TEXT NOT NULL            | Foreign key referencing `patents(patent_id)`                      |
| `inventor_name` | TEXT                     | Inventor name (`data["inventors"][*].name`)                        |
| `link`          | TEXT                     | Link for querying inventor information (optional)                  |
| `serpapi_link`  | TEXT                     | SerpApi link for inventor information (optional)                   |

**Explanation**  
- Corresponds to `data["inventors"]` in the JSON.  
- `patent_id` can be used to identify which specific patent each record belongs to.

---

## 3. Assignees Table: `assignees`

Records the assignees (applicants/patent owners) of each patent.

| Field Name    | Type                      | Description                                               |
|---------------|--------------------------|-----------------------------------------------------------|
| `id`          | INTEGER PK AUTOINCREMENT | Auto-increment primary key                                |
| `patent_id`   | TEXT NOT NULL            | Foreign key, `patents(patent_id)`                         |
| `name`        | TEXT                     | Name of the assignee (e.g., `"Merck Sharp & Dohme LLC"`)  |

---

## 4. Prior Art Keywords Table: `prior_art_keywords`

Stores keywords related to prior art.

| Field Name      | Type                      | Description                                   |
|-----------------|--------------------------|-----------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment primary key                    |
| `patent_id`     | TEXT NOT NULL            | Foreign key                                   |
| `keyword`       | TEXT                     | Keyword (e.g., `"cancer"`, `"tumor"`)         |

---

## 5. Events Table: `events`

Stores patent events (e.g., filing, publication, assignment, etc.).

| Field Name         | Type                      | Description                                                            |
|--------------------|--------------------------|------------------------------------------------------------------------|
| `id`               | INTEGER PK AUTOINCREMENT | Auto-increment primary key                                             |
| `patent_id`        | TEXT NOT NULL            | Foreign key                                                            |
| `event_date`       | DATETIME                 | Event date                                                             |
| `title`            | TEXT                     | Event title (e.g., `"Application filed by..."`)                        |
| `type`             | TEXT                     | Event type (`"filed"`, `"publication"`, `"legal-status"`, etc.)        |
| `critical`         | INTEGER (0/1)            | Indicates whether the event is critical                                |
| `assignee_search`  | TEXT                     | Assignee info if relevant to this event                                |
| `description`      | TEXT                     | If it is an array, it can be concatenated and stored as a single text  |

---

## 6. External Links Table: `external_links`

| Field Name      | Type                      | Description                        |
|-----------------|--------------------------|------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment primary key         |
| `patent_id`     | TEXT NOT NULL            | Foreign key                        |
| `text`          | TEXT                     | Link label (e.g., `"USPTO"`)       |
| `link`          | TEXT                     | URL                                |

---

## 7. Images Table: `images`

| Field Name      | Type                      | Description       |
|-----------------|--------------------------|-------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment PK |
| `patent_id`     | TEXT NOT NULL            | Foreign key       |
| `image_url`     | TEXT                     | Image link        |

---

## 8. Classifications Table: `classifications`

| Field Name      | Type                      | Description                                 |
|-----------------|--------------------------|---------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment PK                           |
| `patent_id`     | TEXT NOT NULL            | Foreign key                                 |
| `code`          | TEXT                     | Classification code (e.g., `"C07K16/2818"`) |
| `description`   | TEXT                     | Description of the classification           |
| `leaf`          | INTEGER (0/1)            | Indicates whether it is a leaf node         |
| `first_code`    | INTEGER (0/1)            | The `first_code` from the JSON             |
| `is_cpc`        | INTEGER (0/1)            | Indicates whether it is CPC                |
| `additional`    | INTEGER (0/1)            | Indicates whether it is an additional classification (`additional`)  |

---

## 9. Claims Table: `claims`

| Field Name      | Type                      | Description                   |
|-----------------|--------------------------|-------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT | Auto-increment PK            |
| `patent_id`     | TEXT NOT NULL            | Foreign key                   |
| `claim_no`      | INTEGER                  | Claim number                  |
| `claim_txt`     | TEXT                     | Text of the claim             |

---

## 10. Applications Claiming Priority Table: `applications_claiming_priority`

| Field Name                | Type                      | Description                                   |
|---------------------------|--------------------------|-----------------------------------------------|
| `id`                      | INTEGER PK AUTOINCREMENT | Auto-increment PK                             |
| `patent_id`               | TEXT NOT NULL            | Foreign key                                   |
| `application_number`      | TEXT                     | Application number                            |
| `priority_date`           | DATETIME                 | Priority date                                 |
| `filing_date`             | DATETIME                 | Filing date                                   |
| `representative_publication` | TEXT                  | Representative publication number             |
| `primary_language`        | TEXT                     | Language (e.g., `"en"`)                       |
| `title`                   | TEXT                     | Title                                         |

---

## 11. Worldwide Applications Table: `worldwide_applications`

| Field Name          | Type                      | Description                                        |
|---------------------|--------------------------|----------------------------------------------------|
| `id`                | INTEGER PK AUTOINCREMENT | Auto-increment PK                                  |
| `patent_id`         | TEXT NOT NULL            | Foreign key                                        |
| `year`              | INTEGER                  | Year (e.g., `2016`)                                |
| `application_number`| TEXT                     | Application number                                 |
| `country_code`      | TEXT                     | Country/region code (e.g., `US`, `WO`)             |
| `document_id`       | TEXT                     | Document ID                                        |
| `filing_date`       | DATETIME                 | Filing date                                        |
| `legal_status`      | TEXT                     | Legal status (e.g., `"Active"`)                    |
| `legal_status_cat`  | TEXT                     | Legal status category (`"active"`, `"not_active"`, etc.) |
| `this_app`          | INTEGER (0/1)            | The `this_app` field from the JSON                |

---

## 12. Patent Citations Table: `patent_citations`

| Field Name            | Type                      | Description                                                |
|-----------------------|--------------------------|------------------------------------------------------------|
| `id`                  | INTEGER PK AUTOINCREMENT | Auto-increment PK                                         |
| `patent_id`           | TEXT NOT NULL            | Foreign key referencing the main table `patents(patent_id)`|
| `is_family_to_family` | INTEGER (0/1)            | Whether it is a family-to-family citation                  |
| `publication_number`  | TEXT                     | Publication number of the cited patent                     |
| `primary_language`    | TEXT                     | Language                                                  |
| `examiner_cited`      | INTEGER (0/1)            | Whether it was cited by an examiner                        |
| `priority_date`       | DATETIME                 | Priority date of the cited patent                          |
| `publication_date`    | DATETIME                 | Publication date of the cited patent                       |
| `assignee_original`   | TEXT                     | Original assignee name of the cited patent                 |
| `title`               | TEXT                     | Title of the cited patent                                  |
| `serpapi_link`        | TEXT                     | Related link                                              |
| `patent_id_ref`       | TEXT                     | ID of the cited patent, such as `patent/WO2015035112A1/en` |

---

## 13. Cited By Table: `cited_by`

| Field Name            | Type                      | Description                                                      |
|-----------------------|--------------------------|------------------------------------------------------------------|
| `id`                  | INTEGER PK AUTOINCREMENT | Auto-increment PK                                               |
| `patent_id`           | TEXT NOT NULL            | Foreign key                                                     |
| `is_family_to_family` | INTEGER (0/1)            | Whether it is family-to-family                                  |
| `publication_number`  | TEXT                     | The publication number of the patent that cites this patent     |
| `primary_language`    | TEXT                     | Main language                                                   |
| `examiner_cited`      | INTEGER (0/1)            | Whether it was cited by an examiner                             |
| `priority_date`       | DATETIME                 | Priority date                                                   |
| `publication_date`    | DATETIME                 | Publication date                                                |
| `assignee_original`   | TEXT                     | Original assignee                                               |
| `title`               | TEXT                     | Title                                                           |
| `serpapi_link`        | TEXT                     | Link                                                            |
| `patent_id_ref`       | TEXT                     | Patent ID of the citing party                                   |

---

## 14. Legal Events Table: `legal_events`

| Field Name        | Type                      | Description                          |
|-------------------|--------------------------|--------------------------------------|
| `id`              | INTEGER PK AUTOINCREMENT | Auto-increment PK                    |
| `patent_id`       | TEXT NOT NULL            | Foreign key                          |
| `date`            | DATETIME                 | Event date                           |
| `code`            | TEXT                     | Event code (e.g., `AS` or `STPP`)    |
| `title`           | TEXT                     | Event title (e.g., `"Assignment"`)   |
| `attributes_json` | TEXT                     | JSON of event attributes (e.g., `attributes`) |

---

## 15. Compounds Table: `concepts`

| Field Name    | Type                      | Description                                                     |
|---------------|--------------------------|-----------------------------------------------------------------|
| `id`          | INTEGER PK AUTOINCREMENT | Auto-increment PK                                              |
| `patent_id`   | TEXT NOT NULL            | Foreign key                                                    |
| `concept_id`  | TEXT                     | `data["concepts"]["match"][*].id` from the JSON                |
| `domain`      | TEXT                     | Domain (e.g., `"Diseases"`)                                    |
| `name`        | TEXT                     | Concept name (e.g., `"Neoplasm"`)                               |
| `similarity`  | REAL                     | Similarity score                                               |
| `sections`    | TEXT                     | If multiple sections, concatenate them with `";"`, e.g. `["title","claims"]` |
| `count`       | INTEGER                  | Occurrence count                                               |
| `inchi_key`   | TEXT                     | InChI Key of the compound                                     |
| `smiles`      | TEXT                     | SMILES string                                                 |

---

## 16. Child Applications Table: `child_applications`

Stores data about continuation/child applications.

| Field Name               | Type                      | Description                                   |
|--------------------------|--------------------------|-----------------------------------------------|
| `id`                     | INTEGER PK AUTOINCREMENT | Auto-increment PK                             |
| `patent_id`              | TEXT NOT NULL            | Foreign key                                   |
| `application_number`     | TEXT                     | Application number                            |
| `relation_type`          | TEXT                     | Relation (e.g., `"Continuation"`)             |
| `representative_publication` | TEXT                 | Representative publication number             |
| `primary_language`       | TEXT                     | Language                                      |
| `priority_date`          | DATETIME                 | Priority date                                 |
| `filing_date`            | DATETIME                 | Filing date                                   |
| `title`                  | TEXT                     | Title                                         |

---

## 17. Parent Applications Table: `parent_applications`

| Field Name               | Type                      | Description                                    |
|--------------------------|--------------------------|------------------------------------------------|
| `id`                     | INTEGER PK AUTOINCREMENT | Auto-increment PK                              |
| `patent_id`              | TEXT NOT NULL            | Foreign key                                    |
| `application_number`     | TEXT                     | Application number                             |
| `relation_type`          | TEXT                     | Relation type (e.g., `"Continuation"`)         |
| `representative_publication` | TEXT                 | Representative publication number              |
| `primary_language`       | TEXT                     | Language                                       |
| `priority_date`          | DATETIME                 | Priority date                                  |
| `filing_date`            | DATETIME                 | Filing date                                    |
| `title`                  | TEXT                     | Title                                          |

---

## 18. Priority Applications Table: `priority_applications`

| Field Name                    | Type                      | Description                                   |
|-------------------------------|--------------------------|-----------------------------------------------|
| `id`                          | INTEGER PK AUTOINCREMENT | Auto-increment PK                             |
| `patent_id`                   | TEXT NOT NULL            | Foreign key                                   |
| `application_number`          | TEXT                     | Application number                            |
| `representative_publication`  | TEXT                     | Representative publication number             |
| `primary_language`            | TEXT                     | Language                                      |
| `priority_date`               | DATETIME                 | Priority date                                 |
| `filing_date`                 | DATETIME                 | Filing date                                   |
| `title`                       | TEXT                     | Title                                         |

---

## 19. Non-Patent Citations Table: `non_patent_citations`

| Field Name        | Type                      | Description                          |
|-------------------|--------------------------|--------------------------------------|
| `id`              | INTEGER PK AUTOINCREMENT | Auto-increment PK                    |
| `patent_id`       | TEXT NOT NULL            | Foreign key                          |
| `citation_title`  | TEXT                     | Title of the cited non-patent        |
| `examiner_cited`  | INTEGER (0/1)            | Whether it was cited by an examiner  |

---

## 20. Similar Documents Table: `similar_documents`

| Field Name           | Type                      | Description                                          |
|----------------------|--------------------------|------------------------------------------------------|
| `id`                 | INTEGER PK AUTOINCREMENT | Auto-increment PK                                   |
| `patent_id`          | TEXT NOT NULL            | Foreign key                                         |
| `is_patent`          | INTEGER (0/1)            | Whether the document is a patent                   |
| `doc_patent_id`      | TEXT                     | If it’s a patent, store its ID (e.g., `patent/US11734097B1/en`) |
| `serpapi_link`       | TEXT                     | SerpApi link                                        |
| `publication_number` | TEXT                     | Publication/publication number                      |
| `primary_language`   | TEXT                     | Language                                            |
| `publication_date`   | DATETIME                 | Publication date                                    |
| `title`              | TEXT                     | Title                                               |

---

## Error Logs Table: `error_logs`

| Field Name       | Type                      | Description                     |
|------------------|--------------------------|---------------------------------|
| `id`             | INTEGER PK AUTOINCREMENT | Auto-increment PK              |
| `error_message`  | TEXT                     | Error description              |
| `stack_trace`    | TEXT                     | Error traceback                |
| `created_at`     | DATETIME                 | Record insertion time          |

---

## Data Flow and Insertion Logic

1. **Read JSONL**:  
   - Each line is of the form `{"patent_id": ..., "data": {...}}`.
2. **Insert into the Main Table**:  
   - Use `patent_id` (TEXT) as the **primary key** when inserting into the `patents` table.
   - If the same `patent_id` is inserted repeatedly, it violates the primary key constraint (you could alternatively use `INSERT OR IGNORE` depending on your needs).
3. **Insert into Child Tables**:  
   - Each child table has `patent_id TEXT NOT NULL` + a foreign key `REFERENCES patents(patent_id)`.
   - Pass `patent_id` to the corresponding insert function — there is **no need** for a numeric ID anymore.
4. **When Querying**:  
   - Simply look up `patent_id` in the child tables to identify the patent’s text-based ID; if you want to retrieve other fields of the patent (e.g., `title`), you can do a `JOIN patents ON child_table.patent_id = patents.patent_id`.

---

## References and Extensions

- If you need **“insert or update”** for the same `patent_id`, you may use `INSERT OR REPLACE` or `UPSERT`.  
- If performance is a concern, you can create an index on `patent_id` (although as a PK, it is automatically indexed).  
- If there is a scenario where the `patent_id` needs to be updated (the ID itself changes), note that you may need to maintain the references carefully.

**If you have any specific questions about this design or its implementation details, feel free to let me know!**