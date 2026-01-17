-- =============================================================================
-- HardWizChippy CPU Database Schema v5 - "Triple Threat Merge"
-- =============================================================================
-- Optimized for multi-source data pipeline:
--   Source A: TechPowerUp (Main View + Nerd Specs)
--   Source B: NanoReview/NotebookCheck (Benchmarks + Gaming FPS)
--   Source C: Intel ARK/AMD Official (General Info)
-- 
-- Target: Laragon MySQL (MariaDB compatible)
-- Author: KBitWare Project
-- Date: January 2026
-- =============================================================================

CREATE DATABASE IF NOT EXISTS hardwizchippy 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
USE hardwizchippy;

-- =============================================================================
-- LOOKUP TABLES
-- =============================================================================

DROP TABLE IF EXISTS manufacturers;
CREATE TABLE manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(255),
    website_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

DROP TABLE IF EXISTS sockets;
CREATE TABLE sockets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    manufacturer_id INT,
    release_year INT,
    pin_count INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

DROP TABLE IF EXISTS cpu_families;
CREATE TABLE cpu_families (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_id INT,
    name VARCHAR(100) NOT NULL,
    codename VARCHAR(100),
    generation VARCHAR(50),
    microarchitecture VARCHAR(100),
    release_year INT,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================================
-- MAIN CPU TABLE - "The Big One"
-- =============================================================================
-- Field naming: snake_case, matches JSON export directly
-- NULL strategy: Allow NULLs for graceful degradation when source doesn't have data

DROP TABLE IF EXISTS cpus;
CREATE TABLE cpus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- =========================================================================
    -- SECTION 1: MAIN VIEW POINT (Header Display - TechPowerUp Primary)
    -- "The Big Part" of the app that's always visible
    -- =========================================================================
    name VARCHAR(200) NOT NULL,                          -- Canonical name (unique identifier)
    name_normalized VARCHAR(200),                        -- For fuzzy matching: lowercase, no spaces
    max_frequency_ghz DECIMAL(5,2),                      -- Max turbo/boost frequency
    total_cache_mb DECIMAL(8,2),                         -- Total cache (L1+L2+L3)
    
    -- =========================================================================
    -- SECTION 2: NERD SPECS (TechPowerUp - The "Big Part" Data)
    -- These are what make TechPowerUp unique
    -- =========================================================================
    transistors_million INT,                             -- Transistor count (millions)
    die_size_mm2 DECIMAL(8,2),                           -- Die size in mm²
    is_mcm BOOLEAN DEFAULT FALSE,                        -- Multi-Chip Module?
    mcm_chiplet_count INT,                               -- Number of chiplets/dies
    mcm_config VARCHAR(150),                             -- e.g., "2x CCD + 1x IOD"
    voltage_range VARCHAR(50),                           -- e.g., "0.65V - 1.45V"
    max_voltage DECIMAL(4,2),                            -- Max operating voltage
    min_voltage DECIMAL(4,2),                            -- Min operating voltage
    
    -- =========================================================================
    -- SECTION 3: GENERAL INFORMATION (Intel ARK / AMD Official)
    -- =========================================================================
    manufacturer_id INT,
    family_id INT,
    socket_id INT,
    
    -- Launch & Pricing
    launch_date DATE,                                    -- Official launch date
    launch_quarter VARCHAR(10),                          -- e.g., "Q4'2024" (from ARK)
    launch_msrp DECIMAL(10,2),                           -- Launch price USD
    current_price DECIMAL(10,2),                         -- Current street price
    price_currency VARCHAR(3) DEFAULT 'USD',
    price_updated_at TIMESTAMP NULL,
    
    -- Product Codes
    product_code VARCHAR(50),                            -- e.g., "BX8071513900K"
    ark_id VARCHAR(50),                                  -- Intel ARK product ID
    amd_product_id VARCHAR(50),                          -- AMD product ID
    
    -- Status
    status ENUM('announced', 'launched', 'available', 'eol', 'legacy') DEFAULT 'available',
    is_released BOOLEAN DEFAULT TRUE,
    is_discontinued BOOLEAN DEFAULT FALSE,
    
    -- =========================================================================
    -- SECTION 4: CORE INFORMATION
    -- =========================================================================
    microarchitecture VARCHAR(100),                      -- e.g., "Zen 5", "Lion Cove + Skymont"
    codename VARCHAR(100),                               -- e.g., "Granite Ridge", "Arrow Lake"
    core_stepping VARCHAR(30),                           -- e.g., "B0", "C0"
    generation VARCHAR(50),                              -- e.g., "15th Gen", "Ryzen 9000"
    market_segment ENUM('desktop', 'laptop', 'server', 'workstation', 'mobile', 'embedded') DEFAULT 'desktop',
    
    -- Core Counts
    cores_total INT,                                     -- Total physical cores
    threads_total INT,                                   -- Total threads (with SMT/HT)
    p_cores INT,                                         -- Performance cores (hybrid arch)
    e_cores INT,                                         -- Efficiency cores (hybrid arch)
    lp_cores INT,                                        -- Low-power cores (Intel Arrow Lake+)
    
    -- Frequencies (GHz)
    base_clock_ghz DECIMAL(5,2),                         -- Base frequency
    boost_clock_ghz DECIMAL(5,2),                        -- Max boost/turbo
    p_core_base_ghz DECIMAL(5,2),                        -- P-core base
    p_core_boost_ghz DECIMAL(5,2),                       -- P-core max boost
    e_core_base_ghz DECIMAL(5,2),                        -- E-core base
    e_core_boost_ghz DECIMAL(5,2),                       -- E-core max boost
    all_core_boost_ghz DECIMAL(5,2),                     -- All-core turbo
    
    -- Multipliers
    base_multiplier DECIMAL(5,1),
    turbo_multiplier DECIMAL(5,1),
    is_unlocked BOOLEAN DEFAULT FALSE,                   -- Overclockable (K/X series)
    
    -- =========================================================================
    -- SECTION 5: FEATURES & EXTENSIONS
    -- =========================================================================
    data_width INT DEFAULT 64,                           -- 32/64 bit
    instruction_set VARCHAR(100),                        -- e.g., "x86-64-v4"
    
    -- Extensions (stored as JSON for flexibility)
    cpu_extensions JSON,                                 -- {"AVX-512": true, "AVX2": true, ...}
    security_features JSON,                              -- {"SGX": true, "TDX": false, ...}
    virtualization_features JSON,                        -- {"VT-x": true, "VT-d": true, ...}
    
    -- Scalability
    scalability VARCHAR(20),                             -- "1S", "2S", "4S", "8S"
    numa_nodes INT,
    
    -- =========================================================================
    -- SECTION 6: CACHE HIERARCHY
    -- =========================================================================
    l1_cache_kb INT,                                     -- L1 total per core (KB)
    l1_instruction_kb INT,                               -- L1 instruction cache
    l1_data_kb INT,                                      -- L1 data cache
    l2_cache_kb INT,                                     -- L2 per core (KB)
    l2_cache_total_kb INT,                               -- L2 total (KB)
    l3_cache_mb DECIMAL(6,2),                            -- L3 total (MB)
    l4_cache_mb DECIMAL(6,2),                            -- L4 / eDRAM if present (MB)
    
    -- =========================================================================
    -- SECTION 7: MEMORY CONTROLLER
    -- =========================================================================
    memory_type VARCHAR(100),                            -- e.g., "DDR5-5600, DDR4-3200"
    memory_speed_native VARCHAR(50),                     -- e.g., "DDR5-5600"
    memory_speed_max VARCHAR(50),                        -- e.g., "DDR5-6400 (OC)"
    memory_channels INT,                                 -- Number of channels
    max_memory_gb INT,                                   -- Maximum supported memory
    max_memory_bandwidth_gbs DECIMAL(8,2),               -- Max bandwidth GB/s
    ecc_support BOOLEAN DEFAULT FALSE,
    
    -- =========================================================================
    -- SECTION 8: INTEGRATED GRAPHICS (iGPU)
    -- =========================================================================
    has_igpu BOOLEAN DEFAULT FALSE,
    igpu_name VARCHAR(100),                              -- e.g., "Intel Arc Graphics"
    igpu_architecture VARCHAR(50),                       -- e.g., "Xe-LPG", "RDNA 2"
    igpu_base_mhz INT,
    igpu_boost_mhz INT,
    igpu_execution_units INT,                            -- Intel EU count
    igpu_compute_units INT,                              -- AMD CU count
    igpu_shaders INT,
    igpu_tmus INT,
    igpu_rops INT,
    igpu_fp32_tflops DECIMAL(5,2),
    
    -- =========================================================================
    -- SECTION 9: PCIe & CONNECTIVITY
    -- =========================================================================
    pcie_version VARCHAR(10),                            -- "4.0", "5.0"
    pcie_lanes_total INT,                                -- Total CPU lanes
    pcie_lanes_direct INT,                               -- Direct from CPU
    pcie_config VARCHAR(100),                            -- e.g., "1x16 + 1x4" or "2x8"
    dmi_version VARCHAR(10),                             -- Intel DMI version
    infinity_fabric_version VARCHAR(20),                 -- AMD IF version
    
    -- =========================================================================
    -- SECTION 10: THERMAL & POWER
    -- =========================================================================
    tdp_watts INT,                                       -- Standard TDP
    base_power_watts INT,                                -- Intel PBP / AMD TDP
    max_power_watts INT,                                 -- Intel MTP / AMD PPT
    configurable_tdp_down INT,                           -- Configurable TDP-down
    configurable_tdp_up INT,                             -- Configurable TDP-up
    tjunction_max_c INT,                                 -- Max junction temp
    thermal_solution VARCHAR(100),                       -- Included cooler info
    
    -- =========================================================================
    -- SECTION 11: FABRICATION / PROCESS
    -- =========================================================================
    process_node VARCHAR(50),                            -- e.g., "Intel 7", "TSMC N4"
    process_node_nm DECIMAL(4,1),                        -- Numeric node (nm)
    foundry VARCHAR(50),                                 -- e.g., "TSMC", "Intel", "Samsung"
    fab_details VARCHAR(150),                            -- e.g., "TSMC 4nm FinFET"
    package_type VARCHAR(50),                            -- e.g., "LGA 1700", "AM5"
    package_size VARCHAR(50),                            -- Physical dimensions
    
    -- =========================================================================
    -- SOURCE TRACKING & METADATA
    -- =========================================================================
    -- URLs for data verification
    techpowerup_url VARCHAR(300),
    nanoreview_url VARCHAR(300),
    intel_ark_url VARCHAR(300),
    amd_url VARCHAR(300),
    notebookcheck_url VARCHAR(300),
    image_url VARCHAR(300),
    
    -- Data freshness tracking
    techpowerup_scraped_at TIMESTAMP NULL,
    nanoreview_scraped_at TIMESTAMP NULL,
    ark_scraped_at TIMESTAMP NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Constraints & Indexes
    UNIQUE KEY uk_cpu_name (name),
    INDEX idx_normalized_name (name_normalized),
    INDEX idx_manufacturer (manufacturer_id),
    INDEX idx_socket (socket_id),
    INDEX idx_family (family_id),
    INDEX idx_launch_date (launch_date),
    INDEX idx_cores (cores_total),
    INDEX idx_status (status),
    INDEX idx_segment (market_segment),
    
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE SET NULL,
    FOREIGN KEY (socket_id) REFERENCES sockets(id) ON DELETE SET NULL,
    FOREIGN KEY (family_id) REFERENCES cpu_families(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================================
-- BENCHMARKS TABLE (NanoReview / NotebookCheck / Geekbench)
-- =============================================================================

DROP TABLE IF EXISTS cpu_benchmarks;
CREATE TABLE cpu_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    
    -- =========================================================================
    -- CINEBENCH R23 (Industry Standard)
    -- =========================================================================
    cinebench_r23_single INT,
    cinebench_r23_multi INT,
    cinebench_r23_multi_per_core DECIMAL(6,2),           -- Efficiency metric
    
    -- =========================================================================
    -- CINEBENCH R24 (2024+ Standard)
    -- =========================================================================
    cinebench_r24_single INT,
    cinebench_r24_multi INT,
    
    -- =========================================================================
    -- GEEKBENCH 6 (Cross-platform)
    -- =========================================================================
    geekbench6_single INT,
    geekbench6_multi INT,
    geekbench6_gpu_opencl INT,
    geekbench6_gpu_vulkan INT,
    geekbench6_gpu_metal INT,                            -- Apple only
    
    -- =========================================================================
    -- 3DMARK CPU BENCHMARKS
    -- =========================================================================
    _3dmark_cpu_profile_1t INT,                          -- Single thread
    _3dmark_cpu_profile_2t INT,
    _3dmark_cpu_profile_4t INT,
    _3dmark_cpu_profile_8t INT,
    _3dmark_cpu_profile_16t INT,
    _3dmark_cpu_profile_max INT,                         -- Max threads
    _3dmark_timespy_cpu INT,
    _3dmark_firestrike_physics INT,
    
    -- =========================================================================
    -- PASSMARK
    -- =========================================================================
    passmark_single INT,
    passmark_multi INT,
    passmark_rank INT,                                   -- Overall rank
    
    -- =========================================================================
    -- CONTENT CREATION
    -- =========================================================================
    -- Handbrake Video Encoding (seconds, lower = better)
    handbrake_h264_1080p_sec INT,
    handbrake_h265_4k_sec INT,
    
    -- Blender Rendering (seconds, lower = better)
    blender_classroom_sec INT,
    blender_monster_sec INT,
    blender_bmw_sec INT,
    
    -- V-Ray Benchmark
    vray_cpu_score INT,
    
    -- =========================================================================
    -- PRODUCTIVITY
    -- =========================================================================
    -- 7-Zip (MIPS, higher = better)
    _7zip_compress_mips INT,
    _7zip_decompress_mips INT,
    
    -- Corona Renderer
    corona_rays_per_sec INT,
    
    -- =========================================================================
    -- WEB & GENERAL
    -- =========================================================================
    speedometer_2_score DECIMAL(8,2),
    speedometer_3_score DECIMAL(8,2),
    octane_score INT,
    jetstream_score DECIMAL(8,2),
    
    -- =========================================================================
    -- POWER EFFICIENCY METRICS
    -- =========================================================================
    perf_per_watt_cb23 DECIMAL(6,2),                     -- CB23 Multi / TDP
    perf_per_dollar DECIMAL(6,2),                        -- CB23 Multi / MSRP
    
    -- =========================================================================
    -- METADATA
    -- =========================================================================
    benchmark_date DATE,
    source VARCHAR(100),                                 -- "nanoreview", "notebookcheck", etc.
    source_url VARCHAR(300),
    test_config TEXT,                                    -- JSON of test configuration
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY uk_cpu_benchmark (cpu_id)
) ENGINE=InnoDB;

-- =============================================================================
-- GAMING PERFORMANCE TABLE (NanoReview Aggregate Data)
-- =============================================================================
-- Strategy: Store the "Average of 5 Games" data that NanoReview provides
-- Plus individual game entries when available

DROP TABLE IF EXISTS cpu_gaming_aggregate;
CREATE TABLE cpu_gaming_aggregate (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    
    -- =========================================================================
    -- TEST CONFIGURATION
    -- =========================================================================
    test_resolution VARCHAR(20) NOT NULL,                -- "1080p", "1440p", "4K"
    test_gpu VARCHAR(100),                               -- GPU used for testing
    test_gpu_tier ENUM('high_end', 'mid_range', 'entry') DEFAULT 'high_end',
    graphics_preset VARCHAR(50),                         -- "Ultra", "High", etc.
    
    -- =========================================================================
    -- AGGREGATE METRICS (NanoReview's "5 Games Average")
    -- =========================================================================
    avg_fps DECIMAL(6,1),                                -- Average FPS across 5 games
    fps_1_percent DECIMAL(6,1),                          -- 1% low average
    fps_01_percent DECIMAL(6,1),                         -- 0.1% low average
    
    -- =========================================================================
    -- RELATIVE PERFORMANCE SCORES
    -- =========================================================================
    gaming_score INT,                                    -- NanoReview's gaming score (0-100)
    relative_performance DECIMAL(5,2),                   -- % vs reference CPU
    rank_position INT,                                   -- Position in gaming rankings
    
    -- =========================================================================
    -- METADATA
    -- =========================================================================
    test_date DATE,
    source VARCHAR(50),
    source_url VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY uk_cpu_resolution (cpu_id, test_resolution)
) ENGINE=InnoDB;

-- =============================================================================
-- INDIVIDUAL GAME BENCHMARKS (When available)
-- =============================================================================

DROP TABLE IF EXISTS cpu_gaming_individual;
CREATE TABLE cpu_gaming_individual (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    
    -- Game Info
    game_name VARCHAR(100) NOT NULL,
    game_year INT,                                       -- Year game released
    
    -- Test Config
    resolution VARCHAR(20),
    graphics_preset VARCHAR(50),
    gpu_used VARCHAR(100),
    
    -- Performance
    avg_fps DECIMAL(6,1),
    fps_1_percent DECIMAL(6,1),
    fps_01_percent DECIMAL(6,1),
    min_fps DECIMAL(6,1),
    max_fps DECIMAL(6,1),
    
    -- Metadata
    test_date DATE,
    source VARCHAR(100),
    source_url VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_game (game_name),
    INDEX idx_cpu_game (cpu_id, game_name)
) ENGINE=InnoDB;

-- =============================================================================
-- PRICE HISTORY (For price tracking feature)
-- =============================================================================

DROP TABLE IF EXISTS cpu_price_history;
CREATE TABLE cpu_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    retailer VARCHAR(100),
    retailer_url VARCHAR(300),
    is_sale BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_cpu_date (cpu_id, recorded_at)
) ENGINE=InnoDB;

-- =============================================================================
-- SCRAPER STATE TRACKING (For incremental updates)
-- =============================================================================

DROP TABLE IF EXISTS scraper_state;
CREATE TABLE scraper_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL,                    -- "techpowerup", "nanoreview", etc.
    last_page_scraped INT DEFAULT 0,
    last_cpu_scraped VARCHAR(200),
    last_run_at TIMESTAMP,
    total_cpus_scraped INT DEFAULT 0,
    status ENUM('idle', 'running', 'completed', 'error') DEFAULT 'idle',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_source (source_name)
) ENGINE=InnoDB;

