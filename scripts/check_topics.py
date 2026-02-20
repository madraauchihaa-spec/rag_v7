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
    
    print("=== ACT INDEX TOPICS ===")
    cur.execute("SELECT section_number, section_title, compliance_topic FROM act_index")
    rows = cur.fetchall()
    
    # Sort by section number (trying to handle 41A etc)
    def sort_key(s):
        import re
        num = re.findall(r'\d+', s['section_number'])
        return int(num[0]) if num else 999
        
    for row in sorted(rows, key=sort_key):
        print(f"Sec {row['section_number']}: {row['section_title']} -> {row['compliance_topic']}")
        
    conn.close()

if __name__ == "__main__":
    check()
