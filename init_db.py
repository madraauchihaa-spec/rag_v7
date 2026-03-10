# init_db.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from utils.db import DSN, get_raw_connection

load_dotenv()

def create_database():
    # Neon usually provides the database pre-created (e.g., 'neondb' or 'db_navi.ai').
    # We skip explicit CREATE DATABASE here as it often requires superuser or different connection on cloud providers.
    print("Cloud database (Neon) should already exist. Skipping CREATE DATABASE.")

def create_tables():
    conn = get_raw_connection()
    conn.autocommit = True
    cursor = conn.cursor()


    # Determine dimension from EMBEDDING_MODEL
    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5").lower()
    if "large" in model_name:
        dim = 1024
    elif "base" in model_name:
        dim = 768
    else:
        dim = 384 # Default for small
    
    print(f"Using vector dimension {dim} for model {model_name}")

    # Enable extensions
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # Drop existing tables to reconfigure dimensions if model changed
    cursor.execute("DROP TABLE IF EXISTS sar_index;")
    cursor.execute("DROP TABLE IF EXISTS act_index;")
    cursor.execute("DROP TABLE IF EXISTS standard_index;")

    # SAR Table
    cursor.execute(f"""
    CREATE TABLE sar_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        report_id TEXT,
        industry_type TEXT,
        mah_status TEXT,
        plant_area TEXT,
        compliance_type TEXT,
        compliance_topic TEXT,
        observation TEXT,
        recommendation TEXT,
        search_text TEXT,
        embedding VECTOR({dim}),
        tsv tsvector
    );
    """)

    # ACT Table
    cursor.execute(f"""
    CREATE TABLE act_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        act_name TEXT,
        year INT,
        chapter TEXT,
        section_number TEXT,
        section_title TEXT,
        content TEXT,
        applicable_to TEXT,
        industry_applicability TEXT,
        compliance_topic TEXT,
        embedding VECTOR({dim}),
        tsv tsvector
    );
    """)

    # STANDARD Table
    cursor.execute(f"""
    CREATE TABLE standard_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        standard_code TEXT,            -- e.g., IS 732
        year INT,                      -- e.g., 2019
        standard_title TEXT,           -- optional if available
        clause_number TEXT,            -- e.g., 4.1.2
        clause_title TEXT,             -- best-effort
        section_number TEXT,           -- e.g., 4 (the top level section)
        parent_clause_title TEXT,      -- title of the top-level section
        content TEXT,
        applicable_to TEXT,
        industry_applicability TEXT,
        compliance_topic TEXT,
        embedding VECTOR({dim}),
        tsv tsvector
    );
    """)

    # Indexes (using HNSW for better performance on Ubuntu/16GB)
    cursor.execute(f"""
    CREATE INDEX sar_embedding_idx ON sar_index USING hnsw (embedding vector_cosine_ops);
    """)
    cursor.execute(f"""
    CREATE INDEX act_embedding_idx ON act_index USING hnsw (embedding vector_cosine_ops);
    """)
    cursor.execute(f"""
    CREATE INDEX standard_embedding_idx ON standard_index USING hnsw (embedding vector_cosine_ops);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS sar_tsv_idx
    ON sar_index
    USING GIN (tsv);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS act_tsv_idx
    ON act_index
    USING GIN (tsv);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS standard_tsv_idx
    ON standard_index
    USING GIN (tsv);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS standard_code_year_idx ON standard_index (standard_code, year);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS standard_section_idx ON standard_index (standard_code, section_number);
    """)

    print("Tables and indexes created successfully.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_database()
    create_tables()
