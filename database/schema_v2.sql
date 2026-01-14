-- HardWizChippy CPU Database Schema v2.0
-- Optimized for performance

CREATE DATABASE IF NOT EXISTS hardwizchippy;
USE hardwizchippy;

-- Core tables
CREATE TABLE IF NOT EXISTS manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sockets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    manufacturer_id INT NOT NULL,
    release_year INT,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cpu_families (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    codename VARCHAR(100),
    generation VARCHAR(50),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cpu_features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    category VARCHAR(30) DEFAULT 'instruction',
    description VARCHAR(255)
) ENGINE=InnoDB;

-- Main CPUs table with all fields
CREATE TABLE IF NOT EXISTS cpus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    manufacturer_id INT NOT NULL,
    family_id INT,
    socket_id INT,
    -- Architecture
    microarchitecture VARCHAR(100),
    codename VARCHAR(100),
    core_stepping VARCHAR(50),
    generation VARCHAR(50),
    -- Cores
    cores INT,
    threads INT,
    p_cores INT NULL,
    e_cores INT NULL,
    -- Clock (MHz)
    base_clock INT,
    boost_clock INT,
    p_core_base_clock INT NULL,
    p_core_boost_clock INT NULL,
    e_core_base_clock INT NULL,
    e_core_boost_clock INT NULL,
    -- Multipliers
    multiplier DECIMAL(5,1),
    turbo_multiplier DECIMAL(5,1),
    unlocked_multiplier BOOLEAN DEFAULT FALSE,
    -- Cache (KB)
    l1_cache_instruction INT,
    l1_cache_data INT,
    l1_cache_total INT,
    l2_cache INT,
    l3_cache INT,
    -- Power (Watts)
    tdp INT,
    base_power INT NULL,
    max_turbo_power INT NULL,
    -- Manufacturing
    fab_processor VARCHAR(50),
    fab_details VARCHAR(100),
    process_node VARCHAR(30),
    transistors_million INT,
    die_size_mm2 DECIMAL(8,2),
    cpu_size VARCHAR(50),
    multi_chip_module BOOLEAN DEFAULT FALSE,
    mcm_count INT DEFAULT 1,
    mcm_config VARCHAR(100),
    -- Features
    data_width INT DEFAULT 64,
    scalability VARCHAR(100),
    bus_type VARCHAR(100),
    bus_frequency INT,
    instruction_set VARCHAR(50),
    -- Memory
    memory_type VARCHAR(150),
    memory_bandwidth DECIMAL(8,2),
    memory_channels INT,
    max_memory_gb INT,
    ecc_supported BOOLEAN DEFAULT FALSE,
    -- iGPU
    has_integrated_gpu BOOLEAN DEFAULT FALSE,
    integrated_gpu_name VARCHAR(100),
    graphics_base_freq INT,
    graphics_turbo_freq INT,
    graphics_core_config VARCHAR(100),
    graphics_fp32_tflops DECIMAL(6,3),
    -- PCIe
    pcie_version VARCHAR(10),
    pcie_lanes INT,
    pcie_config VARCHAR(150),
    -- Pricing
    launch_msrp DECIMAL(10,2),
    current_price DECIMAL(10,2),
    price_currency CHAR(3) DEFAULT 'USD',
    price_updated_at TIMESTAMP NULL,
    -- Release
    launch_date DATE,
    launch_date_raw VARCHAR(50),
    is_released BOOLEAN DEFAULT TRUE,
    is_discontinued BOOLEAN DEFAULT FALSE,
    -- URLs
    image_url VARCHAR(500),
    techpowerup_url VARCHAR(500),
    passmark_url VARCHAR(500),
    geekbench_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Foreign Keys
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
    FOREIGN KEY (family_id) REFERENCES cpu_families(id),
    FOREIGN KEY (socket_id) REFERENCES sockets(id),
    -- Indexes
    INDEX idx_name (name),
    INDEX idx_manufacturer (manufacturer_id),
    INDEX idx_socket (socket_id),
    INDEX idx_cores (cores),
    INDEX idx_boost_clock (boost_clock),
    INDEX idx_current_price (current_price),
    INDEX idx_mfg_cores (manufacturer_id, cores),
    FULLTEXT INDEX ft_search (name, codename, microarchitecture)
) ENGINE=InnoDB;

