# Compliance RAG Engine v5

An AI-powered Compliance Intelligence System designed to analyze legal documents (Acts/Rules) and Safety Audit Reports (SAR). The system provides structured insights into legal applicability, compliance gaps, and risk exposure.

## 🚀 Features
- **Legal Mode**: Precise retrieval and analysis of legal sections from ingested Acts.
- **Finding Mode**: Mapping factory observations to relevant legal clauses and recommendations.
- **Hybrid Search**: Combines Dense Vector Search (pgvector) with Full-Text Search (FTS).
- **Automated Ingestion**: Support for complex nested JSON structures from legal and audit sources.
- **Modern UI**: Streamlined interface for compliance exploration.

---

## 🏗️ Project Structure
```text
RAG/
├── app/                  # FastAPI Application Core
│   ├── ingestion/        # Ingestion logic (Act & SAR)
│   ├── rag/              # RAG processing & prompt engineering
│   ├── retrieval/        # Hybrid search implementation
│   ├── utils/            # Embedding, Ontology, and Governance helpers
│   └── main.py           # API Entry point & browser launcher
├── frontend/             # Single Page Application
├── act_data/             # Dataset for Legal Acts
├── sar_data/             # Dataset for Safety Audit Reports
├── scripts/              # Verification & Diagnostic scripts
├── tests/                # System test suite
├── init_db.py            # Database schema initialization
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variable template
```

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.10+
- PostgreSQL with `pgvector` extension installed.

### 2. Environment Setup
Clone the repository and create a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Configuration
1. Create a `.env` file based on `.env.example`.
2. Initialize the database schema:
```powershell
python init_db.py
```

### 4. Data Ingestion
Ingest the datasets into the vector database:
```powershell
# Ingest Legal Acts
python app/ingestion/act_ingest.py

# Ingest Safety Audit Reports
python app/ingestion/sar_ingest.py
```

### 5. Verification (Optional)
Run the test suite to evaluate system performance:
```powershell
python tests/compliance_eval.py
```

---

## 🏃 Running the Application
To start the backend and automatically launch the UI:
```powershell
python app/main.py
```
The UI will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 🧪 Testing
The system includes a specialized evaluation script for compliance accuracy:
```powershell
python tests/compliance_eval.py
```
