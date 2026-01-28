-- Temporary SQL script to remove duplicate video entries from history
-- Keeps only the most recent entry for each unique video_id

-- Create a temporary table with unique videos (most recent timestamp)
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
GROUP BY video_id;

-- Delete all entries from history
DELETE FROM history;

-- Insert back only the unique entries
INSERT INTO history (id, url, video_id, title, channel, duration, description, thumbnail, timestamp)
SELECT id, url, video_id, title, channel, duration, description, thumbnail, timestamp
FROM temp_unique_history;

-- Drop the temporary table
DROP TABLE temp_unique_history;

-- Show the cleaned up history
SELECT COUNT(*) as total_unique_videos FROM history;
SELECT video_id, title, timestamp FROM history ORDER BY timestamp DESC;