-- Feature mapping
CREATE TABLE IF NOT EXISTS cpu_feature_mapping (
    cpu_id INT NOT NULL,
    feature_id INT NOT NULL,
    PRIMARY KEY (cpu_id, feature_id),
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    FOREIGN KEY (feature_id) REFERENCES cpu_features(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Benchmarks
CREATE TABLE IF NOT EXISTS benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    short_name VARCHAR(30),
    category VARCHAR(30) NOT NULL,
    description TEXT,
    unit VARCHAR(50),
    higher_is_better BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cpu_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    benchmark_id INT NOT NULL,
    score DECIMAL(12,2),
    percentile DECIMAL(5,2),
    source VARCHAR(100),
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id) ON DELETE CASCADE,
    UNIQUE KEY unique_cpu_benchmark (cpu_id, benchmark_id),
    INDEX idx_score (benchmark_id, score DESC)
) ENGINE=InnoDB;

-- Gaming benchmarks
CREATE TABLE IF NOT EXISTS gaming_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    game_name VARCHAR(100) NOT NULL,
    resolution VARCHAR(20) NOT NULL,
    settings VARCHAR(50),
    avg_fps DECIMAL(7,2),
    one_percent_low DECIMAL(7,2),
    point_one_percent_low DECIMAL(7,2),
    gpu_used VARCHAR(100),
    source VARCHAR(100),
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_cpu_game (cpu_id, game_name)
) ENGINE=InnoDB;

-- Price history
CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    source VARCHAR(50) NOT NULL,
    retailer VARCHAR(100),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_cpu_date (cpu_id, recorded_at DESC)
) ENGINE=InnoDB;

-- Scraper progress
CREATE TABLE IF NOT EXISTS scraper_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scraper_name VARCHAR(50) NOT NULL UNIQUE,
    last_item_processed VARCHAR(255),
    total_processed INT DEFAULT 0,
    total_errors INT DEFAULT 0,
    last_run_started TIMESTAMP NULL,
    last_run_completed TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'idle',
    error_message TEXT
) ENGINE=InnoDB;

-- CPU name mappings for cross-source matching
CREATE TABLE IF NOT EXISTS cpu_name_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_name VARCHAR(200) NOT NULL,
    source_id VARCHAR(100),
    match_confidence DECIMAL(4,3),
    is_verified BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY unique_source_mapping (source, source_name)
) ENGINE=InnoDB;

-- Default data
INSERT INTO manufacturers (name) VALUES ('AMD'), ('Intel'), ('VIA') ON DUPLICATE KEY UPDATE name = name;

INSERT INTO benchmarks (name, short_name, category, unit, higher_is_better) VALUES
    ('Cinebench R23 Single', 'CB23 1T', 'cpu_single', 'pts', TRUE),
    ('Cinebench R23 Multi', 'CB23 MT', 'cpu_multi', 'pts', TRUE),
    ('Cinebench R24 Single', 'CB24 1T', 'cpu_single', 'pts', TRUE),
    ('Cinebench R24 Multi', 'CB24 MT', 'cpu_multi', 'pts', TRUE),
    ('Geekbench 6 Single', 'GB6 1C', 'cpu_single', 'pts', TRUE),
    ('Geekbench 6 Multi', 'GB6 MC', 'cpu_multi', 'pts', TRUE),
    ('PassMark Single', 'PM 1T', 'cpu_single', 'pts', TRUE),
    ('PassMark Multi', 'PM MT', 'cpu_multi', 'pts', TRUE),
    ('3DMark CPU Profile', '3DM CPU', 'cpu_multi', 'pts', TRUE),
    ('Handbrake Video Encoding', 'HB Enc', 'encoding', 'fps', TRUE),
    ('7-Zip Compression', '7-Zip', 'compression', 'MIPS', TRUE),
    ('Speedometer 2.1', 'Speedo', 'web', 'runs/min', TRUE)
ON DUPLICATE KEY UPDATE name = name;

INSERT INTO cpu_features (name, category, description) VALUES
    ('SSE4.2', 'instruction', 'Streaming SIMD Extensions 4.2'),
    ('AVX', 'instruction', 'Advanced Vector Extensions'),
    ('AVX2', 'instruction', 'Advanced Vector Extensions 2'),
    ('AVX-512', 'instruction', '512-bit Advanced Vector Extensions'),
    ('AES-NI', 'instruction', 'AES New Instructions'),
    ('VT-x', 'virtualization', 'Intel Virtualization Technology'),
    ('AMD-V', 'virtualization', 'AMD Virtualization'),
    ('SMT', 'other', 'Simultaneous Multi-Threading'),
    ('3D V-Cache', 'other', 'AMD 3D V-Cache Technology')
ON DUPLICATE KEY UPDATE name = name;

INSERT INTO scraper_progress (scraper_name, status) VALUES
    ('techpowerup', 'idle'), ('pcpartpicker', 'idle'),
    ('passmark', 'idle'), ('geekbench', 'idle'),
    ('cinebench', 'idle'), ('tomshardware', 'idle')
ON DUPLICATE KEY UPDATE scraper_name = scraper_name;
