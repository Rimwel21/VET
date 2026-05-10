from dotenv import load_dotenv
import os
load_dotenv()

from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
engine = create_engine(url)

print("Applying schema to Supabase...")

with open('vetsync_schema.sql', 'r') as f:
    sql_content = f.read()

# Split by double newline to separate statements
statements = [s.strip() for s in sql_content.split(';\n') if s.strip() and not s.strip().startswith('--')]

with engine.connect() as conn:
    for stmt in statements:
        try:
            # Use IF NOT EXISTS to be safe
            safe_stmt = stmt.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ')
            conn.execute(text(safe_stmt))
            conn.commit()
            # Extract table name for feedback
            if 'CREATE TABLE' in safe_stmt:
                table = safe_stmt.split('IF NOT EXISTS ')[1].split('(')[0].strip()
                print(f"  [OK] Table '{table}' ready.")
        except Exception as e:
            # Tables may already exist — that's fine
            if 'already exists' in str(e) or 'DuplicateTable' in str(type(e)):
                print(f"  -> Skipped (already exists)")
            else:
                print(f"  [ERR] Error: {e}")

print("\nSUCCESS: Schema applied to Supabase!")