-- =============================================================================
-- FUZZY MATCH CACHE (Speed up repeated lookups)
-- =============================================================================

DROP TABLE IF EXISTS fuzzy_match_cache;
CREATE TABLE fuzzy_match_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(200) NOT NULL,                   -- Name from source site
    source_site VARCHAR(50) NOT NULL,                    -- Which site it came from
    matched_cpu_id INT,                                  -- Matched CPU in our DB
    match_score INT,                                     -- TheFuzz score (0-100)
    is_verified BOOLEAN DEFAULT FALSE,                   -- Manually verified?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (matched_cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY uk_source_match (source_name, source_site),
    INDEX idx_cpu_matches (matched_cpu_id)
) ENGINE=InnoDB;

-- =============================================================================
-- USER FAVORITES (App Feature)
-- =============================================================================

DROP TABLE IF EXISTS user_favorites;
CREATE TABLE user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    cpu_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY uk_device_cpu (device_id, cpu_id)
) ENGINE=InnoDB;

-- =============================================================================
-- DEFAULT DATA INSERTS
-- =============================================================================

INSERT INTO manufacturers (name, website_url) VALUES
    ('Intel', 'https://www.intel.com'),
    ('AMD', 'https://www.amd.com'),
    ('Apple', 'https://www.apple.com'),
    ('Qualcomm', 'https://www.qualcomm.com'),
    ('MediaTek', 'https://www.mediatek.com'),
    ('NVIDIA', 'https://www.nvidia.com'),
    ('ARM', 'https://www.arm.com'),
    ('Samsung', 'https://www.samsung.com'),
    ('VIA', 'https://www.via.com.tw'),
    ('Ampere', 'https://amperecomputing.com'),
    ('Other', NULL)
