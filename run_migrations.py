#!/usr/bin/env python3
"""
Run migrations.sql against the database
"""
import os
from sqlalchemy import create_engine, text

# Database connection (same as server.py)
DATABASE_USERNAME = "yl5961"
DATABASE_PASSWRD = "115674"
DATABASE_HOST = "34.139.8.30"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"

def run_migrations():
    """Execute migrations.sql"""
    engine = create_engine(DATABASEURI)
    
    # Read migrations.sql
    migrations_path = os.path.join(os.path.dirname(__file__), 'migrations.sql')
    with open(migrations_path, 'r') as f:
        sql_content = f.read()
    
    # Execute each statement (split by semicolon)
    with engine.connect() as conn:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                try:
                    conn.execute(text(statement))
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    print(f"  Statement: {statement[:100]}...")
        
        conn.commit()
        print("\n✅ Migrations completed!")

if __name__ == "__main__":
    run_migrations()


