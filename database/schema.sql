-- HardWizChippy CPU Database Schema v4
-- Complete schema for comprehensive CPU data
-- ============================================

CREATE DATABASE IF NOT EXISTS hardwizchippy;
USE hardwizchippy;

-- ============================================
-- LOOKUP TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(255),
    website_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sockets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    manufacturer_id INT NOT NULL,
    release_year INT,
    description TEXT,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

CREATE TABLE IF NOT EXISTS cpu_families (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    codename VARCHAR(100),
    generation VARCHAR(50),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

-- ============================================
-- MAIN CPU TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS cpus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- ===========================================
    -- MAIN VIEW (Big header section)
    -- ===========================================
    name VARCHAR(150) NOT NULL UNIQUE,
    max_frequency DECIMAL(6,2),              -- Max turbo/boost (GHz)
    total_cache INT,                         -- Total cache (KB)
    
    -- ===========================================
    -- GENERAL INFORMATION
    -- ===========================================
    manufacturer_id INT NOT NULL,
    family_id INT,
    socket_id INT,
    launch_date DATE,
    launch_msrp DECIMAL(10,2),               -- Launch price USD
    current_price DECIMAL(10,2),             -- Current US price
    price_updated_at TIMESTAMP,
    
    -- Fabrication
    process_node VARCHAR(30),                -- e.g., "7nm", "Intel 7", "TSMC N5"
    fab_details VARCHAR(100),                -- e.g., "TSMC 5nm FinFET"
    transistors_million INT,                 -- Transistor count
    die_size_mm2 DECIMAL(8,2),               -- Die size in mm²
    cpu_package_size VARCHAR(50),            -- Physical package size
    
    -- Power
    tdp INT,                                 -- TDP in Watts
    base_power INT,                          -- Base power (Intel PBP)
    max_turbo_power INT,                     -- Max turbo power (Intel MTP)
    
    -- Multi-chip
    is_mcm BOOLEAN DEFAULT FALSE,            -- Is Multi-Chip Module?
    mcm_chiplet_count INT,                   -- Number of chiplets
    mcm_config VARCHAR(100),                 -- MCM configuration details
    
    -- ===========================================
    -- CORE INFORMATION
    -- ===========================================
    microarchitecture VARCHAR(50),           -- e.g., "Zen 4", "Raptor Lake"
    codename VARCHAR(100),                   -- e.g., "Raphael", "Raptor Lake-S"
    core_stepping VARCHAR(20),               -- e.g., "B0", "C0"
    generation VARCHAR(50),                  -- e.g., "13th Gen", "Ryzen 7000"
    
    -- Core counts
    cores INT,                               -- Total cores
    threads INT,                             -- Total threads
    p_cores INT,                             -- Performance cores (hybrid)
    e_cores INT,                             -- Efficiency cores (hybrid)
    
    -- Frequencies (GHz)
    base_clock DECIMAL(6,2),                 -- Base frequency
    boost_clock DECIMAL(6,2),                -- Boost/Turbo frequency
    p_core_base_clock DECIMAL(6,2),          -- P-core base (hybrid)
    p_core_boost_clock DECIMAL(6,2),         -- P-core boost (hybrid)
    e_core_base_clock DECIMAL(6,2),          -- E-core base (hybrid)
    e_core_boost_clock DECIMAL(6,2),         -- E-core boost (hybrid)
    
    -- Cache (in KB)
    l1_cache_instruction INT,                -- L1 instruction cache
    l1_cache_data INT,                       -- L1 data cache
    l1_cache INT,                            -- L1 total (if not split)
    l2_cache INT,                            -- L2 cache per core
    l2_cache_total INT,                      -- L2 total
    l3_cache INT,                            -- L3 cache total
    
    -- Multipliers
    base_multiplier DECIMAL(6,2),            -- Base multiplier
    turbo_multiplier DECIMAL(6,2),           -- Turbo multiplier
    unlocked_multiplier BOOLEAN DEFAULT FALSE, -- Is overclockable?
    
    -- ===========================================
    -- FEATURES
    -- ===========================================
    data_width INT,                          -- e.g., 64
    scalability VARCHAR(50),                 -- e.g., "1S", "2S", "4S"
    bus_type VARCHAR(50),                    -- e.g., "DMI 4.0", "Infinity Fabric"
    bus_frequency VARCHAR(50),               -- Bus speed
    instruction_set VARCHAR(100),            -- e.g., "x86-64-v4"
    features TEXT,                           -- Comma-separated features (AVX-512, etc.)
    
    -- ===========================================
    -- MEMORY
    -- ===========================================
    memory_type VARCHAR(100),                -- e.g., "DDR5-5600, DDR4-3200"
    memory_bandwidth DECIMAL(10,2),          -- Max bandwidth GB/s
    memory_channels INT,                     -- Number of channels
    max_memory_gb INT,                       -- Maximum memory size
    ecc_support BOOLEAN DEFAULT FALSE,       -- ECC memory support
    
    -- ===========================================
    -- GRAPHICS (Integrated GPU)
    -- ===========================================
    has_integrated_gpu BOOLEAN DEFAULT FALSE,
    integrated_gpu_name VARCHAR(100),        -- e.g., "Intel UHD 770"
    gpu_base_frequency INT,                  -- MHz
    gpu_boost_frequency INT,                 -- MHz
    gpu_execution_units INT,                 -- EU count
    gpu_shaders INT,                         -- Shader count
    gpu_fp32_tflops DECIMAL(6,2),            -- FP32 performance
    
    -- ===========================================
    -- PCI EXPRESS
    -- ===========================================
    pcie_version VARCHAR(10),                -- e.g., "5.0"
    pcie_lanes INT,                          -- Total lanes
    pcie_config VARCHAR(100),                -- e.g., "1x16 or 2x8"
    
    -- ===========================================
    -- STATUS & METADATA
    -- ===========================================
    is_released BOOLEAN DEFAULT TRUE,
    is_discontinued BOOLEAN DEFAULT FALSE,
    image_url VARCHAR(255),
    techpowerup_url VARCHAR(255),
    intel_ark_url VARCHAR(255),
    amd_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
    FOREIGN KEY (family_id) REFERENCES cpu_families(id),
    FOREIGN KEY (socket_id) REFERENCES sockets(id),
    
    -- Indexes
    INDEX idx_manufacturer (manufacturer_id),
    INDEX idx_socket (socket_id),
    INDEX idx_cores (cores),
    INDEX idx_launch_date (launch_date)
);

