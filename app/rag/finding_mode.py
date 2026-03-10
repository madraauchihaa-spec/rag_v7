import re
import os
from collections import defaultdict
from retrieval.hybrid_search import search_sar, get_db_connection
from retrieval.context_expander import expand_standard_context, aggregate_standard_sections
from retrieval.advanced_retrieval import multi_query_hybrid_search, authority_rank
from utils.query_decomposer import decompose_query
from utils.llm_client import generate_response, LLMError
from utils.ontology import get_topic_for_text
from utils.governance import filter_general_sections
from utils.logger import log_rag_flow
from utils.citation_validator import validate_citations
from utils.text_cleaner import truncate_text




def build_prompt(issue, site_profile, sar_results, act_results, std_results):
    sar_text = "\n\n".join(
        [f"EXPERIENCE CASE {i+1}:\nObservation: {r['observation']}\nRecommendation: {r['recommendation']}"
         for i, r in enumerate(sar_results)]
    )

    act_text = "\n\n".join(
        [f"LAW: Factories Act - Section {r['section_number']} ({r['section_title']})\n{r['content']}"
         for r in act_results]
    )

    std_text = "\n\n".join(
        [
            f"STANDARD: {r.get('standard_code')}:{r.get('year')} - Section {r.get('section_number')} ({r.get('section_title')})\n"
            f"Clauses: {', '.join(r.get('clauses', []))}\n"
            f"{r.get('content')}"
            for r in std_results
        ]
    )
    
    sar_text = truncate_text(sar_text, 1000)
    act_text = truncate_text(act_text, 1500)
    std_text = truncate_text(std_text, 1500)

    prompt = f"""
SYSTEM ROLE: You are Navi.AI, a Compliance Intelligence Specialist. Your goal is to map audit findings to legal frameworks and technical standards with extreme precision.

STEP 1: QUERY COMPREHENSION
First, deep-dive into the user's issue. Understand the technical and operational context.

STEP 2: CITATION RULES
1) Only cite provisions present in LEGAL DATA or STANDARDS DATA.
2) Do not create new sections or clauses.
3) If no provision applies, write "Not Applicable".

STEP 3: RETRIEVAL ANALYSIS
Compare the issue against the provided LEGAL DATA and STANDARDS DATA.
ONLY cite a provision if it is an 80-90% MATCH to the requirement. If the data is only tangentially related or too general, you MUST state "Not Applicable" for that section.

STEP 4: STRUCTURED RESPONSE
You MUST follow this exact format:

### 📝 Executive Summary
[Provide a clear, high-level overview of the issue and its significance. Use **bold text** for emphasis.]

---

### 🔍 Fact-Check Table
| Source Category | Status | Provision Reference |
| :--- | :--- | :--- |
| **Legal (Factories Act)** | [Applicable/N.A.] | [Section No.] |
| **Tech Standards** | [Applicable/N.A.] | [IS Code:Year] |

---

### 🔴 Observation & Gap Analysis
* **Current State**: [Describe the problem found]
* **Legal Requirement**: [Cite specific law/standard details]
* **Compliance Gap**: [Highlight the exact mismatch with **bold** highlights]

### 🚨 Risk & Business Impact
* **Safety Risk**: [Specific hazard]
* **Legal Exposure**: [Potential penalties or fines]

### ✅ Actionable Recommendations
1. **Immediate Step**: [Prioritized action]
2. **Systemic Change**: [Long-term fix based on best practices]

### 📂 Proof of Compliance (Audit Evidence)
* [ ] [Evidence item 1 - e.g. Inspection Logs]
* [ ] [Evidence item 2 - e.g. Training Records]

---

USER ISSUE: {issue}
INDUSTRY: {site_profile.get("industry_type", "General")}
MAH STATUS: {site_profile.get("mah_status", "N/A")}

LEGAL DATA (Factories Act):
{act_text if act_text else "No directly relevant law found."}

STANDARDS DATA:
{std_text if std_text else "No directly relevant standard clause found."}

EXPERIENCE DATA (SAR):
{sar_text if sar_text else "No past audit records found."}
"""
    return prompt


