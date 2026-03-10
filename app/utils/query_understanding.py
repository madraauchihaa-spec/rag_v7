# app/utils/query_understanding.py
from rapidfuzz import process, fuzz

LEGAL_TERMS = [
    "safety",
    "machine guarding",
    "fire extinguisher",
    "earthing",
    "protective equipment",
    "emergency exit",
    "belt drive",
    "electrical protection",
    "ventilation",
    "lighting",
    "welfare",
    "canteen",
    "first aid",
    "hazardous",
    "chemical",
    "scaffolding",
    "pressure vessel",
    "boiler",
    "hoist",
    "conveyor"
]

SYNONYM_MAP = {
    "ppe": "personal protective equipment",
    "earthing": "grounding",
    "fire exit": "emergency exit",
    "worker": "workmen",
    "employees": "workmen",
    "machine guard": "machine guarding",
    "belt": "belt drive",
}

STOP_WORDS = {
    "what", "is", "the", "are", "for", "of", "in", "to", "a", "an", "on", "with", "from", "at", "by"
}

def correct_typos(query):
    words = query.split()
    corrected = []

    for w in words:
        # Avoid correcting very short words or numbers
        if len(w) <= 2 or w.isdigit():
            corrected.append(w)
            continue
            
        match = process.extractOne(w, LEGAL_TERMS, scorer=fuzz.ratio)
        if match and match[1] > 80:
            corrected.append(match[0])
        else:
            corrected.append(w)

    return " ".join(corrected)

def normalize_query(query):
    q = query.lower()

    # Apply synonym mapping
    for k, v in SYNONYM_MAP.items():
        if f" {k} " in f" {q} ":
            q = q.replace(k, v)

    q = correct_typos(q)
    return q

def extract_keywords(query):
    # Remove special characters for keyword extraction
    clean_q = "".join([c if c.isalnum() or c.isspace() else " " for c in query.lower()])
    words = clean_q.split()

    return [w for w in words if w not in STOP_WORDS and len(w) > 2]

def build_query_set(query):
    normalized = normalize_query(query)
    keywords = extract_keywords(normalized)
    
    # Base set includes original and normalized
    queries = [query, normalized]

    # Add keyword-only version for better recall in vector search
    if len(keywords) > 1:
        queries.append(" ".join(keywords))

    # Remove duplicates and empty strings
    return list(set([q.strip() for q in queries if q.strip()]))
