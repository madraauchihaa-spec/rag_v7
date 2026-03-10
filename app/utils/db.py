import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

# Use DATABASE_URL if provided, else construct DSN from individual fields.
# For Neon, DB_SSLMODE=require is critical.
if DATABASE_URL:
    # Ensure sslmode is present in the URL if not already there.
    if "sslmode=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += f"&sslmode={DB_SSLMODE}"
        else:
            DATABASE_URL += f"?sslmode={DB_SSLMODE}"
    DSN = DATABASE_URL
else:
    DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}"

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DSN
            )
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise
    return _pool

def get_db_connection():
    """Returns a connection from the pool and registers the pgvector extension."""
    pool = get_pool()
    conn = pool.getconn()
    register_vector(conn)
    return conn

def release_db_connection(conn):
    """Returns a connection to the pool."""
    pool = get_pool()
    pool.putconn(conn)

def get_raw_connection():
    """Returns a new, non-pooled connection with pgvector registered."""
    try:
        conn = psycopg2.connect(DSN)
        register_vector(conn)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise
