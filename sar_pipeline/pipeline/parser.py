# pipeline/parser.py

import re
from .config import ANNEXURE_TYPE_MAP


def extract_legal_reference(text):

    rule_match = re.search(r'\bRule\s+(\d+[A-Z\-]*)\b', text, re.IGNORECASE)
    section_match = re.search(r'\bSection\s+(\d+[A-Z\-]*)\b', text, re.IGNORECASE)
    schedule_match = re.search(
        r'\bSchedule\s+((?:X{0,3}(?:IX|IV|V?I{0,3}))|\d+)\b',
        text,
        re.IGNORECASE
    )
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


def normalize_annexure(line):
    match = re.search(r'Annexure\s*-\s*([A-Z])', line, re.IGNORECASE)
    if match:
        return f"Annexure {match.group(1).upper()}"
    return None


def clean_text(text):
    text = text.replace("**", "").strip()
    return text if text else None


def is_valid_sr_row(line):
    return bool(re.match(r'^\|\s*\d+\.\s*\|', line))


def is_spillover_row(line):
    return bool(re.match(r'^\|\s*\|', line))


def extract_plant_area(line):
    clean = line.strip().replace("|", "").strip()

    if re.match(r'^(Plant\s*[–-]\s*\d+)', clean, re.IGNORECASE):
        return clean

    if re.match(r'^(Utility\s*[–-]\s*\d+)', clean, re.IGNORECASE):
        return clean

    if re.match(r'.*Handling Area$', clean, re.IGNORECASE):
        return clean

    return None


# ==============================
# MAIN PARSER WITH SR ISOLATION
# ==============================

def parse_markdown(content: str, config: dict):

    lines = content.split("\n")

    records = []
    current_annexure = None
    current_content_type = None
    current_heading = None
    current_plant_area = None
    current_record = None

    sr_seen = set()
    annexure_part_counter = {}

    for raw_line in lines:

        line = raw_line.strip()
        if not line:
            continue

        # ---- Annexure Detection ----
        annexure = normalize_annexure(line)
        if annexure:

            current_annexure = annexure
            annex_letter = annexure.split()[-1]

            current_content_type = ANNEXURE_TYPE_MAP.get(
                annex_letter,
                "non_compliance"
            )

            sr_seen = set()
            annexure_part_counter[annexure] = 1

            continue

        # ---- Heading Detection ----
        if line.startswith("#"):
            current_heading = line.replace("#", "").strip()
            continue

        # ---- Plant Area ----
        plant_area = extract_plant_area(line)
        if plant_area:
            current_plant_area = plant_area
            continue

        # ---- SR Row ----
        if is_valid_sr_row(line):

            row_content = line.strip("|")
            columns = [c.strip() for c in row_content.split("|")]

            sr_no = int(columns[0].replace(".", "").strip())

            # 🔴 SR DUPLICATION DETECTED
            if sr_no in sr_seen:

                base_annexure = current_annexure.split(" - Part")[0]

                annexure_part_counter[base_annexure] += 1
                part_number = annexure_part_counter[base_annexure]

                current_annexure = f"{base_annexure} - Part {part_number}"

                sr_seen = set()

            sr_seen.add(sr_no)

            if current_record:
                records.append(current_record)

            observation = clean_text(columns[1]) if len(columns) > 1 else None
            recommendation = clean_text(columns[2]) if len(columns) > 2 else None

            current_record = {
                "report_id": config["report_id"],
                "industry_type": config["industry_type"],
                "mah_status": config["mah_status"],
                "annexure": current_annexure,
                "content_type": current_content_type,
                "main_heading": current_heading,
                "plant_area": current_plant_area,
                "sr_no": sr_no,
                "checkpoint": None,
                "observation": observation,
                "recommendation": recommendation,
                "legal_reference": {}
            }

            continue

        # ---- Spillover ----
        if current_record and is_spillover_row(line):

            row_content = line.strip("|")
            columns = [c.strip() for c in row_content.split("|")]

            if len(columns) > 1 and columns[1]:
                extra_text = clean_text(columns[1])
                if extra_text:
                    current_record["recommendation"] = (
                        (current_record["recommendation"] or "")
                        + " "
                        + extra_text
                    ).strip()

            continue

    if current_record:
        records.append(current_record)

    # ---- Legal Extraction ----
    for record in records:
        combined = f"{record['observation'] or ''} {record['recommendation'] or ''}"
        record["legal_reference"] = extract_legal_reference(combined)

    return records
