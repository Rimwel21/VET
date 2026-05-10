from app import create_app, db
from sqlalchemy.schema import CreateTable
import os

app = create_app()

def generate_sql_dump():
    """Generates a raw SQL file for the database schema from SQLAlchemy models."""
    with app.app_context():
        # Get all table objects
        tables = db.metadata.sorted_tables
        
        sql_statements = []
        
        # Add basic setup commands
        sql_statements.append("-- VetSync Database Schema Dump")
        sql_statements.append("-- Generated for local PostgreSQL setup\n")
        
        for table in tables:
            # Generate CREATE TABLE statement
            statement = str(CreateTable(table).compile(db.engine))
            sql_statements.append(f"{statement.strip()};")
            
        # Write to file
        output_path = os.path.join(os.getcwd(), 'vetsync_schema.sql')
        with open(output_path, 'w') as f:
            f.write("\n\n".join(sql_statements))
            
        print(f"Success! Schema exported to: {output_path}")

if __name__ == "__main__":
    generate_sql_dump()
