from utils.llm_client import generate_response

def llm_rerank(query, sections):
    if not sections:
        return []
        
    prompt = f"""
You are a legal ranking assistant.

User Query:
{query}

Below are retrieved legal sections.

Rank them from MOST legally relevant to LEAST relevant.
Only return section numbers in ranked order, separated by commas.

Sections:
"""

    for s in sections:
        prompt += f"\nSection {s['section_number']}: {s['section_title']}"

    response = generate_response(prompt)
    
    # Extract ranked numbers and clean them
    ranked_numbers = [n.strip() for n in response.replace("Section", "").split(",") if n.strip()]
    
    # Sort original sections based on the ranked numbers
    ranked_sections = sorted(
        sections,
        key=lambda x: ranked_numbers.index(str(x['section_number']))
        if str(x['section_number']) in ranked_numbers else 999
    )
    
    return ranked_sections

def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return np.dot(v1, v2) / (norm1 * norm2)

def mmr(query_embedding, doc_embeddings, docs, top_k=5, lambda_param=0.5):
    """
    Max Marginal Relevance reranking.
    :param query_embedding: List or array of the query embedding.
    :param doc_embeddings: List of embeddings for each document in candidate set.
    :param docs: List of document records (dicts) corresponding to embeddings.
    :param top_k: Number of documents to return.
    :param lambda_param: Diversity factor (1 => similarity only, 0 => diversity only).
    """
    if not docs:
        return []
    
    selected_indices = []
    candidate_indices = list(range(len(docs)))
    
    # Pre-calculate similarities to query
    query_sims = [cosine_similarity(query_embedding, emb) for emb in doc_embeddings]
    
    # First selection is simply the best match
    best_initial = np.argmax(query_sims)
    selected_indices.append(best_initial)
    candidate_indices.remove(best_initial)
    
    while len(selected_indices) < min(top_k, len(docs)):
        mmr_scores = []
        for cand_idx in candidate_indices:
            # Similarity to query
            sim_q = query_sims[cand_idx]
            
            # Max similarity to already selected documents
            sim_selected = max([cosine_similarity(doc_embeddings[cand_idx], doc_embeddings[sel_idx]) 
                               for sel_idx in selected_indices])
            
            # MMR Score
            score = lambda_param * sim_q - (1 - lambda_param) * sim_selected
            mmr_scores.append((score, cand_idx))
        
        # Select candidate with highest MMR score
        next_selected = max(mmr_scores, key=lambda x: x[0])[1]
        selected_indices.append(next_selected)
        candidate_indices.remove(next_selected)
        
    return [docs[i] for i in selected_indices]
