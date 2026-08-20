--  OutfitAR - Schema Database MySQL (Laragon)
--  Sistem Rekomendasi Outfit dengan AR Real-time
-- ============================================================

CREATE DATABASE IF NOT EXISTS outfit_ar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE outfit_ar;
-- ----------------------------------------------------------
-- Tabel: categories (Kategori Produk)
-- ----------------------------------------------------------
CREATE TABLE categories (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(255) NOT NULL UNIQUE,
    parent_id   INT UNSIGNED NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: products (Produk Outfit dari Marketplace)
-- ----------------------------------------------------------
CREATE TABLE products (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_external_id VARCHAR(255) NOT NULL UNIQUE COMMENT 'ID dari Zalora/Shopee',
    name                VARCHAR(500) NOT NULL,
    brand               VARCHAR(200) NULL,
    category_id         INT UNSIGNED NULL,
    color               VARCHAR(100) NULL,
    price               DECIMAL(12, 2) NULL,
    image_url           TEXT NULL,
    product_url         TEXT NULL,
    source_page         TEXT NULL,
    source_platform     ENUM('shopee', 'zalora', 'tokopedia', 'other') DEFAULT 'zalora',
    -- FIX: Menambahkan 'wanitahijab' ke dalam ENUM
    gender              ENUM('pria', 'wanita', 'wanitahijab', 'unisex') DEFAULT 'pria',
    material            VARCHAR(200) NULL,
    style_tags          JSON NULL COMMENT 'Array tag gaya: ["casual", "formal"]',
    feature_vector      JSON NULL COMMENT 'CNN Feature vector dari EfficientNet',
    skin_tone_compat    JSON NULL COMMENT 'Kompatibilitas skin tone [1-5]',
    is_active           TINYINT(1) DEFAULT 1,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_brand (brand),
    INDEX idx_color (color),
    INDEX idx_category (category_id),
    INDEX idx_gender (gender),
    FULLTEXT INDEX ft_name (name)
) ENGINE=INNODB;

-- ----------------------------------------------------------
-- Tabel: users (Pengguna Aplikasi)
-- ----------------------------------------------------------
CREATE TABLE users (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    -- FIX: Diselaraskan dengan tabel products
    gender          ENUM('pria', 'wanita', 'wanitahijab') DEFAULT 'pria',
    skin_tone       TINYINT UNSIGNED NULL COMMENT 'Skala 1-5 (1=sangat terang, 5=gelap)',
    skin_tone_hex   VARCHAR(7) NULL COMMENT 'Hex warna kulit terdeteksi',
    style_pref      JSON NULL COMMENT 'Preferensi gaya pengguna',
    body_type       ENUM('slim', 'regular', 'athletic', 'plus') DEFAULT 'regular',
    profile_image   TEXT NULL,
    is_active       TINYINT(1) DEFAULT 1,
    last_login      TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_skin_tone (skin_tone)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: user_sessions (Session JWT)
-- ----------------------------------------------------------
CREATE TABLE user_sessions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: skin_tone_detections (Log Deteksi Skin Tone)
-- ----------------------------------------------------------
CREATE TABLE skin_tone_detections (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NULL,
    skin_tone_level TINYINT UNSIGNED NOT NULL COMMENT '1-5',
    skin_tone_hex   VARCHAR(7) NOT NULL,
    confidence      FLOAT NOT NULL COMMENT 'Confidence score CNN 0-1',
    image_path      TEXT NULL COMMENT 'Path gambar input',
    feature_vector  JSON NULL COMMENT 'Raw feature vector EfficientNet',
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_detect_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: recommendations (Hasil Rekomendasi KNN)
-- ----------------------------------------------------------
CREATE TABLE recommendations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NULL,
    session_id      VARCHAR(100) NOT NULL COMMENT 'Session tanpa login pun bisa',
    skin_tone_id    INT UNSIGNED NULL,
    outfit_set      JSON NOT NULL COMMENT 'Array product_id yang direkomendasikan',
    knn_scores      JSON NOT NULL COMMENT 'KNN similarity scores',
    diversity_score FLOAT NULL COMMENT 'Gap Diversity score',
    algorithm_ver   VARCHAR(50) DEFAULT 'v1.0',
    is_accepted     TINYINT(1) NULL COMMENT 'Apakah user menerima rekomendasi',
    feedback_score  TINYINT NULL COMMENT '1-5 rating dari user',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rec_user    FOREIGN KEY (user_id)      REFERENCES users(id)                 ON DELETE SET NULL,
    CONSTRAINT fk_rec_detect  FOREIGN KEY (skin_tone_id) REFERENCES skin_tone_detections(id)  ON DELETE SET NULL,
    INDEX idx_session (session_id),
    INDEX idx_user_rec (user_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: ar_sessions (Sesi AR Virtual Try-On)
-- ----------------------------------------------------------
CREATE TABLE ar_sessions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NULL,
    product_id      INT UNSIGNED NOT NULL,
    ar_mode         ENUM('realtime', 'photo') DEFAULT 'realtime',
    mask_image_path TEXT NULL COMMENT 'Path U-Net segmentation mask',
    result_path     TEXT NULL COMMENT 'Path hasil try-on',
    render_time_ms  INT NULL COMMENT 'Waktu render dalam ms',
    is_saved        TINYINT(1) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ar_user    FOREIGN KEY (user_id)    REFERENCES users(id)     ON DELETE SET NULL,
    CONSTRAINT fk_ar_product FOREIGN KEY (product_id) REFERENCES products(id)  ON DELETE CASCADE,
    INDEX idx_ar_user (user_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: outfit_combinations (Kombinasi Outfit Valid)
-- ----------------------------------------------------------
CREATE TABLE outfit_combinations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NULL,
    products        JSON NOT NULL COMMENT 'Array product_id',
    style_category  VARCHAR(100) NULL COMMENT 'casual, formal, sporty, dll',
    skin_tone_range JSON NULL COMMENT 'Range skin tone yang cocok [min, max]',
    color_harmony   VARCHAR(50) NULL COMMENT 'monochromatic, complementary, dll',
    compatibility   FLOAT DEFAULT 1.0 COMMENT 'Skor kompatibilitas 0-1',
    is_curated      TINYINT(1) DEFAULT 0 COMMENT 'Manual kurasi atau AI',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_style (style_category)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Tabel: product_features (Cache Feature Vector CNN)
-- ----------------------------------------------------------
CREATE TABLE product_features (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id      INT UNSIGNED NOT NULL UNIQUE,
    feature_vector  JSON NOT NULL COMMENT '1280-dim EfficientNet-B0 features',
    color_histogram JSON NOT NULL COMMENT 'HSV Color histogram',
    texture_score   FLOAT NULL,
    extracted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version   VARCHAR(50) DEFAULT 'efficientnet-b0',
    CONSTRAINT fk_feat_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Data Seed: Kategori Dasar
-- ----------------------------------------------------------
INSERT INTO categories (name, slug, parent_id) VALUES
('Pakaian Pria',    'pakaian-pria',    NULL),
('Pakaian Wanita',  'pakaian-wanita',  NULL),
('Aksesori',        'aksesori',        NULL),
('Alas Kaki',       'alas-kaki',       NULL);

INSERT INTO categories (name, slug, parent_id) VALUES
('Kemeja Pria',     'kemeja-pria',     1),
('Kaos Pria',       'kaos-pria',       1),
('Celana Pria',     'celana-pria',     1),
('Jaket Pria',      'jaket-pria',      1),
('Celana Pendek',   'celana-pendek',   1),
('Sepatu Pria',     'sepatu-pria',     4),
('Sandal Pria',     'sandal-pria',     4),
('Kaus Kaki',       'kaus-kaki',       4),
('Ikat Pinggang',   'ikat-pinggang',   3),
('Dasi',            'dasi',            3),
('Tas Pria',        'tas-pria',        3),
('Jam Tangan',      'jam-tangan',      3);