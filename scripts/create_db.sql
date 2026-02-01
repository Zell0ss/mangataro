CREATE DATABASE IF NOT EXISTS mangataro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mangataro;

CREATE TABLE mangas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mangataro_id VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    alternative_titles TEXT,
    cover_filename VARCHAR(255),
    mangataro_url VARCHAR(500),
    date_added DATETIME,
    last_checked DATETIME,
    status ENUM('reading', 'completed', 'on_hold', 'plan_to_read') DEFAULT 'reading',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE scanlators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    base_url VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE manga_scanlator (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT NOT NULL,
    scanlator_id INT NOT NULL,
    scanlator_manga_url VARCHAR(500) NOT NULL,
    manually_verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE CASCADE,
    UNIQUE KEY unique_manga_scanlator (manga_id, scanlator_id),
    INDEX idx_manga (manga_id),
    INDEX idx_scanlator (scanlator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT NOT NULL,
    chapter_number VARCHAR(20) NOT NULL,
    chapter_title VARCHAR(255),
    chapter_url VARCHAR(500) NOT NULL,
    published_date DATETIME,
    detected_date DATETIME NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    UNIQUE KEY unique_chapter (manga_scanlator_id, chapter_number),
    INDEX idx_detected (detected_date DESC),
    INDEX idx_read (read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE scraping_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT,
    error_type VARCHAR(50),
    error_message TEXT,
    timestamp DATETIME NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_resolved (resolved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
