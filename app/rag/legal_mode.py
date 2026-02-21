import re
from retrieval.hybrid_search import hybrid_search
from utils.llm_client import generate_response
from utils.intent_classifier import classify_query_intent
from utils.reranker import llm_rerank
from utils.governance import filter_general_sections, detect_overreach

def build_legal_prompt(query, site_profile, act_results):
    """
    Builds structured legal prompt with strict grounding.
    """
    act_text = "\n\n".join(
        [
            f"ACT SECTION {r.get('section_number')} - {r.get('section_title')}\n"
            f"{r.get('content')}"
            for r in act_results
        ]
    )

    prompt = f"""
SYSTEM ROLE: You are a Senior Legal Compliance Specialist. Your goal is to provide a fact-based legal interpretation using ONLY the provided ACT clauses.

CRITICAL GROUNDING RULES:
1. NO EXTERNAL KNOWLEDGE: Answer strictly using the 'RELEVANT LEGAL PROVISIONS' provided below. 
2. CITATION DISCIPLINE: You must ONLY reference the sections provided below. You are strictly prohibited from citing any section number or Act not present in the retrieved list. Do NOT invent thresholds, numbers, timelines, or frequencies. 
3. STRICT GOVERNANCE:
   - Only cite a section if it directly regulates the specific subject matter described in the user query.
   - Do NOT use general duty sections (e.g., Section 7A) if a more specific section exists in the list.
   - Do NOT stretch interpretation beyond what is explicitly written.
   - Do NOT infer regulatory intent beyond the section's wording.
   - Do NOT escalate to hazardous process sections unless the issue explicitly involves hazardous processes.
4. SOURCE VERACITY: If none of the retrieved sections directly govern the issue, clearly state: "No directly governing section found in the retrieved Factories Act database."
5. SITE APPLICABILITY: Evaluate how the law applies specifically to the site profile (Industry: {site_profile.get("industry_type")}).

LEGAL QUERY:
{query}

RELEVANT LEGAL PROVISIONS:
{act_text if act_text else "No relevant legal clauses found in the current corpus."}

Before drafting Legal Position, internally verify for each section:
1. Does the section explicitly regulate this issue?
2. Is the subject matter clearly mentioned in the section?
3. Would a compliance inspector directly cite this section for this violation?
If the answer is NO, exclude that section from your analysis.

STRUCTURED RESPONSE:

1. **Legal Position**
   - Direct answer to the query based on the Act.
   - Mention the specific section(s).

2. **Conditions / Requirements**
   - List the explicit conditions mentioned in the text.
   - Highlight any 'prescribed' requirements that need State Rule verification.

3. **Applicability to Site Profile**
   - How this specific bit of law affects an industry of type '{site_profile.get("industry_type")}'.

4. **Compliance Steps**
   - Actionable items to ensure one is following the law.

5. **Penalty (If Applicable)**
   - ONLY mention penalties if explicitly present in the retrieved text. Otherwise, state "Penalty details for this specific provision are not provided in the current excerpt."

6. **Reference Sections**
   - List the section numbers used.
"""
    return prompt

def legal_mode(query: str, site_profile: dict):
    """
    Enhanced Legal Query Mode with Intent Classification
    """
    # 1. Classify Intent
    topic = classify_query_intent(query)

    # 2. Hybrid Search for legal provisions
    act_results = hybrid_search(
        table_name="act_index",
        query_text=query,
        top_k=5,
        compliance_topic=topic,
        diversity_lambda=0.7 
    )

    # Rerank Results
    if act_results:
        act_results = llm_rerank(query, act_results)
        # Allow 2-3 sections if they are truly relevant
        act_results = act_results[:3]
    
    # 2.5 Apply Legal Governance - Filter General Sections
    act_results = filter_general_sections(act_results)

    print(f"[LEGAL MATCH COUNT]: {len(act_results)}")
    if act_results:
        print(f"[LEGAL SECTIONS USED]: {[m['section_number'] for m in act_results]}")

    if not act_results:
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "draft_response": """
### ⚠️ No Direct Legal Provision Found
The current Factories Act database does not contain a section explicitly governing this query. 
"""
        }

    # 3. Build Prompt with Topic Context
    prompt = build_legal_prompt(query, site_profile, act_results)
    
    # Generate Initial Response
    response = generate_response(prompt)

    # --- VERIFICATION LAYER ---
    source_context = "\n\n".join([f"SECTION {r.get('section_number')}:\n{r.get('content')}" for r in act_results])
    
    verification_prompt = f"""
SYSTEM ROLE: You are a strict Legal Fact-Checker. 
YOUR TASK: Analyze the 'DRAFT RESPONSE' for accuracy against 'SOURCE TEXT'. 

SOURCE TEXT:
{source_context}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1. Verify numbers, timelines, and requirements strictly against the Source Text.
2. Ensure the response matches the user's specific query requirements.
3. Rewrite only if there are factual errors or hallucinations.
4. Remove any 'Draft' headers.

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
        "legal_matches": act_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display # Raw text directly from DB
    }
