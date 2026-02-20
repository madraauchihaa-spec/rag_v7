# app/rag/finding_mode.py
from retrieval.hybrid_search import search_sar, search_act
from utils.llm_client import generate_response
from utils.intent_classifier import classify_query_intent

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
1. CITATION GATE: You must ONLY cite legal sections from the 'APPLICABLE LEGAL CLAUSES' list below. 
2. NO HALLUCINATION: Do NOT invent thresholds, numbers, or frequencies (e.g., "once in 6 months", "4 boxes") unless they are EXPLICITLY stated in the text provided. If the text says 'as may be prescribed', state that the specific frequency is not in the current text and requires checking the State Rules.
3. SOURCE DISTINCTION: 
   - 'ACT SECTIONS' are the primary law. 
   - 'EXPERIENCE CASES' (SAR) are past audit observations, NOT the law itself. Do not cite SAR findings as legal mandates.
4. MISSING INFO: If the provided legal clauses do not directly cover a specific aspect (like rubber matting or secondary containment), state: "The provided Factories Act excerpts do not explicitly mandate [item], but Section [X] regarding [General Duty] provides a relevant framework."

USER ISSUE:
{issue}

SITE PROFILE:
Industry: {site_profile.get("industry_type")}
MAH Status: {site_profile.get("mah_status")}

SIMILAR PAST FINDINGS (Audit Experience):
{sar_text if sar_text else "No similar past findings found."}

APPLICABLE LEGAL CLAUSES (Primary Law):
{act_text if act_text else "No relevant legal clauses found in the current corpus."}

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

Mark output as:
Draft – For Professional Review
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

    # 4. Generate Response
    prompt = build_prompt(issue, site_profile, sar_results, act_results)
    if topic != "GENERAL_SAFETY":
        prompt = f"ROOT TOPIC: {topic}\n\n" + prompt

    response = generate_response(prompt)

    return {
        "detected_topic": topic,
        "sar_matches": sar_results,
        "legal_matches": act_results,
        "draft_response": response
    }
