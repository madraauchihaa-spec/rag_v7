# app/rag/legal_mode.py
import re
from retrieval.hybrid_search import search_standard, get_db_connection
from retrieval.context_expander import expand_standard_context
from retrieval.advanced_retrieval import multi_query_hybrid_search, authority_rank
from utils.query_decomposer import decompose_query
from utils.llm_client import generate_response
from utils.ontology import get_topic_for_text
from utils.governance import filter_general_sections
from utils.logger import log_rag_flow
from utils.citation_validator import validate_citations
from utils.text_cleaner import truncate_text

def aggregate_standard_sections(results):
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in results:
        key = (
            r.get("standard_code"),
            r.get("year"),
            r.get("section_number")
        )
        grouped[key].append(r)

    aggregated = []
    for key, clauses in grouped.items():
        first = clauses[0]
        aggregated.append({
            "standard_code": first.get("standard_code"),
            "year": first.get("year"),
            "section_number": first.get("section_number"),
            "section_title": first.get("parent_clause_title"),
            "clauses": [c.get("clause_number") for c in clauses],
            "content": "\n".join(c.get("content", "") for c in clauses)
        })
    return aggregated



def build_legal_prompt(query, site_profile, act_results, std_results):
    act_text = "\n\n".join(
        [
            f"ACT SECTION {r.get('section_number')} - {r.get('section_title')}\n{r.get('content')}"
            for r in act_results
        ]
    )
    
    std_text = "\n\n".join(
        [
            f"STANDARD: {r.get('standard_code')}:{r.get('year')} - Section {r.get('section_number')} ({r.get('section_title')})\n"
            f"Clauses: {', '.join(r.get('clauses', []))}\n"
            f"{r.get('content')}"
            for r in std_results
        ]
    )
    
    act_text = truncate_text(act_text, 1500)
    std_text = truncate_text(std_text, 1500)

    prompt = f"""
SYSTEM ROLE: You are Navi.AI, a highly specialized Compliance Intelligent Assistant for Safety and Legal Professionals.

STEP 1: QUERY COMPREHENSION
First, deep-dive into the user's query. Understand the technical and regulatory context.

STEP 2: CITATION RULES
1) Only cite provisions present in LEGAL DATA or STANDARDS DATA.
2) Do not create new sections or clauses.
3) If no provision applies, write "Not Applicable".

STEP 3: RETRIEVAL ANALYSIS
Compare the query against the provided LEGAL DATA and STANDARDS DATA.
ONLY cite a provision if it is an 80-90% MATCH to the requirement. If the data is only tangentially related or too general, you MUST state "Not Applicable" for that section.

STEP 4: STRUCTURED RESPONSE
You MUST follow this exact format:

### 📝 Summary
[Provide a user-friendly, helpful message first. Explain your understanding of the query and how it fits into the compliance landscape.]

---

### ⚖️ Legal Applicability
[Identify specific Section/Rule from the Factories Act. If no 80-90% match found, state "Not Applicable".]

### 📜 Technical Standard Applicability
[Identify specific IS Standard/Clause. If no 80-90% match found, state "Not Applicable".]

### 🔍 Compliance Gap
[Analyze if the current query implies a mismatch with the law or standards. Describe 'potential' gap based on best practices. Be specific to user context.]

### 🚨 Risk Exposure
[Detail legal, operational, and safety risks if these clauses are violated.]

### ✅ Recommended Action
[Provide step-by-step practical advice to achieve full compliance. Ensure accuracy to user's requirement.]

### 📂 Evidence Required
[List specific documents, logs, or certificates required to prove compliance during an audit.]

---

USER QUERY: {query}
INDUSTRY: {site_profile.get('industry_type', 'General')}
MAH STATUS: {site_profile.get('mah_status', 'N/A')}

LEGAL DATA (Factories Act):
{act_text}

STANDARDS DATA:
{std_text}
"""
    return prompt


