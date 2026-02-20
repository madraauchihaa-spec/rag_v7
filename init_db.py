import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


def create_database():
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Database '{DB_NAME}' created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists.")

    cursor.close()
    conn.close()


def create_tables():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Enable extensions
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # SAR Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sar_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        report_id TEXT,
        industry_type TEXT,
        mah_status TEXT,
        plant_area TEXT,
        compliance_type TEXT,
        compliance_topic TEXT,  -- New column for routing
        observation TEXT,
        recommendation TEXT,
        search_text TEXT,
        embedding VECTOR(384),
        tsv tsvector
    );
    """)

    # ACT Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS act_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        act_name TEXT,
        year INT,
        chapter TEXT,
        section_number TEXT,
        section_title TEXT,
        content TEXT,
        applicable_to TEXT,
        industry_applicability TEXT,
        compliance_topic TEXT,  -- New column for routing
        embedding VECTOR(384),
        tsv tsvector
    );
    """)

    # Indexes
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS sar_embedding_idx
    ON sar_index
    USING ivfflat (embedding vector_cosine_ops);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS act_embedding_idx
    ON act_index
    USING ivfflat (embedding vector_cosine_ops);
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

    print("Tables and indexes created successfully.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_database()
    create_tables()
