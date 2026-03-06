INTENTS = {
    "LEGAL_QUERY": [
        "section",
        "rule",
        "law",
        "as per",
        "requirement",
        "mandatory",
        "provision",
        "penalty",
        "license",
        "renewal"
    ],
    "AUDIT_FINDING": [
        "observed",
        "found",
        "missing",
        "broken",
        "damaged",
        "blocked",
        "not available",
        "violation",
        "incident",
        "accident",
        "leak",
        "spill"
    ],
    "TECHNICAL_STANDARD": [
        "standard",
        "specification",
        "clause",
        "is code",
        "technical",
        "testing",
        "maintenance",
        "installation"
    ]
}


def classify_intent(query: str):
    """
    Classifies the user query into LEGAL_QUERY, AUDIT_FINDING, 
    or TECHNICAL_STANDARD based on keyword density.
    """
    q = query.lower()
    scores = {intent: 0 for intent in INTENTS}

    for intent, keywords in INTENTS.items():
        for k in keywords:
            if k in q:
                scores[intent] += 1

    # Default to LEGAL_QUERY if no keywords match (most common baseline)
    if all(score == 0 for score in scores.values()):
        return "LEGAL_QUERY"

    # Return the intent with the highest score
    return max(scores, key=scores.get)
