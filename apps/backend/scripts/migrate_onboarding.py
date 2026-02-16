from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/podcast")

engine = create_engine(DATABASE_URL)

alter_queries = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS location TEXT;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS topics JSONB DEFAULT '[]';",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS target_audience TEXT;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'English';",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS social_links JSONB DEFAULT '{}';",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS host_details JSONB DEFAULT '{}';",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS guest_details JSONB DEFAULT '{}';"
]

with engine.connect() as conn:
    for query in alter_queries:
        try:
            conn.execute(text(query))
            conn.commit()
            print(f"Executed: {query}")
        except Exception as e:
            print(f"Error executing {query}: {e}")

print("Database schema updated successfully.")
