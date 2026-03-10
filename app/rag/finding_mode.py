import re
from collections import defaultdict
from retrieval.hybrid_search import search_sar, search_act, search_standard, get_db_connection
from retrieval.context_expander import expand_standard_context
from utils.llm_client import generate_response
from utils.ontology import get_topic_for_text
from utils.governance import filter_general_sections
from utils.logger import log_rag_flow
from utils.citation_validator import validate_citations
from utils.text_cleaner import truncate_text

def aggregate_standard_sections(results):
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

### 📝 Summary
[Provide a user-friendly, helpful message first. Explain your understanding of the query and how it fits into the compliance landscape.]

---

### ⚖️ Legal Applicability
[Identify specific Section/Rule from the Factories Act. If no 80-90% match found, state "Not Applicable".]

### 📜 Technical Standard Applicability
[Identify specific IS Standard/Clause. If no 80-90% match found, state "Not Applicable".]

### 🔍 Compliance Gap
[Detail exactly where the user's issue fails to meet the legal or standard criteria. Be specific to the user's requirement.]

### 🚨 Risk Exposure
[Identify specific safety hazards, environmental risks, and potential legal fines/prosecutions.]

### ✅ Recommended Action
[Provide a clear, actionable solution. Use 'EXPERIENCE CASES' and 'STANDARDS DATA' for practical and technical solutions. Ensure it's accurate to the user's need.]

### 📂 Evidence Required
[List specific proofs needed: e.g., Inspection Certificates, Maintenance Logs, Training Records.]

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

    # Retrieval
    sar_results = search_sar(
        issue,
        industry_type=site_profile.get("industry_type"),
        mah_status=site_profile.get("mah_status"),
        compliance_topic=topic
    )
    log_rag_flow("Retrieved SAR Matches", [{"id": r.get("id"), "score": r.get("score")} for r in sar_results])


    act_results = search_act(issue, compliance_topic=topic)
    std_results = search_standard(issue, compliance_topic=topic)
    
    log_rag_flow("Initial Act Retrieval", [{"id": r.get("id"), "section": r.get("section_number")} for r in (act_results or [])])
    log_rag_flow("Initial Std Retrieval", [{"id": r.get("id"), "clause": r.get("clause_number")} for r in (std_results or [])])

    # Phase 7: Context Expansion
    if std_results:
        conn = get_db_connection()
        try:
            std_results = expand_standard_context(std_results, conn)
            log_rag_flow("Expanded Std Context", [{"clause": r.get("clause_number")} for r in std_results])
        finally:
            conn.close()

    # Filtering
    act_results = act_results[:3] if act_results else []
    act_results = filter_general_sections(act_results)
    
    std_results = std_results[:5] if std_results else []
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
1) Ensure 'Legal & Standard Applicability' is rephrased for humans but stays 100% true to the law/standards.
2) When citing standards, use the format: "IS XXX:YYYY, Clause X.Y.Z".
3) Ensure 'Compliance Gap' clearly explains the violation.
4) DO NOT REMOVE headers or 'Query Analysis'.
5) Maintain professional tone.

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