-- Migration: Add NSFW flag to manga
-- Date: 2026-02-13
-- Description: Adds nsfw boolean field to mangas table for content filtering

-- Add nsfw column (default false for all existing manga)
ALTER TABLE mangas ADD COLUMN nsfw TINYINT(1) DEFAULT 0 NOT NULL;

-- Add index for efficient filtering queries
ALTER TABLE mangas ADD INDEX idx_nsfw (nsfw);
