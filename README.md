# Compliance RAG Engine v7 (Advanced)

An AI-powered Compliance Intelligence System (V7) featuring Query Decomposition, Multi-Query Hybrid Retrieval, and Context Expansion. Designed to analyze Legal Documents (Acts/Rules), Technical Standards (IS), and Safety Audit Reports (SAR).

---

## 🚀 Key Features (V7 Architecture)
- **Query Decomposition** — Breaks complex intents into targeted sub-queries for broader coverage.
- **Multi-Query Hybrid Retrieval** — Cross-references multiple search vectors and merged rankings.
- **Authority Ranking** — Intelligently boosts mandatory clauses and core Act sections.
- **Context Expansion** — Automatically fetches surrounding standard clauses for comprehensive technical context.
- **Legal Mode V7** — Advanced analysis with LLM-backed query optimization and verification.

---

## 🏗️ Project Structure
```text
RAG_v7/
├── app/                   # FastAPI Application Core
│   ├── ingestion/         # Ingestion logic (Act, SAR, Standards)
│   │   ├── act_ingest.py
│   │   ├── sar_ingest.py
│   │   └── standard_ingest.py
│   ├── rag/               # Advanced RAG logic
│   │   ├── query_processor.py # NEW: Decomposition logic
│   │   ├── legal_mode.py      # V7 Flow
│   │   └── finding_mode.py
│   ├── retrieval/         # Retrieval backend
│   │   ├── hybrid_search.py   # Base hybrid FTS + Vector
│   │   └── advanced_retrieval.py # NEW: Multi-query & Authority Rank
│   ├── utils/             # LLM & Embedding utilities
│   │   ├── embedding.py
│   │   ├── llm_client.py
│   │   └── reranker.py
│   └── main.py            # API entry point
├── act_data/              # Factories Act Dataset
├── sar_data/              # Audit Reports Dataset
├── standards_data/        # Technical Standards (IS) Dataset
├── frontend/              # Web Interface
├── tests/                 # Evaluation suite
├── init_db.py             # Schema setup
├── baseline_results.json  # Phase 0 Baseline data
└── requirements.txt
```

---

## 🛠️ Setup Instructions (Ubuntu)

### 1. Prerequisites
- Ubuntu 20.04+ / 22.04+
- Python 3.10+
- PostgreSQL 14+ with `pgvector` extension

#### Install PostgreSQL & pgvector
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib libpq-dev
# Install pgvector from source
sudo apt install -y postgresql-server-dev-all build-essential git
git clone https://github.com/pgvector/pgvector.git /tmp/pgvector
cd /tmp/pgvector && make && sudo make install
```

#### Enable pgvector in PostgreSQL
```bash
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

### 2. Python Environment Setup
```bash
# Create and activate a virtual environment (or use conda)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Environment Configuration
```bash
# Copy template and fill in your credentials
cp .env.example .env
nano .env   # or: vim .env
```

Key variables to set in `.env`:
| Variable | Description |
|---|---|
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host (default: `localhost`) |
| `DB_PORT` | Database port (default: `5432`) |
| `XAI_API_KEY` | xAI Grok API key |
| `LLM_MODEL` | LLM model name (e.g. `grok-4-fast-reasoning`) |
| `EMBEDDING_MODEL` | HuggingFace embedding model |
| `API_BASE_URL` | Full xAI chat completions endpoint URL |

---

### 4. Database Initialization
```bash
python init_db.py
```

---

### 5. Data Ingestion
```bash
# Ingest Legal Acts
python app/ingestion/act_ingest.py

# Ingest Safety Audit Reports
python app/ingestion/sar_ingest.py
```

---

### 6. Run the Application
```bash
python app/main.py
```
The API and UI will be available at: **http://127.0.0.1:8000**

To run with auto-reload (development):
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🧪 Testing & Evaluation
```bash
python tests/compliance_eval.py
```

---

## 🐧 Ubuntu & Hardware Notes
- **CPU-Only Execution**: Forced to CPU in `app/utils/embedding.py` to leverage the 16GB RAM and avoid VRAM overflow on GPUs (especially 2GB versions).
- Use `python3` instead of `python` if your system doesn't alias it.
- Ensure your conda/venv is activated before running any commands.
- PostgreSQL service management:
  ```bash
  sudo systemctl start postgresql
  sudo systemctl enable postgresql
  sudo systemctl status postgresql
  ```
- If port 8000 is already in use:
  ```bash
  lsof -i :8000          # find the process
  kill -9 <PID>          # kill it
  ```
