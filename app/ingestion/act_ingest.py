import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

# Add the 'app' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embedding import get_embedding
from utils.ontology import get_topic_for_text

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def clean_noise(text):
    """
    Remove TOC junk and repetitive index structures.
    """
    import re
    # If text has too many 'Sec X.' or 'XX. Title' in a row, it's likely a TOC
    if len(re.findall(r"\d{1,3}\.", text)) > 5 and len(text) < 2000:
        return ""
    return text

def ingest_act(file_path, applicable_to="All"):
    """
    Ingests Act data from a structured JSON file.
    """
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # CRITICAL: Clear existing data to prevent duplicates
    print("Clearing existing Act data...")
    cursor.execute("TRUNCATE act_index RESTART IDENTITY")

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    act_name = metadata.get("act_name", "Factories Act")
    
    import re
    year_match = re.search(r"\d{4}", act_name)
    year = int(year_match.group()) if year_match else 1948

    documents = data.get("documents", [])
    print(f"Found {len(documents)} document units in {file_path}")

    ingested_count = 0
    for doc in documents:
        section_number = doc.get("section_number", "N/A")
        section_title = doc.get("section_title", "Untitled")
        chapter_title = doc.get("chapter_title", "")
        chapter_number = doc.get("chapter_number", "")
        
        content = clean_noise(doc.get("content", ""))
        subsections_text = ""
        for sub in doc.get("subsections", []):
            subsections_text += f"\n({sub.get('number', '')}) {sub.get('text', '')}"
        
        full_content = (content + subsections_text).strip()
        
        # Skip empty sections (likely suppressed TOC noise)
        if not full_content or len(full_content) < 10:
            if "Short title" not in section_title:
                continue

        # Determine topic
        topic = get_topic_for_text(f"{section_title} {full_content}")
        
        search_text = f"""
Act: {act_name}
Chapter: {chapter_number} - {chapter_title}
Topic: {topic}
Section: {section_number}
Title: {section_title}

{full_content}
"""

        embedding = get_embedding(search_text)

        cursor.execute("""
            INSERT INTO act_index (
                act_name,
                year,
                chapter,
                section_number,
                section_title,
                content,
                applicable_to,
                industry_applicability,
                compliance_topic,
                embedding,
                tsv
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector(%s))
        """, (
            act_name,
            year,
            f"{chapter_number}: {chapter_title}" if chapter_number else None,
            section_number,
            section_title,
            full_content,
            applicable_to,
            "All",
            topic,
            embedding,
            search_text
        ))
        ingested_count += 1

    print(f"Act ingestion completed. Total unique sections: {ingested_count}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Path provided by user: act_pipeline/data/final_structured/factory_act_structured.json
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Check root data folder first
    JSON_PATH = os.path.join(BASE_DIR, "data", "final_structured", "factory_act_structured.json")
    
    if not os.path.exists(JSON_PATH):
        # Fallback to pipeline-specific folder
        JSON_PATH = os.path.join(BASE_DIR, "act_pipeline", "data", "final_structured", "factory_act_structured.json")

    ingest_act(file_path=JSON_PATH)
