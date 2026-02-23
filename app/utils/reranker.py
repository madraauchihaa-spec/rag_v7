# app/utils/reranker.py
import numpy as np
from utils.llm_client import generate_response

def llm_rerank(query, sections):
    """
    Optional LLM reranker.
    If LLM returns unexpected output, safely falls back to original order.
    """
    if not sections:
        return []

    prompt = f"""
You are a legal ranking assistant.

User Query:
{query}

Rank these sections from MOST relevant to LEAST relevant.
Return ONLY section numbers separated by commas.

Sections:
"""
    for s in sections:
        prompt += f"\nSection {s.get('section_number')}: {s.get('section_title')}"

    response = (generate_response(prompt) or "").strip()

    ranked_numbers = [n.strip() for n in response.replace("Section", "").split(",") if n.strip()]
    if not ranked_numbers:
        return sections

    try:
        ranked_sections = sorted(
            sections,
            key=lambda x: ranked_numbers.index(str(x.get("section_number")))
            if str(x.get("section_number")) in ranked_numbers else 999
        )
        return ranked_sections
    except Exception:
        return sections


def cosine_similarity(v1, v2):
    v1 = np.array(v1, dtype=float)
    v2 = np.array(v2, dtype=float)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(np.dot(v1, v2) / (norm1 * norm2))


def mmr(query_embedding, doc_embeddings, docs, top_k=5, lambda_param=0.6):
    """
    Max Marginal Relevance (MMR) reranking.
    - lambda_param: 1.0 => relevance only, 0.0 => diversity only
    """
    if not docs:
        return []

    if len(docs) <= top_k:
        return docs

    selected = []
    candidates = list(range(len(docs)))

    query_sims = [cosine_similarity(query_embedding, emb) for emb in doc_embeddings]
    best_initial = int(np.argmax(query_sims))

    selected.append(best_initial)
    candidates.remove(best_initial)

    while len(selected) < min(top_k, len(docs)):
        best_score = None
        best_idx = None

        for cand in candidates:
            sim_q = query_sims[cand]
            sim_selected = max(
                cosine_similarity(doc_embeddings[cand], doc_embeddings[s])
                for s in selected
            )
            score = lambda_param * sim_q - (1 - lambda_param) * sim_selected

            if best_score is None or score > best_score:
                best_score = score
                best_idx = cand

        selected.append(best_idx)
        candidates.remove(best_idx)

    return [docs[i] for i in selected]