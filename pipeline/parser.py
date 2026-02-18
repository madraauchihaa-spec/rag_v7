# pipeline/parser.py

import re


# ==============================
# LEGAL EXTRACTION (HARDENED)
# ==============================

def extract_legal_reference(text):

    rule_match = re.search(r'\bRule\s+(\d+[A-Z\-]*)\b', text, re.IGNORECASE)
    section_match = re.search(r'\bSection\s+(\d+[A-Z\-]*)\b', text, re.IGNORECASE)
    schedule_match = re.search(r'\bSchedule\s+((?:X{0,3}(?:IX|IV|V?I{0,3}))|\d+)\b', text, re.IGNORECASE)
    act_match = re.search(
        r'(Factories Act(?:,\s*\d{4})?|Gujarat Factories Rules(?:,\s*\d{4})?)',
        text,
        re.IGNORECASE
    )

    return {
        "act": act_match.group(0) if act_match else None,
        "rule": rule_match.group(1) if rule_match else None,
        "section": section_match.group(1) if section_match else None,
        "schedule": schedule_match.group(1) if schedule_match else None
    }


# ==============================
# HELPERS
# ==============================

def clean_cell_text(text):
    text = text.replace("Recommendation ---", "")
    text = text.replace("Recommendations ---", "")
    text = text.replace("**", "")
    return text.strip()


def is_annexure_heading(line):
    return bool(
        re.match(r'^#+\s*\d*\.?\d*\s*Annexure\s*-\s*[A-Z]', line, re.IGNORECASE)
    )


def is_valid_sr_row(line):
    """
    Strict match:
    |  12. | something | something |
    """
    return bool(
        re.match(r'^\|\s*\d+\.\s*\|', line)
    )


def is_spillover_row(line):
    """
    Row that starts with pipe but no sr no
    """
    return bool(
        re.match(r'^\|\s*\|', line)
    )


def extract_plant_area(line):
    """
    Only capture real plant/utility section labels
    """
    clean = line.strip().replace("|", "").strip()

    if re.match(r'^(Plant\s*[–-]\s*\d+)', clean, re.IGNORECASE):
        return clean

    if re.match(r'^(Utility\s*[–-]\s*\d+)', clean, re.IGNORECASE):
        return clean

    if re.match(r'.*Handling Area$', clean, re.IGNORECASE):
        return clean

    return None


# ==============================
# MAIN PARSER
# ==============================

def parse_markdown(content: str, config: dict):

    lines = content.split("\n")

    records = []
    current_annexure = None
    current_heading = None
    current_plant_area = None
    current_record = None

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        # ---- Annexure Detection ----
        if is_annexure_heading(line):
            current_annexure = line.strip()
            continue

        # ---- Main Heading Detection ----
        if line.startswith("#"):
            current_heading = line.replace("#", "").strip()
            continue

        # ---- Plant Area Detection ----
        plant_area_candidate = extract_plant_area(line)
        if plant_area_candidate:
            current_plant_area = plant_area_candidate
            continue

        # ---- Sr No Row ----
        if is_valid_sr_row(line):

            if current_record:
                records.append(current_record)

            # Remove outer pipes and split
            row_content = line.strip("|")
            columns = [c.strip() for c in row_content.split("|")]

            sr_no_raw = columns[0]
            sr_no = int(sr_no_raw.replace(".", "").strip())

            observation = clean_cell_text(columns[1]) if len(columns) > 1 else ""
            recommendation = clean_cell_text(columns[2]) if len(columns) > 2 else ""

            current_record = {
                "report_id": config["report_id"],
                "industry_type": config["industry_type"],
                "mah_status": config["mah_status"],
                "annexure": current_annexure,
                "content_type": "non_compliance",
                "main_heading": current_heading,
                "plant_area": current_plant_area,
                "sr_no": sr_no,
                "checkpoint": None,
                "observation": observation,
                "recommendation": recommendation,
                "legal_reference": {}
            }

            continue

        # ---- Spillover Handling ----
        if current_record and is_spillover_row(line):

            row_content = line.strip("|")
            columns = [c.strip() for c in row_content.split("|")]

            if len(columns) >= 2:
                extra_text = clean_cell_text(columns[1])
                current_record["recommendation"] += " " + extra_text

            continue

    if current_record:
        records.append(current_record)

    # ---- Legal Reference Extraction ----
    for record in records:
        combined = record["observation"] + " " + record["recommendation"]
        record["legal_reference"] = extract_legal_reference(combined)

    return records
