-- Manga Tracker Database Schema
-- Drop database if exists and create fresh
DROP DATABASE IF EXISTS mangataro;
CREATE DATABASE mangataro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mangataro;

-- Table: mangas
-- Stores manga metadata
CREATE TABLE mangas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL,
    cover_image_url TEXT,
    status ENUM('ongoing', 'completed', 'hiatus', 'cancelled', 'unknown') DEFAULT 'unknown',
    description TEXT,
    latest_chapter VARCHAR(100),
    last_checked TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title(255)),
    INDEX idx_status (status),
    INDEX idx_last_checked (last_checked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: scanlators
-- Stores scanlation group information
CREATE TABLE scanlators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: manga_scanlator
-- Many-to-many relationship between mangas and scanlators
CREATE TABLE manga_scanlator (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT NOT NULL,
    scanlator_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE CASCADE,
    UNIQUE KEY unique_manga_scanlator (manga_id, scanlator_id),
    INDEX idx_manga_id (manga_id),
    INDEX idx_scanlator_id (scanlator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: chapters
-- Stores chapter information
CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT NOT NULL,
    scanlator_id INT NOT NULL,
    chapter_number VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    url TEXT NOT NULL,
    release_date TIMESTAMP NULL DEFAULT NULL,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE CASCADE,
    UNIQUE KEY unique_chapter (manga_id, scanlator_id, chapter_number),
    INDEX idx_manga_id (manga_id),
    INDEX idx_scanlator_id (scanlator_id),
    INDEX idx_release_date (release_date),
    INDEX idx_notified (notified)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: scraping_errors
-- Logs scraping errors for debugging
CREATE TABLE scraping_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT,
    scanlator_id INT,
    error_type VARCHAR(100),
    error_message TEXT,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE SET NULL,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE SET NULL,
    INDEX idx_manga_id (manga_id),
    INDEX idx_scanlator_id (scanlator_id),
    INDEX idx_error_type (error_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
