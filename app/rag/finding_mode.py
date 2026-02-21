import re
from retrieval.hybrid_search import search_sar, search_act
from utils.llm_client import generate_response
from utils.intent_classifier import classify_query_intent
from utils.reranker import llm_rerank
from utils.governance import filter_general_sections, detect_overreach

def build_prompt(issue, site_profile, sar_results, act_results):
    sar_text = "\n\n".join(
        [f"EXPERIENCE CASE {i+1}:\nObservation: {r['observation']}\nRecommendation: {r['recommendation']}"
         for i, r in enumerate(sar_results)]
    )

    act_text = "\n\n".join(
        [f"ACT SECTION {r['section_number']} - {r['section_title']}\n{r['content']}"
         for r in act_results]
    )

    prompt = f"""
SYSTEM ROLE: You are a Senior Compliance Auditor. Your task is to analyze the USER ISSUE using ONLY the provided LEGAL CLAUSES and PAST FINDINGS.

CRITICAL GROUNDING RULES:
1. CITATION GATE: You must ONLY reference the sections provided below. Use ONLY legal sections from the 'APPLICABLE LEGAL CLAUSES' list.
2. NO HALLUCINATION: You are strictly prohibited from citing any section number or Act not present in the retrieved list. Do NOT invent thresholds, numbers, or frequencies unless they are EXPLICITLY stated in the text provided.
3. STRICT GOVERNANCE:
   - Only cite a section if it directly regulates the specific subject matter described in the user query.
   - Do NOT use general duty sections (e.g., Section 7A) if a more specific section exists in the list.
   - Do NOT stretch interpretation beyond what is explicitly written.
   - Do NOT infer regulatory intent beyond the section's wording.
   - Do NOT escalate to hazardous process sections unless the issue explicitly involves hazardous processes.
4. SOURCE DISTINCTION: 
   - 'ACT SECTIONS' are the primary law. 
   - 'EXPERIENCE CASES' (SAR) are past audit observations, NOT the law itself. Do not cite SAR findings as legal mandates.
5. MISSING INFO: If none of the retrieved sections directly govern the issue, clearly state: "No directly governing section found in the retrieved Factories Act database."

USER ISSUE:
{issue}

SITE PROFILE:
Industry: {site_profile.get("industry_type")}
MAH Status: {site_profile.get("mah_status")}

SIMILAR PAST FINDINGS (Audit Experience):
{sar_text if sar_text else "No similar past findings found."}

APPLICABLE LEGAL CLAUSES (Primary Law):
{act_text if act_text else "No relevant legal clauses found in the current corpus."}

Before drafting Legal Applicability, internally verify for each section:
1. Does the section explicitly regulate this issue?
2. Is the subject matter clearly mentioned in the section?
3. Would a compliance inspector directly cite this section for this violation?
If the answer is NO, exclude that section from your analysis.

Generate structured response:

1. **Legal Applicability**
   - Cite the specific Section Number and Title from the ACT sections.
   - Summarize what the law explicitly says.
   - If a specific detail (like a number) is missing from the provided text, say "The provided text does not specify [X]; check State Rules."

2. **Compliance Gap**
   - Compare the USER ISSUE directly against the legal text.

3. **Risk Exposure**
   - Technical and legal risks.

4. **Recommended Action**
   - Concrete steps to fix the issue.

5. **Evidence Required**
   - What document/photo is needed to prove it's fixed.
"""
    return prompt

def finding_mode(issue: str, site_profile: dict):
    """
    Enhanced Finding Mode with Metadata filtering and Diversity.
    """
    # 1. Classify Issue Topic
    topic = classify_query_intent(issue)

    # 2. Search SAR findings with metadata priority and topic boost
    sar_results = search_sar(
        issue,
        industry_type=site_profile.get("industry_type"),
        mah_status=site_profile.get("mah_status"),
        compliance_topic=topic
    )

    # 3. Search Legal matches with topic guidance
    legal_query = issue
    act_results = search_act(legal_query, compliance_topic=topic)

    # Rerank Results
    if act_results:
        act_results = llm_rerank(issue, act_results)
        # Allow 2-3 sections if they are truly relevant
        act_results = act_results[:3]
    
    # 3.5 Apply Legal Governance - Filter General Sections
    act_results = filter_general_sections(act_results)

    print(f"[LEGAL MATCH COUNT]: {len(act_results)}")
    if act_results:
        print(f"[LEGAL SECTIONS USED]: {[m['section_number'] for m in act_results]}")

    if not act_results:
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "sar_matches": sar_results,
            "draft_response": """
### ⚠️ No Direct Legal Provision Found
No directly governing section found in the retrieved Factories Act database for this specific finding.
"""
        }

    # 4. Generate Response
    prompt = build_prompt(issue, site_profile, sar_results, act_results)
    response = generate_response(prompt)

    # --- VERIFICATION LAYER ---
    source_context = "\n\n".join([f"SECTION {r.get('section_number')}:\n{r.get('content')}" for r in act_results])

    verification_prompt = f"""
SYSTEM ROLE: You are a strict Compliance Auditor & Fact-Checker.
YOUR TASK: Verify the 'DRAFT RESPONSE' against the 'SOURCE LAW'.

SOURCE LAW:
{source_context}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1. Ensure the 'Summary' and audit logic strictly follows the Source Law.
2. Verify that no technical values (mm, rpm, kg, days) are invented.
3. Remove any 'Draft' headers.

FINAL VERIFIED RESPONSE:
"""
    verified_response = generate_response(verification_prompt)
    verified_response = re.sub(r"Draft\s*–\s*For Professional Review", "", verified_response, flags=re.IGNORECASE).strip()

    # --- PREPARE RAW ACTS (No AI involvement) ---
    raw_acts_display = "\n\n".join([
        f"### Section {r.get('section_number')}: {r.get('section_title')}\n\n{r.get('content')}"
        for r in act_results
    ])

    return {
        "detected_topic": topic,
        "sar_matches": sar_results,
        "legal_matches": act_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display # Raw text directly from DB
    }
