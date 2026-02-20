import os
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()

def check():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT section_number, section_title, compliance_topic FROM act_index")
    rows = cur.fetchall()
    
    # Analyze topics
    sections = {}
    for r in rows:
        sn = r['section_number']
        if sn not in sections:
            sections[sn] = r
            
    # Key sections to check
    targets = ["13", "14", "15", "34", "37", "38", "45", "95", "114"]
    print("=== TARGET SECTIONS ANALYSIS ===")
    for t in targets:
        if t in sections:
            r = sections[t]
            print(f"Sec {t}: {r['section_title']} -> {r['compliance_topic']}")
        else:
            print(f"Sec {t}: MISSING")
            
    conn.close()

if __name__ == "__main__":
    check()
