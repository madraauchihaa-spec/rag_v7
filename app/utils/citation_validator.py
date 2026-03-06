import re

def extract_sections(text):
    """Extracts section numbers like 'Section 52' or 'Section 7A'"""
    return re.findall(r"Section\s(\d+[A-Z]?)", text)


def extract_clauses(text):
    """Extracts clause numbers like 'Clause 4.1.2'"""
    return re.findall(r"Clause\s(\d+(\.\d+)+)", text)


def validate_citations(response, act_results, std_results):
    """
    Validates that every Section or Clause cited in the response 
    actually exists in the retrieved context.
    """
    valid_sections = [str(r.get("section_number")) for r in act_results if r.get("section_number")]

    valid_clauses = []
    for r in std_results:
        if "clauses" in r:
            valid_clauses.extend(r["clauses"])
        elif "clause_number" in r:
            valid_clauses.append(r["clause_number"])

    sections = extract_sections(response)
    clauses = extract_clauses(response)

    invalid = []

    for s in sections:
        if s not in valid_sections:
            invalid.append(f"Section {s}")

    for c, _ in clauses:
        if c not in valid_clauses:
            invalid.append(f"Clause {c}")

    return invalid