def legal_mode(query: str, site_profile: dict):
    # Greeting / Out-of-Scope Pre-check
    lower_q = query.lower().strip()
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon"]
    if any(lower_q == g or lower_q.startswith(g + " ") for g in greetings):
        return {
            "detected_topic": "GREETING",
            "legal_matches": [],
            "standard_matches": [],
            "draft_response": "Hello! I am **Navi.AI**, your Compliance Intelligent Assistant. I can help you with legal lookups, technical standards, and safety audit analysis. How can I assist you today?"
        }

    # PHASE 1: Query Decomposition
    log_rag_flow("Query received", query)
    
    decomposed_queries = decompose_query(query)
    log_rag_flow("Expanded Queries", decomposed_queries)
    
    # PHASE 2: Topic Detection
    topic = get_topic_for_text(query)
    log_rag_flow("Detected Topic", topic)

    # PHASE 3: Multi-Query Hybrid Retrieval
    act_results = multi_query_hybrid_search(
        table_name="act_index",
        sub_queries=decomposed_queries,
        compliance_topic=topic,
        top_k=5
    )
    log_rag_flow("Initial Act Retrieval", [{"id": r.get("id"), "section": r.get("section_number")} for r in (act_results or [])])
    
    std_results = multi_query_hybrid_search(
        table_name="standard_index",
        sub_queries=decomposed_queries,
        compliance_topic=topic,
        top_k=5
    )
    log_rag_flow("Initial Std Retrieval", [{"id": r.get("id"), "clause": r.get("clause_number")} for r in (std_results or [])])

    # PHASE 4: Filtering & Ranking
    act_results = act_results[:3] if act_results else []
    act_results = filter_general_sections(act_results)
    act_results = authority_rank(act_results)
    log_rag_flow("Filtered Act Results", [{"id": r.get("id"), "section": r.get("section_number")} for r in act_results])
    
    std_results = std_results[:5] if std_results else []
    std_results = authority_rank(std_results)
    log_rag_flow("Ranked Std Results", [{"id": r.get("id"), "clause": r.get("clause_number")} for r in std_results])
    
    # PHASE 5: Aggregation & Context Expansion
    if std_results:
        conn = get_db_connection()
        try:
            std_results = expand_standard_context(std_results, conn)
            log_rag_flow("Expanded Std Context", [{"clause": r.get("clause_number")} for r in std_results])
        finally:
            conn.close()
            
    std_results = aggregate_standard_sections(std_results)
    log_rag_flow("Aggregated Std Sections", [{"section": r.get("section_number"), "clauses": r.get("clauses")} for r in std_results])

    if not act_results and not std_results:
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "standard_matches": [],
            "draft_response": "### 🧐 Scope Validation\nI am designed specifically for **Compliance & Safety Intelligence**. I couldn't find any directly governing provisions in the Factories Act or technical Standards for this specific query."
        }

    prompt = build_legal_prompt(query, site_profile, act_results, std_results)
    response = generate_response(prompt)

    law_context = "\n\n".join([f"Factories Act Section {r.get('section_number')}:\n{r.get('content')}" for r in act_results])
    std_context = "\n\n".join([f"{r.get('standard_code')}:{r.get('year')} Clause {r.get('clause_number')}:\n{r.get('content')}" for r in std_results])

    verification_prompt = f"""
You are a Senior Compliance Auditor. Your task is to verify the DRAFT RESPONSE against the SOURCE LAW and STANDARDS for extreme factual accuracy.

SOURCE LAW:
{law_context or "None"}

SOURCE STANDARDS:
{std_context or "None"}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1) Ensure 'Legal & Standard Applicability' is rephrased for humans but stays 100% true to the sources.
2) Use the format: "IS XXX:YYYY, Clause X.Y.Z" for standards.
3) DO NOT REMOVE the headers or 'Query Analysis'.
4) Ensure the tone is professional yet helpful.

Return the final, polished, and verified response.
"""
    verified_response = generate_response(verification_prompt)
    verified_response = re.sub(r"Draft\s*–\s*For Professional Review", "", verified_response, flags=re.IGNORECASE).strip()

    # PHASE 2: Citation Validation Guard
    invalid_citations = validate_citations(
        verified_response,
        act_results,
        std_results
    )
    if invalid_citations:
        log_rag_flow("Invalid citations detected", invalid_citations)

    raw_acts_display = "\n\n".join([
        f"### Section {r.get('section_number')}: {r.get('section_title')}\n\n{r.get('content')}"
        for r in act_results
    ])
    
    if std_results:
        raw_acts_display += "\n\n--- Tech Standards ---\n\n" + "\n\n".join([
            f"### {r.get('standard_code')}:{r.get('year')} Clause {r.get('clause_number')}: {r.get('clause_title')}\n\n{r.get('content')}"
            for r in std_results
        ])

    return {
        "detected_topic": topic,
        "legal_matches": act_results,
        "standard_matches": std_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display
    }