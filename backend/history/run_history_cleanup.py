#!/usr/bin/env python3
"""
Temporary script to clean up duplicate video entries from history database.
Keeps only the most recent entry for each unique video_id.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "history.db"

def cleanup_history():
    """Remove duplicate entries, keeping only the most recent for each video_id"""

    # Backup the database first
    backup_path = DB_PATH.with_suffix('.db.backup')
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Created backup: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count current entries
    cursor.execute("SELECT COUNT(*) FROM history")
    total_before = cursor.fetchone()[0]
    print(f"\n📊 Total entries before cleanup: {total_before}")

    # Count duplicates
    cursor.execute("""
        SELECT video_id, COUNT(*) as count
        FROM history
        GROUP BY video_id
        HAVING count > 1
    """)
    duplicates = cursor.fetchall()
    print(f"🔍 Found {len(duplicates)} videos with duplicates:")
    for video_id, count in duplicates:
        print(f"   - {video_id}: {count} entries")

    # Create temporary table with unique videos (most recent timestamp)
    cursor.execute("""
        CREATE TEMPORARY TABLE temp_unique_history AS
        SELECT
            MIN(id) as id,
            url,
            video_id,
            title,
            channel,
            duration,
            description,
            thumbnail,
            MAX(timestamp) as timestamp
        FROM history
        GROUP BY video_id
    """)

    # Delete all entries from history
    cursor.execute("DELETE FROM history")

    # Insert back only the unique entries
    cursor.execute("""
        INSERT INTO history (id, url, video_id, title, channel, duration, description, thumbnail, timestamp)
        SELECT id, url, video_id, title, channel, duration, description, thumbnail, timestamp
        FROM temp_unique_history
    """)

    # Drop the temporary table
    cursor.execute("DROP TABLE temp_unique_history")

    conn.commit()

    # Count final entries
    cursor.execute("SELECT COUNT(*) FROM history")
    total_after = cursor.fetchone()[0]

    # Show cleaned up history
    cursor.execute("SELECT video_id, title, timestamp FROM history ORDER BY timestamp DESC LIMIT 10")
    recent = cursor.fetchall()

    conn.close()

    print(f"\n✓ Cleanup complete!")
    print(f"📊 Total entries after cleanup: {total_after}")
    print(f"🗑️  Removed {total_before - total_after} duplicate entries")

    print(f"\n📋 Most recent {len(recent)} videos:")
    for video_id, title, timestamp in recent:
        print(f"   - {title[:50]}... ({video_id}) - {timestamp}")

    print(f"\n💾 Backup saved to: {backup_path}")
    print("   You can restore it if needed by copying it back to history.db")

if __name__ == "__main__":
    try:
        cleanup_history()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
