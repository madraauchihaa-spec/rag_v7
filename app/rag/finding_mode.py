# app/rag/finding_mode.py
import re
from retrieval.hybrid_search import search_sar, search_act
from utils.llm_client import generate_response
from utils.ontology import get_topic_for_text
from utils.governance import filter_general_sections

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
SYSTEM ROLE: You are Navi.AI, a Compliance Intelligence Specialist. Your goal is to map audit findings to legal frameworks.

STEP 1: FINDING EVALUATION
Analyze the user's audit issue. If it's a greeting or completely unrelated to industrial safety/factories, politely redirect the user.
Bridge the user's natural language finding to the structured legal data provided.

STEP 2: STRUCTURED RESPONSE
You MUST follow this exact format:

### 🛠️ Query Analysis
[Explain how this specific audit finding relates to the legal requirements of the Factories Act]

---

### 1) Legal Applicability
[Identify the specific Section/Rule from the LEGAL DATA that governs this issue. Rephrase it clearly for a safety officer.]

### 2) Compliance Gap
[Detail exactly where the user's issue fails to meet the legal criteria. If no direct gap is found in experience data, construct a logical compliance gap based on the law.]

### 3) Risk Exposure
[Identify safety hazards, environmental risks, and potential legal fines/prosecutions.]

### 4) Recommended Action
[Provide a clear, actionable solution. Incorporate 'EXPERIENCE CASES' if they provide better practical solutions.]

### 5) Evidence Required
[List proofs needed: e.g., Inspection Certificates, Maintenance Logs, Training Records.]

---

USER ISSUE: {issue}
INDUSTRY: {site_profile.get("industry_type", "General")}
MAH STATUS: {site_profile.get("mah_status", "N/A")}

EXPERIENCE DATA (SAR):
{sar_text if sar_text else "No past audit records found."}

LEGAL DATA:
{act_text if act_text else "No directly relevant law found."}
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
            "draft_response": "Hello! I am **Navi.AI**, your Compliance Intelligent Assistant. I can help you analyze audit observations and find their corresponding legal requirements in the Factories Act. How can I help you today?"
        }

    topic = get_topic_for_text(issue)

    # Retrieval
    sar_results = search_sar(
        issue,
        industry_type=site_profile.get("industry_type"),
        mah_status=site_profile.get("mah_status"),
        compliance_topic=topic
    )

    act_results = search_act(issue, compliance_topic=topic)

    # Keep top 3 and apply governance filter
    act_results = (act_results or [])[:3]
    act_results = filter_general_sections(act_results)

    if not act_results:
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "sar_matches": sar_results,
            "draft_response": "### ⚠️ No Direct Legal Provision Found\nNo directly governing section found in the retrieved Factories Act database."
        }

    prompt = build_prompt(issue, site_profile, sar_results, act_results)
    response = generate_response(prompt)

    # Verification Pass
    source_context = "\n\n".join([f"SECTION {r.get('section_number')}:\n{r.get('content')}" for r in act_results])

    verification_prompt = f"""
You are a Senior Compliance Auditor. Your task is to verify the DRAFT RESPONSE against the SOURCE LAW and EXPERIENCE CASES.

SOURCE LAW:
{source_context}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1) Ensure 'Legal Applicability' is rephrased for a human (not just a legal copy-paste) but stays 100% true to the law.
2) Ensure the 'Compliance Gap' clearly explains why the user finding is a violation of the Law.
3) DO NOT REMOVE the headers or the 'Query Analysis' section.
4) Ensure 'Recommended Action' is practical and grounded in both Law and Experience.
5) Maintain a professional and helpful tone.

Return the final, polished, and verified response.
"""
    verified_response = generate_response(verification_prompt)
    verified_response = re.sub(r"Draft\s*–\s*For Professional Review", "", verified_response, flags=re.IGNORECASE).strip()

    raw_acts_display = "\n\n".join([
        f"### Section {r.get('section_number')}: {r.get('section_title')}\n\n{r.get('content')}"
        for r in act_results
    ])

    return {
        "detected_topic": topic,
        "sar_matches": sar_results,
        "legal_matches": act_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display
    }