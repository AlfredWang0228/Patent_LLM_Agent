# Patents Query Platform

This project is currently in the **Proof of Concept (PoC)** stage.

## Project Description

This project provides a sophisticated query platform specifically designed to support Ph.D.-level antibody drug researchers. It allows users to efficiently explore and analyze complex patent-related data through two complementary approaches:

- **Text-to-SQL Queries**: Ideal for straightforward data retrieval tasks using natural language inputs, enabling quick access to precise patent information.
- **Multi-Agent Orchestration (under development)**: Designed for handling intricate, research-level inquiries, leveraging coordinated AI agents to collaboratively parse, interpret, and synthesize detailed responses from patent datasets.

By integrating these methods, the platform ensures both ease of use for simple queries and robust capabilities for advanced research exploration.

---

## Project Structure

```
patents/
├── data/
│   ├── SerpAPI/
│   │   └── patent_data.jsonl
│   └── uspto/
│       ├── drug_relevancy_data.csv
│       └── other_patent_data.csv
├── database_design/
│   ├── patent_schema.png
│   ├── db_English_Version.md
│   └── db_Chinese_Version.md
├── serpapi_fetch/
│   ├── config_manager.py
│   ├── fetch_manager.py
│   ├── main.py
│   └── config.yaml
├── database_constraction/
│   ├── abstract_dao.py
│   ├── db_context.py
│   ├── daos.py
│   ├── patent_service.py
│   └── main.py
├── text2sql/
│   ├── managers/
│   │   ├── config_manager.py
│   │   ├── db_manager.py
│   │   ├── vectorstore_manager.py
│   │   ├── tools_manager.py
│   │   └── agent_manager.py
│   ├── main.py
│   ├── config.yaml
│   ├── schema_docs.json
│   └── logs/
│       └── app.log
├── draft_notebooks/
├── _some_search/
├── Makefile
├── environment.yml
├── .env
├── .gitignore
└── ... (other files or folders)
```

---

## Project Status

This project is currently a **Proof of Concept (PoC)**, showcasing initial functionality with basic infrastructure. Further significant enhancements and additional capabilities are planned.

---

## Quickstart

### Using Makefile

```bash
make create-env        # Create Conda environment
make update-env        # Update existing Conda environment
make fetch-serpapi     # Fetch patent data from SerpAPI
make build-db          # Build or update SQLite database
make run-text2sql      # Run text-to-SQL pipeline
make clean             # Clean logs and Python cache
make help              # Show available commands
```

---

## TODO

- [ ] **Multi-Agent Orchestration**
  - [ ] Define agent roles clearly (e.g., data retrieval agent, summarization agent, analytical reasoning agent).
  - [ ] Develop robust agent communication protocols (e.g., using structured JSON messaging).
  - [ ] Implement agent collaboration logic for complex patent data inquiries.
  - [ ] Evaluate and optimize agent interactions for accuracy and speed.

- [ ] **Web Interface Development**
  - [ ] Create an interactive web-based UI to submit queries.
  - [ ] Integrate visualizations for patent data analysis.
  - [ ] Provide an intuitive frontend interface to handle simple and complex queries interactively.

- [ ] **Documentation and Tutorials**
  - [ ] Write comprehensive developer documentation.
  - [ ] Provide user-friendly examples demonstrating query capabilities.
  - [ ] Prepare clear tutorials for onboarding new researchers.

- [ ] **Deployment and Scalability**
  - [ ] Containerize the application using Docker.
  - [ ] Explore options for deploying on cloud platforms (e.g., AWS, Azure).
  - [ ] Plan load testing and optimization strategies for handling larger datasets.

---

## License

© 2024 Yuxiang Wang, Vibrant Wellness LLC. All rights reserved.  
Unauthorized copying, modification, distribution, or use without prior written permission is strictly prohibited. See [LICENSE](LICENSE) for details.

