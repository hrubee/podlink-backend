from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)

def run_auto_migration(engine: Engine):
    """
    Automatically adds missing columns to the 'users' table.
    This is a temporary fallback since we don't have Alembic set up yet.
    """
    logger.info("🔄 Checking database schema...")
    
    # List of columns to add if they are missing
    # Format: (column_name, column_type)
    columns = [
        ("location", "TEXT"),
        ("timezone", "TEXT"),
        ("onboarded", "BOOLEAN DEFAULT FALSE"),
        ("topics", "JSON DEFAULT '[]'"),
        ("target_audience", "TEXT"),
        ("language", "TEXT DEFAULT 'English'"),
        ("engagement_style", "JSON DEFAULT '[]'"),
        ("interview_format", "TEXT DEFAULT 'both'"),
        ("episode_length_pref", "TEXT DEFAULT '45-60'"),
        ("content_rating", "TEXT DEFAULT 'clean'"),
        ("fee_expectation", "TEXT DEFAULT 'free'"),
        ("social_links", "JSON DEFAULT '{}'"),
        ("host_details", "JSON DEFAULT '{}'"),
        ("guest_details", "JSON DEFAULT '{}'"),
        ("is_public", "BOOLEAN DEFAULT TRUE"),
        ("is_deleted", "BOOLEAN DEFAULT FALSE"),
        ("deleted_at", "TIMESTAMP"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns:
            try:
                # Postgres 'ADD COLUMN IF NOT EXISTS' is standard
                sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
                conn.execute(text(sql))
                conn.commit()
                # logger.info(f"✅ Ensured column '{col_name}' exists.")
            except Exception as e:
                logger.warning(f"⚠️ Could not add column '{col_name}': {e}")
                conn.rollback()
    
    logger.info("✅ Auto-migration complete.")
