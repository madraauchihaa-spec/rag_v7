import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "app"))

from utils.db import get_db_connection, release_db_connection

def verify():
    print("Connecting to Neon database...")
    try:
        conn = get_db_connection()
        print("✅ Connection successful!")
        
        with conn.cursor() as cursor:
            # Check tables
            tables = ["act_index", "sar_index", "standard_index"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM public.{table}")
                count = cursor.fetchone()[0]
                print(f"✅ Table 'public.{table}' exists and has {count} rows.")
            
            # Run a dummy vector similarity query if tables are not empty
            if count >= 0: # Even if 0, we can check if the extension and column work
                print("Running dummy vector similarity query...")
                cursor.execute("""
                    SELECT id, (embedding <=> %s::vector) as distance
                    FROM standard_index
                    LIMIT 1
                """, ([0.1] * 1024,)) # Assuming 1024 dim
                row = cursor.fetchone()
                print("✅ Vector similarity query executed successfully.")
                
        release_db_connection(conn)
        print("\nAll verifications passed!")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