def finding_mode(issue: str, site_profile: dict):
    # Greeting / Out-of-Scope Pre-check
    lower_q = issue.lower().strip()
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon"]
    if any(lower_q == g or lower_q.startswith(g + " ") for g in greetings):
        return {
            "detected_topic": "GREETING",
            "sar_matches": [],
            "legal_matches": [],
            "standard_matches": [],
            "draft_response": "Hello! I am **Navi.AI**, your Compliance Intelligent Assistant. I can help you analyze audit observations and find their corresponding legal requirements and technical standards. How can I help you today?"
        }

    log_rag_flow("Query received", issue)
    
    topic = get_topic_for_text(issue)
    log_rag_flow("Detected Topic", topic)

    # Phase 1: Query Decomposition
    decomposed_queries = decompose_query(issue)
    log_rag_flow("Expanded Queries", decomposed_queries)

    # Phase 2: Retrieval
    sar_results = search_sar(
        issue,
        industry_type=site_profile.get("industry_type"),
        mah_status=site_profile.get("mah_status"),
        compliance_topic=topic
    )
    log_rag_flow("Retrieved SAR Matches", [{"id": r.get("id"), "score": r.get("score")} for r in sar_results])

    act_results = multi_query_hybrid_search(
        table_name="act_index",
        sub_queries=decomposed_queries,
        compliance_topic=topic,
        top_k=5
    )
    
    std_results = multi_query_hybrid_search(
        table_name="standard_index",
        sub_queries=decomposed_queries,
        compliance_topic=topic,
        top_k=7
    )
    
    log_rag_flow("Initial Act Retrieval", [{"id": r.get("id"), "section": r.get("section_number")} for r in (act_results or [])])
    log_rag_flow("Initial Std Retrieval", [{"id": r.get("id"), "clause": r.get("clause_number")} for r in (std_results or [])])

    # Phase 7: Context Expansion
    if std_results:
        conn = get_db_connection()
        try:
            std_results = expand_standard_context(std_results, conn)
            log_rag_flow("Expanded Std Context", [{"clause": r.get("clause_number")} for r in std_results])
        finally:
            from retrieval.hybrid_search import release_db_connection
            release_db_connection(conn)

    # Filtering & Ranking
    act_results = act_results[:3] if act_results else []
    act_results = filter_general_sections(act_results)
    act_results = authority_rank(act_results)
    
    std_results = std_results[:5] if std_results else []
    std_results = authority_rank(std_results)
    std_results = aggregate_standard_sections(std_results)
    log_rag_flow("Aggregated Std Sections", [{"section": r.get("section_number"), "clauses": r.get("clauses")} for r in std_results])

    if not act_results and not std_results:
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "sar_matches": sar_results,
            "standard_matches": [],
            "draft_response": "### ⚠️ No Direct Legal or Standard Provision Found\nNo directly governing Factories Act section or Standard clause found in the retrieved database."
        }

    try:
        prompt = build_prompt(issue, site_profile, sar_results, act_results, std_results)
        response = generate_response(prompt)

        # Verification Pass
        law_context = "\n\n".join([f"Factories Act - Section {r.get('section_number')}:\n{r.get('content')}" for r in act_results])
        std_context = "\n\n".join([f"{r.get('standard_code')}:{r.get('year')} Section {r.get('section_number')}:\n{r.get('content')}" for r in std_results])

        verification_prompt = f"""
You are a Senior Compliance Auditor. Your task is to verify the DRAFT RESPONSE against the SOURCE LAW, STANDARDS, and EXPERIENCE CASES.

SOURCE LAW:
{law_context or "None"}

SOURCE STANDARDS:
{std_context or "None"}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1) Use **Bold Headings** for key terms and identifiers.
2) Use **Structured Bullet Points** (not just blocks of text).
3) Ensure 'Fact-Check Table' is accurately filled.
4) Keep the tone professional, authoritative, and helpful.
5) USE MARKDOWN: Utilize bolding, lists, and tables to make the response "premium".

Return the final, polished, and verified response.
"""
        verified_response = generate_response(verification_prompt)
        verified_response = re.sub(r"Draft\s*–\s*For Professional Review", "", verified_response, flags=re.IGNORECASE).strip()
    except LLMError as e:
        return {
            "detected_topic": topic,
            "sar_matches": sar_results,
            "legal_matches": act_results,
            "standard_matches": std_results,
            "draft_response": f"### ⚠️ AI Service Error\nI encountered an error while analyzing the compliance data: {str(e)}"
        }

    # PHASE 2: Citation Validation Guard
    invalid_citations = validate_citations(
        verified_response,
        act_results,
        std_results
    )
    if invalid_citations:
        log_rag_flow("Invalid citations detected", invalid_citations)
        verified_response += f"\n\n> [!WARNING]\n> **Citation Audit**: Some cited provisions ({', '.join(invalid_citations)}) were not found in the retrieved context. Please verify manually."

    raw_acts_display = "\n\n".join([
        f"### Section {r.get('section_number')}: {r.get('section_title')}\n\n{r.get('content')}"
        for r in act_results
    ])
    
    if std_results:
        raw_acts_display += "\n\n--- Tech Standards ---\n\n" + "\n\n".join([
            f"### {r.get('standard_code')}:{r.get('year')} Section {r.get('section_number')}\n**Clauses**: {', '.join(r.get('clauses', []))}\n\n{r.get('content')}"
            for r in std_results
        ])
    
    # Return matched objects too
    return {
        "detected_topic": topic,
        "sar_matches": sar_results,
        "legal_matches": act_results,
        "standard_matches": std_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display
    }