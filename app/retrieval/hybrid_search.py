import os
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from utils.embedding import get_embedding
from utils.reranker import mmr
from utils.ontology import get_topic_for_text
import numpy as np

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

ALLOWED_TABLES = {"sar_index", "act_index"}


def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


from utils.reranker import mmr
from utils.ontology import get_topic_for_text

def hybrid_search(
    table_name: str,
    query_text: str,
    top_k: int = 5,
    vector_weight: float = 0.75,
    text_weight: float = 0.25,
    metadata_filter: dict = None,
    compliance_topic: str = None,
    diversity_lambda: float = None 
):
    """
    Performs hybrid search with controlled soft fallback and a 0.55 confidence threshold.
    """

    if table_name not in ALLOWED_TABLES:
        raise ValueError("Invalid table name")

    MIN_SCORE_THRESHOLD = 0.45
    fetch_count = top_k * 2
    query_embedding = get_embedding(query_text)

    # 1. Prepare Initial Filtered Conditions (Metadata + Topic)
    filter_conditions = []
    filter_values = []
    if metadata_filter:
        for key, value in metadata_filter.items():
            if value:
                filter_conditions.append(f"{key} = %s")
                filter_values.append(value)
    
    if compliance_topic:
        filter_conditions.append("compliance_topic = %s")
        filter_values.append(compliance_topic)

    where_clause = "WHERE " + " AND ".join(filter_conditions) if filter_conditions else ""
    topic_boost_sql = "(CASE WHEN compliance_topic = %s THEN 0.15 ELSE 0 END)" if compliance_topic else "0"

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # --- STAGE 1: FILTERED SEARCH ---
            strict_sql = f"""
            SELECT *,
                ({vector_weight} * (1 - (embedding <=> %s::vector)) +
                 {text_weight} * ts_rank(COALESCE(tsv, ''), plainto_tsquery(%s))) AS score
            FROM {table_name}
            {where_clause}
            ORDER BY score DESC
            LIMIT %s;
            """
            
            strict_params = [query_embedding, query_text] + filter_values + [fetch_count]
            cursor.execute(strict_sql, strict_params)
            results = cursor.fetchall()
            
            if results:
                top_score = results[0]['score']
            else:
                top_score = 0

            # --- STAGE 2: SOFT FALLBACK ONLY IF WEAK OR NO RESULTS ---
            # Triggered if initial results are missing or below threshold, provided filters were used
            if (not results or top_score < MIN_SCORE_THRESHOLD) and filter_conditions:
                print(f"Weak or no results for {table_name}. Triggering soft fallback...")

                fallback_sql = f"""
                SELECT *,
                    ({vector_weight} * (1 - (embedding <=> %s::vector)) +
                     {text_weight} * ts_rank(COALESCE(tsv, ''), plainto_tsquery(%s)) +
                     {topic_boost_sql}) AS score
                FROM {table_name}
                ORDER BY score DESC
                LIMIT %s;
                """

                fallback_params = [query_embedding, query_text]
                if compliance_topic:
                    fallback_params.append(compliance_topic)
                fallback_params.append(fetch_count)

                cursor.execute(fallback_sql, fallback_params)
                results = cursor.fetchall()

    if not results:
        return []

    # 1.5 Keyword Reinforcement Layer (Safe Boost)
    def apply_keyword_boost(results, query_text):
        query = query_text.lower()
        KEYWORD_SECTION_MAP = {
            "fire": ["38"],
            "smoke": ["38"],
            "exit": ["38"],
            "machine": ["21"],
            "press": ["21"],
            "rotating": ["21"],
            "pressure": ["31"],
            "compressor": ["31"],
            "air receiver": ["31"],
            "welding": ["35"],
            "goggles": ["35"],
            "ppe": ["35"]
        }
        BOOST_VALUE = 0.12
        for keyword, sections in KEYWORD_SECTION_MAP.items():
            if keyword in query:
                for r in results:
                    if str(r.get("section_number")) in sections:
                        r["score"] += BOOST_VALUE
        # Re-sort after boosting
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results

    results = apply_keyword_boost(results, query_text)

    # 2. FINAL CONFIDENCE GATE (0.45)
    if results[0]['score'] < MIN_SCORE_THRESHOLD:
        return []

    return results[:top_k]


def search_sar(query_text, industry_type=None, mah_status=None, compliance_topic=None):
    metadata = {}
    if industry_type:
        metadata["industry_type"] = industry_type
    if mah_status:
        metadata["mah_status"] = mah_status

    return hybrid_search(
        table_name="sar_index",
        query_text=query_text,
        top_k=5,
        metadata_filter=metadata,
        compliance_topic=compliance_topic,
        diversity_lambda=0.6 
    )


def search_act(query_text, compliance_topic=None):
    return hybrid_search(
        table_name="act_index",
        query_text=query_text,
        top_k=5,
        compliance_topic=compliance_topic,
        diversity_lambda=0.7 
    )
