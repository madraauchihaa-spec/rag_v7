# app/rag/legal_mode.py
import re
from retrieval.hybrid_search import hybrid_search
from utils.llm_client import generate_response
from utils.ontology import get_topic_for_text
from utils.governance import filter_general_sections

def build_legal_prompt(query, site_profile, act_results):
    act_text = "\n\n".join(
        [
            f"ACT SECTION {r.get('section_number')} - {r.get('section_title')}\n{r.get('content')}"
            for r in act_results
        ]
    )

    prompt = f"""
SYSTEM ROLE: You are Navi.AI, a highly specialized Compliance Intelligent Assistant for Safety and Legal Professionals.

STEP 1: QUERY ANALYSIS
Interpret the user's intent. If it's a greeting, respond warmly. If it's outside the scope of safety/legal/compliance, politely decline.
If it's a valid query, bridge any partial text or synonyms to the formal legal matches provided.

STEP 2: STRUCTURED RESPONSE (ONLY use the sections below)
You MUST follow this exact Markdown format:

### 🛠️ Query Analysis
[Briefly explain how you interpreted the query and its legal relevance]

---

### 1) Legal Applicability
[Rephrase the retrieved law into human-readable language. Ensure 100% accuracy to the DB content. Focus on how it applies to the user's industry/state.]

### 2) Compliance Gap
[Analyze if the current query implies a mismatch with the law. If no direct gap is found in data, describe the 'potential' gap based on compliance best practices.]

### 3) Risk Exposure
[Detail the legal, operational, and safety risks if this clause is violated.]

### 4) Recommended Action
[Step-by-step practical advice to achieve full compliance.]

### 5) Evidence Required
[List documents, logs, or certificates required to prove compliance during an audit.]

---

USER QUERY: {query}
INDUSTRY: {site_profile.get('industry_type', 'General')}
MAH STATUS: {site_profile.get('mah_status', 'N/A')}

LEGAL DATA:
{act_text}
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
            "draft_response": "Hello! I am **Navi.AI**, your Compliance Intelligent Assistant. I can help you with legal lookups, safety audit analysis, and understanding Factories Act requirements. How can I assist you today?"
        }

    topic = get_topic_for_text(query)

    # Retrieval
    act_results = hybrid_search(
        table_name="act_index",
        query_text=query,
        top_k=5,
        compliance_topic=topic,
        diversity_lambda=0.70
    )

    act_results = (act_results or [])[:3]
    act_results = filter_general_sections(act_results)

    if not act_results:
        # Check if it's completely out of scope using LLM or just default
        return {
            "detected_topic": topic,
            "legal_matches": [],
            "draft_response": "### 🧐 Scope Validation\nI am designed specifically for **Compliance & Safety Intelligence**. I couldn't find any directly governing provisions in the Factories Act for this specific query. If this is a general question, please rephrase it with safety-related keywords."
        }

    prompt = build_legal_prompt(query, site_profile, act_results)
    response = generate_response(prompt)

    source_context = "\n\n".join([f"SECTION {r.get('section_number')}:\n{r.get('content')}" for r in act_results])

    verification_prompt = f"""
You are a Senior Compliance Auditor. Your task is to verify the DRAFT RESPONSE against the SOURCE LAW for extreme factual accuracy.

SOURCE LAW:
{source_context}

DRAFT RESPONSE:
{response}

INSTRUCTIONS:
1) Ensure 'Legal Applicability' is rephrased for a human (not just a legal copy-paste) but stays 100% true to the law.
2) If the original response mentioned a 'Compliance Gap' that is not supported by the law, correct it.
3) DO NOT REMOVE the headers or the 'Query Analysis' section.
4) Remove any technical jargon that is not necessary.
5) Ensure the tone is professional yet helpful.

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
        "legal_matches": act_results,
        "draft_response": verified_response,
        "Legal Applicability": raw_acts_display
    }