# app/utils/ontology.py

COMPLIANCE_ONTOLOGY = {
    "FIRE_SAFETY": [
        "fire load", "fire detection", "fire extinguisher", "fire hydrant", 
        "fire hose", "smoke detector", "sprinkler", "fire wall", "emergency exit",
        "fire exit", "means of escape", "fire drill", "flammable", "combustible"
    ],
    "ELECTRICAL_SAFETY": [
        "earthing", "breaker", "mccb", "cable", "wiring", "electrical panel",
        "short circuit", "insulation", "transformer", "generator", "loto",
        "rubber mat", "shock"
    ],
    "MECHANICAL_SAFETY": [
        "machine guard", "conveyor", "pressure vessel", "compressor", "boiler",
        "maintenance", "moving parts", "vibration", "noise", "hoist", "lift",
        "pulley", "gears"
    ],
    "PPE_COMPLIANCE": [
        "helmet", "safety shoes", "gloves", "goggles", "earplug", "apron",
        "respirator", "harness"
    ],
    "CHEMICAL_SAFETY": [
        "msds", "spillage", "secondary containment", "chemical storage",
        "toxic", "hazardous waste", "eyewash", "safety shower"
    ],
    "STRUCTURAL_SAFETY": [
        "floor", "stairs", "railing", "platforms", "roof", "gangway",
        "scaffolding", "load bearing", "stability certificate"
    ],
    "LICENSE_LEGAL": [
        "factory license", "consent to operate", "fire noc", 
        "test report", "renewal", "display of notice", "inspector", "occupier"
    ],
    "OCCUPATIONAL_HEALTH": [
        "manual handling", "excessive weight", "lifting", "carrying",
        "ergonomics", "posture", "repetition", "occupational disease"
    ],
    "HYGIENE_HEALTH": [
        "ventilation", "temperature", "cleanliness", "waste", "effluent",
        "dust", "fume", "humidification", "overcrowding", "lighting",
        "drinking water", "latrine", "urinal", "spittoon"
    ],
    "WELFARE_FACILITIES": [
        "washing facilities", "canteen", "shelter", "rest room", "lunch room",
        "creche", "first aid", "ambulance", "welfare officer"
    ]
}

def get_topic_for_text(text: str):
    text = text.lower()
    scores = {}
    
    for topic, keywords in COMPLIANCE_ONTOLOGY.items():
        score = 0
        for keyword in keywords:
            # Count occurrences for better weighted matching
            count = text.count(keyword)
            if count > 0:
                # Direct match gets priority
                score += count
                # Exact phrase bonus
                if f" {keyword} " in f" {text} ":
                    score += 2
        
        if score > 0:
            scores[topic] = score
            
    if not scores:
        return "GENERAL_SAFETY"
        
    # Pick topic with highest score
    return max(scores, key=scores.get)
