# app/ingestion/act_ingest.py
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

from utils.db import get_raw_connection

load_dotenv()

def ingest_act(file_path: str, applicable_to: str = "All", reset: bool = False):
    """
    Ingests Act data from the new 'pages' -> 'items' JSON structure.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    conn = get_raw_connection()
    conn.autocommit = True
    cursor = conn.cursor()


    if reset:
        print("Clearing existing Act data...")
        cursor.execute("TRUNCATE act_index RESTART IDENTITY")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    act_name = os.path.basename(file_path).replace(".json", "").title()
    year_match = re.search(r"\b(18|19|20)\d{2}\b", act_name)
    year = int(year_match.group()) if year_match else 1948

    print(f"Processing: {act_name}")

    current_chapter = "General"
    sections = []
    current_section = None

    # Matches "29. Title" or "**29. Title**"
    section_pattern = re.compile(r"^\*?\*?(\d+[A-Z]?)\.\s*(.*?)(?:\*?\*?|$)", re.IGNORECASE)
    chapter_pattern = re.compile(r"^CHAPTER\s+([IVXLCDM\d]+)", re.IGNORECASE)

    pages = data.get("pages", [])
    for page in pages:
        items = page.get("items", [])
        for item in items:
            text = item.get("value", "").strip()
            if not text:
                continue

            # Check for Chapter transitions
            if "CHAPTER" in text.upper()[:15]:
                chap_match = chapter_pattern.match(text)
                if chap_match:
                    current_chapter = text
                    continue

            # Check for Section Start
            sec_match = section_pattern.match(text)
            if sec_match:
                # Store the previous one
                if current_section:
                    sections.append(current_section)
                
                sec_no = sec_match.group(1)
                sec_title = sec_match.group(2).split("\n")[0].strip()
                current_section = {
                    "number": sec_no,
                    "title": sec_title or "Untitled",
                    "content": text,
                    "chapter": current_chapter
                }
            elif current_section:
                # Add continuation text to current section
                current_section["content"] += "\n" + text

    # Add the final section
    if current_section:
        sections.append(current_section)

    print(f"Extracted {len(sections)} potential sections. Syncing to DB...")
    
    ingested_count = 0
    for sec in tqdm(sections, desc=f"Ingesting {act_name}"):
        content = sec["content"].strip()
        # Filter out very noise/TOC fragments
        if len(content) < 50 and "short title" not in sec["title"].lower():
            continue

        # DUPLICATE CHECK
        cursor.execute(
            "SELECT 1 FROM act_index WHERE act_name = %s AND section_number = %s",
            (act_name, sec["number"])
        )
        if cursor.fetchone():
            continue

        topic = get_topic_for_text(f"{sec['title']} {content}")
        
        search_markdown = f"""Structure: {act_name}
Chapter: {sec['chapter']}
Topic: {topic}
Section: {sec['number']}
Title: {sec['title']}

{content}
""".strip()

        embedding = get_embedding(search_markdown, is_query=False)

        cursor.execute(
            """
            INSERT INTO act_index (
                act_name, year, chapter, section_number, section_title,
                content, applicable_to, industry_applicability, compliance_topic,
                embedding, tsv
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector(%s))
            """,
            (
                act_name, year, sec["chapter"], sec["number"], sec["title"],
                content, applicable_to, "All", topic, embedding, search_markdown
            )
        )
        ingested_count += 1

    print(f"✅ Sync complete for {act_name}. New sections ingested: {ingested_count}.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ACT_DIR = os.path.join(BASE_DIR, "act_data", "structured")
    
    if os.path.exists(ACT_DIR):
        files = [f for f in os.listdir(ACT_DIR) if f.endswith(".json")]
        files.sort()
        for f in files:
            ingest_act(os.path.join(ACT_DIR, f), reset=False)
    else:
        print(f"Directory not found: {ACT_DIR}")