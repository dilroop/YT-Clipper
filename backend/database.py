"""
Database module for YTClipper
Handles all database operations for history tracking
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# Get database path from backend/history folder
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "backend" / "history" / "history.db"


def init_database():
    """
    Initialize SQLite database for history tracking
    Creates history table with proper constraints and indices
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create history table with UNIQUE constraint on video_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            video_id TEXT NOT NULL UNIQUE,
            title TEXT,
            channel TEXT,
            duration INTEGER,
            description TEXT,
            thumbnail TEXT,
            view_count INTEGER DEFAULT 1,
            last_viewed DATETIME DEFAULT CURRENT_TIMESTAMP,
            first_viewed DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check if last_viewed column exists before creating index
    cursor.execute("PRAGMA table_info(history)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'last_viewed' in columns:
        # Create index on last_viewed for faster sorting
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_viewed
            ON history(last_viewed DESC)
        """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")


def migrate_database():
    """
    Migrate existing database to new schema
    - Removes duplicate video_ids (keeps most recent)
    - Adds view_count and updates column names
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if migration is needed (check if view_count column exists)
    cursor.execute("PRAGMA table_info(history)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'view_count' not in columns:
        print("🔄 Migrating database to new schema...")

        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE history_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                video_id TEXT NOT NULL UNIQUE,
                title TEXT,
                channel TEXT,
                duration INTEGER,
                description TEXT,
                thumbnail TEXT,
                view_count INTEGER DEFAULT 1,
                last_viewed DATETIME DEFAULT CURRENT_TIMESTAMP,
                first_viewed DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Copy data from old table, removing duplicates (keep most recent)
        # Use GROUP BY to get the latest timestamp for each video_id
        if 'timestamp' in columns:
            cursor.execute("""
                INSERT INTO history_new
                    (url, video_id, title, channel, duration, description, thumbnail,
                     view_count, last_viewed, first_viewed)
                SELECT
                    url, video_id, title, channel, duration, description, thumbnail,
                    COUNT(*) as view_count,
                    MAX(timestamp) as last_viewed,
                    MIN(timestamp) as first_viewed
                FROM history
                GROUP BY video_id
                ORDER BY MAX(timestamp) DESC
            """)
        else:
            # If no timestamp column, just copy unique video_ids
            cursor.execute("""
                INSERT INTO history_new
                    (url, video_id, title, channel, duration, description, thumbnail, view_count)
                SELECT DISTINCT
                    url, video_id, title, channel, duration, description, thumbnail, 1
                FROM history
                GROUP BY video_id
            """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE history")
        cursor.execute("ALTER TABLE history_new RENAME TO history")

        # Create index
        cursor.execute("""
            CREATE INDEX idx_last_viewed ON history(last_viewed DESC)
        """)

        conn.commit()
        print("✅ Database migration completed successfully")
    else:
        print("✅ Database schema is up to date")

    conn.close()


def save_to_history(
    url: str,
    video_id: str,
    title: str,
    channel: str,
    duration: int,
    thumbnail: str,
    description: str = ''
) -> bool:
    """
    Save or update video in history
    - If video_id exists: updates timestamp and increments view_count
    - If new: inserts with view_count = 1

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Try to insert, if video_id already exists, update instead
        # Using UPSERT (INSERT OR REPLACE with conflict handling)
        cursor.execute("""
            INSERT INTO history
                (url, video_id, title, channel, duration, description, thumbnail,
                 view_count, last_viewed, first_viewed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                url = excluded.url,
                title = excluded.title,
                channel = excluded.channel,
                duration = excluded.duration,
                description = excluded.description,
                thumbnail = excluded.thumbnail,
                view_count = history.view_count + 1,
                last_viewed = excluded.last_viewed
        """, (
            url, video_id, title, channel, duration, description, thumbnail,
            datetime.now().isoformat(), datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error saving to history: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_history(limit: int = 50) -> List[Dict]:
    """
    Get history from database, sorted by most recently viewed

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of history entries as dictionaries
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, url, video_id, title, channel, duration,
                description, thumbnail, view_count, last_viewed, first_viewed
            FROM history
            ORDER BY last_viewed DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        print(f"❌ Error getting history: {e}")
        return []


def clear_history() -> bool:
    """
    Clear all history entries

    Returns:
        bool: True if cleared successfully, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error clearing history: {e}")
        return False


def delete_history_entry(video_id: str) -> bool:
    """
    Delete a specific history entry by video_id

    Args:
        video_id: YouTube video ID to delete

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE video_id = ?", (video_id,))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return rows_affected > 0

    except Exception as e:
        print(f"❌ Error deleting history entry: {e}")
        return False


def get_video_stats(video_id: str) -> Optional[Dict]:
    """
    Get statistics for a specific video

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with video stats or None if not found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT view_count, last_viewed, first_viewed
            FROM history
            WHERE video_id = ?
        """, (video_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    except Exception as e:
        print(f"❌ Error getting video stats: {e}")
        return None
