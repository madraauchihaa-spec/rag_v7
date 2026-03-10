# app/utils/query_decomposer.py
LEGAL_EXPANSIONS = {
    "safety": [
        "safety equipment",
        "protective devices",
        "worker protection"
    ],
    "machine": [
        "machine guarding",
        "dangerous machines",
        "mechanical hazards"
    ],
    "permit": [
        "work permit system",
        "permit to work procedure"
    ],
    "electrical": [
        "electrical safety equipment",
        "earthing requirements",
        "electrical protection"
    ],
    "fire": [
        "fire protection systems",
        "fire extinguishers",
        "fire detection equipment"
    ],
    "chemical": [
        "hazardous chemicals",
        "msds requirements",
        "secondary containment",
        "spill control"
    ],
    "ppe": [
        "protective equipment",
        "safety gear",
        "mandatory ppe"
    ],
    "structural": [
        "structural stability",
        "load bearing",
        "safe access",
        "gangways"
    ],
    "hygiene": [
        "ventilation",
        "cleanliness",
        "drinking water",
        "latrines"
    ],
    "health": [
        "occupational health",
        "medical examination",
        "first aid facilities"
    ],
    "welfare": [
        "canteen facilities",
        "rest rooms",
        "washing facilities"
    ]
}

def decompose_query(query: str):
    """
    Expands the query based on pre-defined legal and safety keyword expansions.
    """
    queries = [query]
    q = query.lower()

    for keyword, expansions in LEGAL_EXPANSIONS.items():
        if keyword in q:
            queries.extend(expansions)

    return list(set(queries))
