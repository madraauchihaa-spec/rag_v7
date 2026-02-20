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
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    metadata_filter: dict = None,
    compliance_topic: str = None,
    diversity_lambda: float = None # If set, triggers MMR
):
    """
    Performs hybrid search (vector + full-text) with topical prioritization and optional MMR.
    """

    if table_name not in ALLOWED_TABLES:
        raise ValueError("Invalid table name")

    query_embedding = get_embedding(query_text)

    filter_conditions = []
    filter_values = []

    if metadata_filter:
        for key, value in metadata_filter.items():
            if value:
                filter_conditions.append(f"{key} = %s")
                filter_values.append(value)

    where_clause = ""
    if filter_conditions:
        where_clause = "WHERE " + " AND ".join(filter_conditions)

    # If MMR is requested, fetch more candidates to allow for diversity selection
    fetch_count = top_k * 4 if diversity_lambda is not None else top_k * 2

    # Score calculation with TOPIC BOOST
    # We give a 0.5 bonus if the compliance_topic matches
    topic_boost_sql = "(CASE WHEN compliance_topic = %s THEN 0.5 ELSE 0 END)" if compliance_topic else "0"
    
    sql = f"""
    SELECT *,
        ({vector_weight} * (1 - (embedding <=> %s::vector)) +
         {text_weight} * ts_rank(COALESCE(tsv, ''), plainto_tsquery(%s)) +
         {topic_boost_sql}) AS score
    FROM {table_name}
    {where_clause}
    ORDER BY score DESC
    LIMIT %s;
    """

    params = [query_embedding, query_text]
    if compliance_topic:
        params.append(compliance_topic)
    params += filter_values + [fetch_count]

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 1. Try with filters + topic boost
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # 2. Fallback: If no results and we had filters, try without metadata filters but keep topic boost
            if not results and filter_conditions:
                print(f"No results for {table_name} with filters {metadata_filter}. Retrying without metadata filters...")
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

    # Apply MMR if diversity_lambda is provided
    if diversity_lambda is not None and len(results) > top_k:
        def parse_embedding(emb):
            if isinstance(emb, str):
                return np.fromstring(emb.strip('[]'), sep=',')
            return np.array(emb)
            
        doc_embeddings = [parse_embedding(r['embedding']) for r in results]
        results = mmr(query_embedding, doc_embeddings, results, top_k=top_k, lambda_param=diversity_lambda)

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
