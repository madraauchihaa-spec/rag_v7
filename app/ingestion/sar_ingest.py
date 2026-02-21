# app/ingestion/sar_ingest.py
import json
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add the 'app' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embedding import get_embedding

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


from utils.ontology import get_topic_for_text

def format_search_text(record):
    observation = record.get("observation", "")
    recommendation = record.get("recommendation", "")
    topic = get_topic_for_text(f"{observation} {recommendation}")
    
    return f"""
Topic: {topic}
Industry: {record.get("industry_type")}
MAH Status: {record.get("mah_status")}
Observation: {observation}
Recommendation: {recommendation}
Summary: {observation[:100]}...
"""


def ingest_sar(file_path):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for record in data:
        observation = record.get("observation", "")
        recommendation = record.get("recommendation", "")
        topic = get_topic_for_text(f"{observation} {recommendation}")
        
        search_text = format_search_text(record)
        embedding = get_embedding(search_text)

        cursor.execute("""
            INSERT INTO sar_index (
                report_id,
                industry_type,
                mah_status,
                plant_area,
                compliance_type,
                compliance_topic,
                observation,
                recommendation,
                search_text,
                embedding,
                tsv
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector(%s))
        """, (
            record.get("report_id"),
            record.get("industry_type"),
            record.get("mah_status"),
            record.get("plant_area"),
            record.get("content_type"),
            topic,
            record.get("observation"),
            record.get("recommendation"),
            search_text,
            embedding,
            search_text
        ))

    print("SAR ingestion completed.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    SAR_DATA_DIR = os.path.join(BASE_DIR, "data", "final_structured")
    
    if not os.path.exists(SAR_DATA_DIR):
        SAR_DATA_DIR = os.path.join(BASE_DIR, "sar_pipeline", "data", "final_structured")

    # Clear existing SAR data
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()
    print("Clearing existing SAR data...")
    cursor.execute("TRUNCATE sar_index RESTART IDENTITY")
    cursor.close()
    conn.close()

    if not os.path.exists(SAR_DATA_DIR):
        print(f"Directory not found: {SAR_DATA_DIR}")
    else:
        for filename in os.listdir(SAR_DATA_DIR):
            if filename.endswith("_structured.json"):
                file_path = os.path.join(SAR_DATA_DIR, filename)
                print(f"Ingesting: {filename}")
                ingest_sar(file_path)
        print("All SAR files processed.")
