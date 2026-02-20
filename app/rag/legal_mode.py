# app/rag/legal_mode.py
from retrieval.hybrid_search import hybrid_search
from utils.llm_client import generate_response
from utils.intent_classifier import classify_query_intent

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
2. CITATION DISCIPLINE: Do NOT invent thresholds, numbers, timelines, or frequencies. If a specific requirement (like 'once every six months') is not in the text, state: "The provided Factories Act excerpt mentions [X], but the specific frequency is not in this text; check the State Rules."
3. SOURCE VERACITY: If the provided text contains placeholders like '(as may be prescribed)', explain that this indicates a dependency on State Rules which are not currently in the primary Act text.
4. SITE APPLICABILITY: Evaluate how the law applies specifically to the site profile (Industry: {site_profile.get("industry_type")}).

LEGAL QUERY:
{query}

RELEVANT LEGAL PROVISIONS:
{act_text if act_text else "No relevant legal clauses found in the current corpus."}

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

Mark output as:
Draft – For Professional Review
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

    # 3. Build Prompt with Topic Context
    prompt = build_legal_prompt(query, site_profile, act_results)
    if topic != "GENERAL_SAFETY":
        prompt = f"DETECTED COMPLIANCE AREA: {topic}\n\n" + prompt

    response = generate_response(prompt)

    return {
        "detected_topic": topic,
        "legal_matches": act_results,
        "draft_response": response
    }
