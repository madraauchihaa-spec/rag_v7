# act_pipeline/pipeline/act_parser.py

import re
import copy


def extract_penalty_flag(text: str) -> bool:
    keywords = ["punishable", "penalty", "imprisonment", "fine"]
    return any(k in text.lower() for k in keywords)


def extract_references(text: str):
    references = []

    section_refs = re.findall(r'section\s+(\d+[A-Z\-]*)', text, re.IGNORECASE)
    chapter_refs = re.findall(r'chapter\s+([IVXLC]+)', text, re.IGNORECASE)

    for s in section_refs:
        references.append({
            "type": "SECTION",
            "value": s.upper()
        })

    for c in chapter_refs:
        references.append({
            "type": "CHAPTER",
            "value": c.upper()
        })

    return references


def split_large_content(content: str, max_chars=3000):
    if len(content) <= max_chars:
        return [content]

    paragraphs = content.split(". ")
    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += p + ". "
        else:
            chunks.append(current.strip())
            current = p + ". "

    if current:
        chunks.append(current.strip())

    return chunks


def parse_act(content: str):

    lines = content.split("\n")
    documents = []

    current_doc = None
    current_chapter = None
    current_chapter_title = None
    current_scope = "CENTRAL"
    current_type = "ACT_CORE"

    capture_next_line_as_chapter_title = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # ------------------------
        # CHAPTER DETECTION
        # ------------------------
        chapter_match = re.match(
            r'CHAPTER\s+([IVXLC]+)',
            line,
            re.IGNORECASE
        )

        if chapter_match:
            current_chapter = chapter_match.group(1).upper()
            capture_next_line_as_chapter_title = True
            continue

        if capture_next_line_as_chapter_title:
            if not re.match(r'^\d+\.', line):
                current_chapter_title = line.strip()
                capture_next_line_as_chapter_title = False
                continue

        # ------------------------
        # STATE AMENDMENT SWITCH
        # ------------------------
        if "STATE_AMENDMENTS_SECTION" in line or "STATE_AMENDMENT_MARKER" in line:
            current_scope = "STATE"
            current_type = "STATE_AMENDMENT"
            continue

        # ------------------------
        # SECTION DETECTION
        # ------------------------
        section_match = re.match(
            r'^(\d+[A-Z\-]*)\.\s*(.+?)—',
            line
        )

        if section_match:

            if current_doc:
                finalize_and_append(current_doc, documents)

            section_number = section_match.group(1).upper()
            section_title = section_match.group(2).strip()

            current_doc = {
                "document_type": current_type,
                "law_scope": current_scope,
                "act_name": "Factories Act, 1948",
                "chapter_number": current_chapter,
                "chapter_title": current_chapter_title,
                "section_number": section_number,
                "section_title": section_title,
                "citation": f"Section {section_number}, Factories Act, 1948",
                "hierarchy_level": "SECTION",
                "subsections": [],
                "content": "",
                "references": [],
                "contains_penalty": False,
                "source_type": "PRIMARY",
                "embedding_priority": 1
            }

            current_scope = "CENTRAL"
            current_type = "ACT_CORE"
            continue

        # ------------------------
        # SUBSECTION (1)
        # ------------------------
        subsection_match = re.match(r'\((\d+)\)\s*(.*)', line)
        if subsection_match and current_doc:
            sub_no = subsection_match.group(1)

            # Prevent duplicate subsection numbers
            existing = [s for s in current_doc["subsections"]
                        if s.get("number") == sub_no]

            if not existing:
                current_doc["subsections"].append({
                    "type": "subsection",
                    "number": sub_no,
                    "text": subsection_match.group(2)
                })
            continue

        # ------------------------
        # CLAUSE (a)
        # ------------------------
        clause_match = re.match(r'\(([a-zivx]+)\)\s*(.*)', line)
        if clause_match and current_doc:
            current_doc["subsections"].append({
                "type": "clause",
                "number": clause_match.group(1),
                "text": clause_match.group(2)
            })
            continue

        # ------------------------
        # PROVISO
        # ------------------------
        if line.lower().startswith("provided"):
            current_doc["subsections"].append({
                "type": "proviso",
                "text": line
            })
            continue

        # ------------------------
        # EXPLANATION
        # ------------------------
        if line.lower().startswith("explanation"):
            current_doc["subsections"].append({
                "type": "explanation",
                "text": line
            })
            continue

        # ------------------------
        # NORMAL CONTENT
        # ------------------------
        if current_doc:
            current_doc["content"] += line + " "

    if current_doc:
        finalize_and_append(current_doc, documents)

    return documents


def finalize_and_append(doc, documents):

    # Remove amendment bleed from core sections
    doc["content"] = re.sub(
        r'STATE_AMENDMENT_MARKER.*',
        '',
        doc["content"]
    )

    # Fallback: if no content but subsections exist
    if not doc["content"].strip() and doc["subsections"]:
        doc["content"] = " ".join(
            s["text"] for s in doc["subsections"]
        )

    doc["contains_penalty"] = extract_penalty_flag(doc["content"])
    doc["references"] = extract_references(doc["content"])

    chunks = split_large_content(doc["content"])

    for chunk in chunks:
        new_doc = copy.deepcopy(doc)
        new_doc["content"] = chunk.strip()
        documents.append(new_doc)
