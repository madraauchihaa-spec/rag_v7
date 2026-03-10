# app/retrieval/advanced_retrieval.py
from retrieval.hybrid_search import hybrid_search, get_db_connection
from psycopg2.extras import RealDictCursor
from utils.reranker import mmr
from utils.embedding import get_embedding

def multi_query_hybrid_search(table_name, sub_queries, compliance_topic=None, top_k=5):
    """
    Executes multiple searches and merges results using reciprocal rank fusion or top-score selection.
    """
    all_results = []
    seen_ids = set()
    
    # Query weights (original is usually first and most important)
    for i, q in enumerate(sub_queries):
        # We fetch more results per sub-query to have a better pool for MMR
        results = hybrid_search(
            table_name=table_name,
            query_text=q,
            top_k=7,
            compliance_topic=compliance_topic,
            diversity_lambda=None # Disable internal MMR to do it once at the end
        )
        for r in results:
            if r["id"] not in seen_ids:
                all_results.append(r)
                seen_ids.add(r["id"])
    
    # Sort by score descending (as a baseline)
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply global MMR if needed
    if len(all_results) > top_k:
        # Use embedding of first (main) query for global MMR
        main_query_emb = get_embedding(sub_queries[0])
        doc_embeddings = [r["embedding"] for r in all_results]
        all_results = mmr(
            query_embedding=main_query_emb,
            doc_embeddings=doc_embeddings,
            docs=all_results,
            top_k=top_k,
            lambda_param=0.5
        )
    
    return all_results


def authority_rank(results):
    """
    Boosts results from preferred authorities (e.g. specialized acts over general rules).
    """
    # Example logic: boost 'Section' hits over 'Rule' hits if applicable,
    # or boost specific central laws over state amendments if desired.
    for r in results:
        # Simple boost for content length or keyword matches like 'shall' or 'mandatory'
        if "shall" in r.get("content", "").lower():
            r["score"] += 0.05
        if r.get("section_number") and r.get("section_number").isdigit():
            # Real sections usually have integer numbers
            r["score"] += 0.02
            
    return sorted(results, key=lambda x: x["score"], reverse=True)