-- ============================================
-- BENCHMARKS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS cpu_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    
    -- Cinebench R23
    cinebench_r23_single INT,
    cinebench_r23_multi INT,
    
    -- Cinebench R24
    cinebench_r24_single INT,
    cinebench_r24_multi INT,
    
    -- Geekbench 6
    geekbench6_single INT,
    geekbench6_multi INT,
    
    -- 3DMark
    _3dmark_cpu_profile_single INT,
    _3dmark_cpu_profile_max INT,
    _3dmark_timespy_cpu INT,
    
    -- PassMark
    passmark_single INT,
    passmark_multi INT,
    
    -- Video Encoding (Handbrake - time in seconds, lower is better)
    handbrake_h264_1080p INT,
    handbrake_h265_4k INT,
    
    -- 3D Rendering (Blender - time in seconds)
    blender_classroom INT,
    blender_monster INT,
    
    -- File Compression (7-Zip - MIPS score)
    _7zip_compression INT,
    _7zip_decompression INT,
    
    -- Web Browsing
    speedometer_score DECIMAL(8,2),
    
    -- Metadata
    benchmark_date DATE,
    source VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY unique_cpu_benchmark (cpu_id)
);

-- ============================================
-- GAMING PERFORMANCE TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS cpu_gaming_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    game_name VARCHAR(100) NOT NULL,
    
    -- Test configuration
    resolution VARCHAR(20),                  -- e.g., "1080p", "1440p", "4K"
    graphics_preset VARCHAR(50),             -- e.g., "Ultra", "High"
    gpu_used VARCHAR(100),                   -- GPU used in test
    
    -- Performance metrics
    avg_fps DECIMAL(6,2),                    -- Average FPS
    fps_1_percent DECIMAL(6,2),              -- 1% low FPS
    fps_01_percent DECIMAL(6,2),             -- 0.1% low FPS
    min_fps DECIMAL(6,2),                    -- Minimum FPS
    max_fps DECIMAL(6,2),                    -- Maximum FPS
    
    -- Metadata
    test_date DATE,
    source VARCHAR(100),
    source_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_game (game_name),
    INDEX idx_cpu_game (cpu_id, game_name)
);

-- ============================================
-- PRICE HISTORY TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS cpu_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    retailer VARCHAR(100),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    INDEX idx_cpu_date (cpu_id, recorded_at)
);

-- ============================================
-- USER FAVORITES (for app)
-- ============================================

CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    cpu_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    UNIQUE KEY unique_device_cpu (device_id, cpu_id)
);

-- ============================================
-- INSERT DEFAULT MANUFACTURERS
-- ============================================

INSERT IGNORE INTO manufacturers (name) VALUES
    ('Intel'),
    ('AMD'),
    ('Apple'),
    ('Qualcomm'),
    ('MediaTek'),
    ('NVIDIA'),
    ('ARM'),
    ('Samsung'),
    ('VIA'),
    ('Other');
