# app/ingestion/standard_ingest.py
import os
import sys
import json
import re
import psycopg2
from tqdm import tqdm
from dotenv import load_dotenv

# Add the 'app' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embedding import get_embedding
from utils.ontology import get_topic_for_text
from utils.text_cleaner import clean_text

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def _infer_standard_meta_from_filename(file_path: str):
    """
    Tries to infer:
    - standard_code like 'IS 732' or 'IS 5216'
    - year like 2019
    - title fallback from filename
    """
    base = os.path.basename(file_path).replace(".json", "")
    
    # Improved parsing:
    # First number in filename is usually the IS code
    num_match = re.search(r"(?P<num>\d+)", base)
    # 4-digit number starting with 18, 19, or 20 is the year
    year_match = re.search(r"(?P<year>(18|19|20)\d{2})", base)

    code = f"IS {num_match.group('num')}" if num_match else "IS"
    year = int(year_match.group("year")) if year_match else None
    
    title = base.replace("_", " ").strip()
    return code, year, title


def ingest_standard(file_path: str, applicable_to: str = "All", reset: bool = False):
    if not os.path.exists(file_path):
        print(f"Error: file not found at {file_path}")
        return

    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()

    if reset:
        print("Clearing existing STANDARD data...")
        cursor.execute("TRUNCATE standard_index RESTART IDENTITY")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    standard_code, year, standard_title = _infer_standard_meta_from_filename(file_path)

    print(f"Processing STANDARD: {standard_code}:{year or 'NA'} ({standard_title})")

    # Clause patterns:
    # "4.1.2 Title" or "4.1.2  TITLE" or "4.1.2"
    clause_start = re.compile(r"^(?P<num>\d+(?:\.\d+)*)\s*(?P<title>.*)$")

    # We will chunk by clause number.
    clauses = []
    current = None
    
    current_section_no = None
    current_parent_title = "General"

    pages = data.get("pages", [])
    for page in pages:
        items = page.get("items", [])
        for item in items:
            itype = (item.get("type") or "").lower().strip()
            val = (item.get("value") or "").strip()

            if not val:
                continue
            if itype in {"header", "footer"}:
                continue

            text = clean_text(val)
            if not text:
                continue

            # Attempt clause detection on first line only
            first_line = text.split("\n")[0].strip()
            m = clause_start.match(first_line)

            # Heuristic: only treat as clause if it begins with digit and has a dot pattern or is a standalone clause number
            is_clause_like = bool(m) and first_line[0].isdigit()

            if is_clause_like:
                clause_no = m.group("num")
                # Avoid false positives like "2019" alone
                if len(clause_no) >= 1 and len(clause_no) <= 12 and not clause_no.startswith(str(year or "")):
                    # Store previous
                    if current and current.get("content"):
                        clauses.append(current)

                    raw_title = (m.group("title") or "").strip()
                    clause_title = raw_title if raw_title and len(raw_title) <= 150 else "General"
                    
                    # Update Parent Context
                    # If clause is like "5", "6", etc.
                    if "." not in clause_no:
                        current_section_no = clause_no
                        current_parent_title = clause_title
                    else:
                        # e.g. "5.1" -> section "5"
                        current_section_no = clause_no.split(".")[0]

                    current = {
                        "clause_number": clause_no,
                        "clause_title": clause_title,
                        "section_number": current_section_no,
                        "parent_clause_title": current_parent_title,
                        "content": text
                    }
                    continue

            # Continuation
            if current:
                current["content"] += "\n" + text

    if current and current.get("content"):
        clauses.append(current)

    print(f"Extracted {len(clauses)} potential clauses. Syncing to DB...")

    inserted = 0
    for c in tqdm(clauses, desc=f"Ingesting {standard_code}"):
        content = (c.get("content") or "").strip()

        # Skip tiny noise fragments
        if len(content) < 60:
            continue

        # DUPLICATE CHECK
        cursor.execute(
            """
            SELECT 1 FROM standard_index 
            WHERE standard_code = %s AND year = %s AND clause_number = %s
            """,
            (standard_code, year, c.get("clause_number"))
        )
        if cursor.fetchone():
            continue

        topic = get_topic_for_text(f"{c.get('clause_title','')} {content}")
        
        parent_ctx = f"Section {c.get('section_number')}: {c.get('parent_clause_title','')}"

        search_text = f"""
Standard: {standard_code}:{year or 'NA'} - {standard_title}
Topic: {topic}
Section Context: {parent_ctx}
Clause: {c.get('clause_number')}
Clause Title: {c.get('clause_title')}

{content}
""".strip()

        embedding = get_embedding(search_text)

        cursor.execute(
            """
            INSERT INTO standard_index (
                standard_code, year, standard_title,
                clause_number, clause_title, section_number, parent_clause_title,
                content, applicable_to, industry_applicability, compliance_topic,
                embedding, tsv
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector(%s))
            """,
            (
                standard_code, year, standard_title,
                c.get("clause_number"), c.get("clause_title"), 
                c.get("section_number"), c.get("parent_clause_title"),
                content, applicable_to, "All", topic,
                embedding, search_text
            )
        )
        inserted += 1

    print(f"✅ Sync complete for {standard_code}:{year or 'NA'}. New clauses inserted: {inserted}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STD_DIR = os.path.join(BASE_DIR, "standards_data", "structured")

    if not os.path.exists(STD_DIR):
        print(f"Standards directory not found: {STD_DIR}")
        sys.exit(0)

    json_files = [f for f in os.listdir(STD_DIR) if f.lower().endswith(".json")]
    json_files.sort()

    for fn in json_files:
        fp = os.path.join(STD_DIR, fn)
        ingest_standard(file_path=fp, reset=False)
