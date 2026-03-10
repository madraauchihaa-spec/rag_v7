# app/ingestion/sar_ingest.py
import os
import sys
import json
import psycopg2
import re
from tqdm import tqdm
from dotenv import load_dotenv

# Add the 'app' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embedding import get_embedding
from utils.ontology import get_topic_for_text

from utils.db import get_raw_connection

load_dotenv()

def get_connection():
    return get_raw_connection()



def format_search_text(record: dict, topic: str) -> str:
    """
    Create enriched searchable text for embedding + FTS.
    """
    observation = record.get("observation", "").strip()
    recommendation = record.get("recommendation", "").strip()

    return f"""
Source: {record.get('report_id', 'Audit Report')}
Topic: {topic}
Plant Area: {record.get("plant_area", "General")}

Observation:
{observation}

Recommendation:
{recommendation}
""".strip()


def ingest_sar(file_path: str, reset: bool = False):
    """
    Ingest SAR structured JSON with pages/items/tables.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()

    if reset:
        print("Clearing existing SAR data (reset=True)...")
        cursor.execute("TRUNCATE sar_index RESTART IDENTITY")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    report_id = os.path.basename(file_path).replace(".json", "").upper()
    print(f"Processing SAR: {report_id}")

    records = []
    pages = data.get("pages", [])

    for page in pages:
        items = page.get("items", [])
        for item in items:
            if item.get("type") == "table":
                rows = item.get("rows", [])
                if not rows: continue

                # Look for header row
                # We normalize headers to find observation and recommendation columns
                header = [str(c).lower().strip() for c in rows[0]]
                
                obs_idx = -1
                rec_idx = -1
                
                for i, h in enumerate(header):
                    if "observation" in h: obs_idx = i
                    if "recommendation" in h: rec_idx = i

                if obs_idx != -1 and rec_idx != -1:
                    # Process data rows
                    for row in rows[1:]:
                        if len(row) <= max(obs_idx, rec_idx): continue
                        
                        obs = str(row[obs_idx]).strip() if row[obs_idx] else ""
                        rec = str(row[rec_idx]).strip() if row[rec_idx] else ""

                        # Skip empty rows or header clones
                        if (len(obs) > 10 or len(rec) > 10) and not obs.lower().startswith("observation"):
                            records.append({
                                "report_id": report_id,
                                "observation": obs,
                                "recommendation": rec,
                                "plant_area": "Audit Area"
                            })

    print(f"Extracted {len(records)} findings. Indexing...")

    inserted = 0
    for record in tqdm(records, desc=f"Ingesting {report_id}"):
        observation = record["observation"]
        recommendation = record["recommendation"]

        # DUPLICATE CHECK
        cursor.execute(
            "SELECT 1 FROM sar_index WHERE report_id = %s AND observation = %s",
            (record["report_id"], observation)
        )
        if cursor.fetchone():
            continue

        # Determine topic
        topic = get_topic_for_text(f"{observation} {recommendation}")
        search_text = format_search_text(record, topic)
        embedding = get_embedding(search_text, is_query=False)

        cursor.execute(
            """
            INSERT INTO sar_index (
                report_id, industry_type, mah_status, plant_area,
                compliance_type, compliance_topic, observation,
                recommendation, search_text, embedding, tsv
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector(%s))
            """,
            (
                record["report_id"], "Chemical/Process", "General", record["plant_area"],
                "Observation", topic, observation, recommendation,
                search_text, embedding, search_text
            )
        )
        inserted += 1

    print(f"✅ Sync complete for {report_id}. New findings inserted: {inserted}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    SAR_DIR = os.path.join(BASE_DIR, "sar_data", "structured")

    if not os.path.exists(SAR_DIR):
        raise RuntimeError(f"SAR directory not found: {SAR_DIR}")

    json_files = [f for f in os.listdir(SAR_DIR) if f.lower().endswith(".json")]
    json_files.sort()

    for fn in json_files:
        fp = os.path.join(SAR_DIR, fn)
        ingest_sar(file_path=fp, reset=False)