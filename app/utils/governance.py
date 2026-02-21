# app/utils/governance.py
import re

GENERAL_SECTIONS = ["7A", "7B", "87", "41B"]

OVERREACH_PHRASES = [
    "general duty",
    "indirectly relates",
    "can be extrapolated",
    "framework for"
]

def filter_general_sections(sections):
    specific = []
    general = []
    
    for s in sections:
        if str(s.get("section_number")) in GENERAL_SECTIONS:
            general.append(s)
        else:
            specific.append(s)
    
    # If specific sections exist, drop general ones
    if specific:
        return specific
    
    # If no specific sections found, allow general as fallback
    return general

def detect_overreach(response):
    response_lower = response.lower()
    return any(phrase in response_lower for phrase in OVERREACH_PHRASES)
