from dotenv import load_dotenv
import os
load_dotenv()

from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
print(f"Connecting to: {url[:50]}...")

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("SUCCESS: Connected to Supabase successfully!")
except Exception as e:
    print(f"FAILED: {e}")
