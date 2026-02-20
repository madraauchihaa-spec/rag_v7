# Compliance Intelligence System (v3)

An AI-powered RAG system for analyzing compliance audit findings and legal queries related to the Factories Act, 1948.

## Project Structure

- `app/`: Core RAG engine and API implementation.
  - `main.py`: FastAPI application entry point.
  - `rag/`: RAG logic (Finding Mode & Legal Mode).
  - `utils/`: Utility functions (embedding, LLM client, reranker, etc.).
  - `db/`: Database schema and connection logic.
- `act_pipeline/`: Data ingestion pipeline for the Factories Act.
- `sar_pipeline/`: Data ingestion pipeline for Site Audit Reports (SAR).
- `scripts/`: Diagnostic and utility scripts.
- `tests/`: Evaluation and testing suite.

## Setup Instructions

1.  **Environment Variables**:
    Create a `.env` file in the root with the following:
    ```env
    DB_NAME=your_db_name
    DB_USER=your_user
    DB_PASSWORD=your_password
    DB_HOST=your_host
    DB_PORT=5432
    API_KEY=your_llm_api_key
    API_BASE_URL=https://openrouter.ai/api/v1
    LLM_MODEL=google/gemini-pro-1.5
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Initialize Database**:
    ```bash
    python app/init_db.py
    ```

4.  **Run the Server**:
    ```bash
    uvicorn app.main:app --host 127.0.0.1 --port 8005 --reload
    ```

## Testing

Run the compliance evaluation report:
```bash
python tests/compliance_eval.py
```
This will generate a report in the console and output results to `tests/latest_report.txt` (note: latest_report.txt is git-ignored).

## License
MIT (or as per organization policy)
