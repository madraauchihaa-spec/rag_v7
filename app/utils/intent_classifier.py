# app/utils/intent_classifier.py
from utils.llm_client import generate_response
from utils.ontology import COMPLIANCE_ONTOLOGY

def classify_query_intent(query: str):
    """
    Classifies the user query into a primary compliance topic.
    """
    topics = list(COMPLIANCE_ONTOLOGY.keys())
    
    prompt = f"""
Query: {query}

Assign exactly one category from this list based on the user intent:
{", ".join(topics)}, GENERAL_SAFETY

Topic Descriptions:
- FIRE_SAFETY: Fire detection, extinguishers, exits, drills, flammable materials.
- ELECTRICAL_SAFETY: Cables, earthing, panels, shocks, wiring, mats.
- MECHANICAL_SAFETY: Machine guards, moving parts, hoists, lifts, pressure vessels.
- PPE_COMPLIANCE: Personal protective equipment like goggles, helmets, gloves.
- CHEMICAL_SAFETY: Spillage, hazardous storage, MSDS, safety showers.
- HYGIENE_HEALTH: Ventilation, temperature, cleanliness, lighting, drinking water.
- OCCUPATIONAL_HEALTH: Manual handling, excessive weights, lifting, ergonomics.
- WELFARE_FACILITIES: Canteens, creche, shelters, rest rooms, first aid appliances.
- LICENSE_LEGAL: Renewals, display of notices, penalties, registers.

Rules:
- If the query specifically asks about ventilation, lighting, or temperature, use HYGIENE_HEALTH.
- If the query is about lifting weights or manual handling, use OCCUPATIONAL_HEALTH.
- If it's about canteens or childcare/creche, use WELFARE_FACILITIES.

Response format: Just the category name.

Category:
"""
    response = generate_response(prompt).strip()
    
    # Validation against known topics
    for topic in topics:
        if topic in response:
            return topic
            
    return "GENERAL_SAFETY"