ON DUPLICATE KEY UPDATE website_url = VALUES(website_url);

INSERT INTO scraper_state (source_name, status) VALUES
    ('techpowerup', 'idle'),
    ('nanoreview', 'idle'),
    ('intel_ark', 'idle'),
    ('amd_official', 'idle'),
    ('notebookcheck', 'idle')
ON DUPLICATE KEY UPDATE status = 'idle';

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

CREATE OR REPLACE VIEW v_cpu_full AS
SELECT 
    c.*,
    m.name AS manufacturer_name,
    m.logo_url AS manufacturer_logo,
    s.name AS socket_name,
    s.pin_count AS socket_pins,
    f.name AS family_name,
    f.codename AS family_codename,
    b.cinebench_r23_single,
    b.cinebench_r23_multi,
    b.cinebench_r24_single,
    b.cinebench_r24_multi,
    b.geekbench6_single,
    b.geekbench6_multi,
    b.passmark_single,
    b.passmark_multi,
    g.avg_fps AS gaming_avg_fps_1080p,
    g.fps_1_percent AS gaming_1p_low_1080p,
    g.gaming_score
FROM cpus c
LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
LEFT JOIN sockets s ON c.socket_id = s.id
LEFT JOIN cpu_families f ON c.family_id = f.id
LEFT JOIN cpu_benchmarks b ON c.id = b.cpu_id
LEFT JOIN cpu_gaming_aggregate g ON c.id = g.cpu_id AND g.test_resolution = '1080p';

