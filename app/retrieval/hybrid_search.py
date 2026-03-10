# app/retrieval/hybrid_search.py
import os
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

from pgvector.psycopg2 import register_vector

from utils.embedding import get_embedding
from utils.reranker import mmr

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

ALLOWED_TABLES = {"sar_index", "act_index", "standard_index"}

SOURCE_WEIGHTS = {
    "act_index": 1.0,
    "standard_index": 0.85,
    "sar_index": 0.6
}


def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    register_vector(conn)
    return conn


def _is_valid_filter_value(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    return s not in ["", "null", "none", "n/a"]


def hybrid_search(
    table_name: str,
    query_text: str,
    top_k: int = 5,
    vector_weight: float = 0.80,
    text_weight: float = 0.20,
    metadata_filter: dict = None,
    compliance_topic: str = None,
    diversity_lambda: float = 0.65
):
    """
    Test-ready Hybrid Search:
    - Stage 1: metadata-filtered search (if filters exist)
    - Stage 2: fallback global search if Stage 1 weak
    - Topic is a BOOST (not hard filter)
    - MMR reduces duplicates
    """
    if table_name not in ALLOWED_TABLES:
        raise ValueError("Invalid table name")

    MIN_SCORE_THRESHOLD = 0.40 # Adjusted for weighted scaling
    fetch_count = top_k * 3

    query_embedding = get_embedding(query_text)

    # ---- Build metadata WHERE clause (only real values) ----
    filter_conditions = []
    filter_values = []
    if metadata_filter:
        for key, value in metadata_filter.items():
            if _is_valid_filter_value(value):
                filter_conditions.append(f"{key} = %s")
                filter_values.append(value)

    where_clause = "WHERE " + " AND ".join(filter_conditions) if filter_conditions else ""

    # ---- Topic boost ----
    topic_boost_sql = " + (CASE WHEN compliance_topic = %s THEN 0.10 ELSE 0 END)" if compliance_topic else ""

    def run_query(use_filters: bool):
        wc = where_clause if use_filters else ""
        sql = f"""
        SELECT *,
            ({vector_weight} * (1 - (embedding <=> %s::vector)) +
             {text_weight} * ts_rank(COALESCE(tsv, ''), plainto_tsquery(%s))
             {topic_boost_sql}) AS score
        FROM {table_name}
        {wc}
        ORDER BY score DESC
        LIMIT %s;
        """

        params = [query_embedding, query_text]
        if compliance_topic:
            params.append(compliance_topic)
        if use_filters:
            params += filter_values
        params.append(fetch_count)

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                # Convert RealDictRow to plain dict for serialization safety
                clean_rows = []
                # Authority multiplier
                auth_multiplier = SOURCE_WEIGHTS.get(table_name, 1.0)
                
                for r in rows:
                    d = dict(r)
                    d["score"] = d["score"] * auth_multiplier
                    
                    for k, v in d.items():
                        # Convert UUIDs and other non-JSON types to strings
                        if hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
                            d[k] = str(v)
                        # Ensure embedding is a list
                        if k == "embedding" and v is not None:
                            if isinstance(v, str):
                                try:
                                    s = v.strip("[]")
                                    d[k] = [float(x) for x in s.split(",") if x.strip()]
                                except Exception:
                                    d[k] = []
                            elif hasattr(v, 'tolist'): # Handle numpy or pgvector arrays
                                d[k] = v.tolist()
                            elif not isinstance(v, list):
                                d[k] = list(v)
                        # Handle tsvector or other special types
                        if k == "tsv":
                            d[k] = str(v)
                    clean_rows.append(d)
                return clean_rows
        finally:
            conn.close()

    # ---- Stage 1: filtered search ----
    results = run_query(use_filters=bool(filter_conditions))

    top_score = results[0]["score"] if results else 0

    # ---- Stage 2: fallback if weak and filters were used ----
    if (not results or top_score < MIN_SCORE_THRESHOLD) and filter_conditions:
        results = run_query(use_filters=False)
        top_score = results[0]["score"] if results else 0

    if not results:
        return []

    # Confidence gate
    if results[0]["score"] < MIN_SCORE_THRESHOLD:
        return []

    # MMR
    if diversity_lambda is not None and len(results) > top_k:
        # Crucial: Ensure embeddings are lists/arrays for the reranker
        # With register_vector, results["embedding"] should already be a numpy array or list
        doc_embeddings = [r["embedding"] for r in results]
        results = mmr(
            query_embedding=query_embedding,
            doc_embeddings=doc_embeddings,
            docs=results,
            top_k=top_k,
            lambda_param=diversity_lambda
        )
    else:
        results = results[:top_k]

    return results


def search_sar(query_text, industry_type=None, mah_status=None, compliance_topic=None):
    metadata = {}
    if industry_type:
        metadata["industry_type"] = industry_type
    if mah_status:
        metadata["mah_status"] = mah_status

    r = hybrid_search(
        table_name="sar_index",
        query_text=query_text,
        top_k=5, # Assuming top_k was meant to be 5 here, as it was not defined in the function signature
        metadata_filter=metadata,
        compliance_topic=compliance_topic,
        diversity_lambda=0.60
    )
    return r


def search_act(query_text, compliance_topic=None):
    return hybrid_search(
        table_name="act_index",
        query_text=query_text,
        top_k=5,
        compliance_topic=compliance_topic,
        diversity_lambda=0.70
    )


def search_standard(query_text, compliance_topic=None):
    return hybrid_search(
        table_name="standard_index",
        query_text=query_text,
        top_k=5,
        compliance_topic=compliance_topic,
        diversity_lambda=0.70
    )