import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT section_number, section_title, compliance_topic FROM act_index")
rows = cur.fetchall()

with open("sections_summary.txt", "w", encoding="utf-8") as f:
    for r in sorted(rows, key=lambda x: x[0]):
        f.write(f"S{r[0]}|{r[1]}|{r[2]}\n")
conn.close()