-- Modern CPUs view (2020+) - Focus for initial scraping
CREATE OR REPLACE VIEW v_modern_cpus AS
SELECT * FROM v_cpu_full 
WHERE launch_date >= '2020-01-01' OR launch_date IS NULL
ORDER BY launch_date DESC;

-- =============================================================================
-- STORED PROCEDURE: Normalize CPU name for fuzzy matching
-- =============================================================================

DELIMITER //
CREATE PROCEDURE IF NOT EXISTS normalize_cpu_name(IN raw_name VARCHAR(200), OUT normalized VARCHAR(200))
BEGIN
    SET normalized = LOWER(raw_name);
    -- Remove common prefixes
    SET normalized = REPLACE(normalized, 'intel ', '');
    SET normalized = REPLACE(normalized, 'amd ', '');
    SET normalized = REPLACE(normalized, 'apple ', '');
    -- Remove special characters
    SET normalized = REPLACE(normalized, '-', '');
    SET normalized = REPLACE(normalized, '_', '');
    SET normalized = REPLACE(normalized, ' ', '');
    -- Remove common suffixes
    SET normalized = REPLACE(normalized, 'processor', '');
    SET normalized = REPLACE(normalized, 'cpu', '');
END //
DELIMITER ;

-- =============================================================================
-- TRIGGER: Auto-normalize CPU names on insert/update
-- =============================================================================

DELIMITER //
CREATE TRIGGER IF NOT EXISTS trg_cpu_normalize_insert 
BEFORE INSERT ON cpus
FOR EACH ROW
BEGIN
    SET NEW.name_normalized = LOWER(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            NEW.name, 'Intel ', ''), 'AMD ', ''), ' ', ''), '-', ''), 'Processor', '')
    );
END //

CREATE TRIGGER IF NOT EXISTS trg_cpu_normalize_update
BEFORE UPDATE ON cpus
FOR EACH ROW
BEGIN
    IF NEW.name != OLD.name THEN
        SET NEW.name_normalized = LOWER(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                NEW.name, 'Intel ', ''), 'AMD ', ''), ' ', ''), '-', ''), 'Processor', '')
        );
    END IF;
END //
DELIMITER ;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
SELECT 'Schema v5 Triple-Threat created successfully!' AS status;
