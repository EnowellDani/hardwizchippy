-- HardWizChippy CPU Database Schema
-- Database: hardwizchippy

CREATE DATABASE IF NOT EXISTS hardwizchippy;
USE hardwizchippy;

-- Manufacturers table
CREATE TABLE IF NOT EXISTS manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CPU Families/Series table
CREATE TABLE IF NOT EXISTS cpu_families (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    codename VARCHAR(100),
    generation VARCHAR(50),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

-- Sockets table
CREATE TABLE IF NOT EXISTS sockets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    manufacturer_id INT NOT NULL,
    release_year INT,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

-- Main CPUs table
CREATE TABLE IF NOT EXISTS cpus (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Basic Info
    name VARCHAR(150) NOT NULL UNIQUE,
    manufacturer_id INT NOT NULL,
    family_id INT,
    socket_id INT,

    -- Codename & Generation
    codename VARCHAR(100),
    generation VARCHAR(50),

    -- Core Configuration
    cores INT,
    threads INT,
    p_cores INT NULL,  -- For hybrid architectures (Intel 12th gen+)
    e_cores INT NULL,  -- Efficiency cores

    -- Clock Speeds (in MHz)
    base_clock DECIMAL(6,2),
    boost_clock DECIMAL(6,2),
    p_core_base_clock DECIMAL(6,2) NULL,
    p_core_boost_clock DECIMAL(6,2) NULL,
    e_core_base_clock DECIMAL(6,2) NULL,
    e_core_boost_clock DECIMAL(6,2) NULL,

    -- Cache (in KB)
    l1_cache INT,
    l2_cache INT,
    l3_cache INT,

    -- Power
    tdp INT,  -- Thermal Design Power in Watts
    base_power INT NULL,  -- Base power (Intel)
    max_turbo_power INT NULL,  -- Maximum turbo power

    -- Manufacturing
    process_node VARCHAR(20),  -- e.g., "7nm", "10nm", "Intel 7"
    transistors_million INT,
    die_size_mm2 DECIMAL(6,2),

    -- Memory Support
    memory_type VARCHAR(100),  -- e.g., "DDR4-3200, DDR5-5600"
    memory_channels INT,
    max_memory_gb INT,

    -- Features
    has_integrated_gpu BOOLEAN DEFAULT FALSE,
    integrated_gpu_name VARCHAR(100),
    pcie_version VARCHAR(10),
    pcie_lanes INT,

    -- Release Info
    launch_date DATE,
    launch_msrp DECIMAL(10,2),

    -- Status
    is_released BOOLEAN DEFAULT TRUE,
    is_discontinued BOOLEAN DEFAULT FALSE,

    -- Metadata
    image_url VARCHAR(255),
    techpowerup_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
    FOREIGN KEY (family_id) REFERENCES cpu_families(id),
    FOREIGN KEY (socket_id) REFERENCES sockets(id),

    INDEX idx_manufacturer (manufacturer_id),
    INDEX idx_name (name),
    INDEX idx_cores (cores),
    INDEX idx_launch_date (launch_date)
);

-- Benchmarks table (for future use)
CREATE TABLE IF NOT EXISTS benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    unit VARCHAR(50),
    higher_is_better BOOLEAN DEFAULT TRUE
);

-- CPU Benchmark scores
CREATE TABLE IF NOT EXISTS cpu_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_id INT NOT NULL,
    benchmark_id INT NOT NULL,
    score DECIMAL(12,2),
    FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id),
    UNIQUE KEY unique_cpu_benchmark (cpu_id, benchmark_id)
);

-- Insert default manufacturers
INSERT INTO manufacturers (name) VALUES
    ('AMD'),
    ('Intel')
ON DUPLICATE KEY UPDATE name = name;

-- Insert common sockets
INSERT INTO sockets (name, manufacturer_id, release_year) VALUES
    -- AMD Sockets
    ('AM4', 1, 2016),
    ('AM5', 1, 2022),
    ('TR4', 1, 2017),
    ('sTRX4', 1, 2019),
    ('sWRX8', 1, 2019),
    ('SP3', 1, 2017),
    -- Intel Sockets
    ('LGA 1200', 2, 2020),
    ('LGA 1700', 2, 2021),
    ('LGA 1851', 2, 2024),
    ('LGA 2066', 2, 2017),
    ('LGA 4189', 2, 2021),
    ('LGA 4677', 2, 2023)
ON DUPLICATE KEY UPDATE name = name;

-- Insert sample CPU families
INSERT INTO cpu_families (manufacturer_id, name, codename, generation) VALUES
    -- AMD Families
    (1, 'Ryzen 9', 'Raphael', '7000 Series'),
    (1, 'Ryzen 7', 'Raphael', '7000 Series'),
    (1, 'Ryzen 5', 'Raphael', '7000 Series'),
    (1, 'Ryzen 9', 'Vermeer', '5000 Series'),
    (1, 'Ryzen 7', 'Vermeer', '5000 Series'),
    (1, 'Ryzen 5', 'Vermeer', '5000 Series'),
    -- Intel Families
    (2, 'Core i9', 'Raptor Lake', '13th/14th Gen'),
    (2, 'Core i7', 'Raptor Lake', '13th/14th Gen'),
    (2, 'Core i5', 'Raptor Lake', '13th/14th Gen'),
    (2, 'Core Ultra 9', 'Arrow Lake', '200 Series'),
    (2, 'Core Ultra 7', 'Arrow Lake', '200 Series'),
    (2, 'Core Ultra 5', 'Arrow Lake', '200 Series');

-- Insert some sample CPUs for testing
INSERT INTO cpus (
    name, manufacturer_id, family_id, socket_id, codename, generation,
    cores, threads, p_cores, e_cores, base_clock, boost_clock,
    l1_cache, l2_cache, l3_cache, tdp, process_node,
    memory_type, memory_channels, max_memory_gb,
    has_integrated_gpu, integrated_gpu_name, pcie_version, pcie_lanes,
    launch_date, launch_msrp, is_released
) VALUES
    -- AMD Ryzen 9 7950X
    ('AMD Ryzen 9 7950X', 1, 1, 2, 'Raphael', 'Zen 4',
     16, 32, NULL, NULL, 4500, 5700,
     1024, 16384, 65536, 170, '5nm',
     'DDR5-5200', 2, 128,
     TRUE, 'AMD Radeon Graphics', '5.0', 24,
     '2022-09-27', 699.00, TRUE),

    -- AMD Ryzen 7 7800X3D
    ('AMD Ryzen 7 7800X3D', 1, 2, 2, 'Raphael', 'Zen 4',
     8, 16, NULL, NULL, 4200, 5000,
     512, 8192, 104857, 120, '5nm',
     'DDR5-5200', 2, 128,
     TRUE, 'AMD Radeon Graphics', '5.0', 24,
     '2023-04-06', 449.00, TRUE),

    -- AMD Ryzen 5 7600X
    ('AMD Ryzen 5 7600X', 1, 3, 2, 'Raphael', 'Zen 4',
     6, 12, NULL, NULL, 4700, 5300,
     384, 6144, 32768, 105, '5nm',
     'DDR5-5200', 2, 128,
     TRUE, 'AMD Radeon Graphics', '5.0', 24,
     '2022-09-27', 299.00, TRUE),

    -- AMD Ryzen 9 5950X
    ('AMD Ryzen 9 5950X', 1, 4, 1, 'Vermeer', 'Zen 3',
     16, 32, NULL, NULL, 3400, 4900,
     1024, 8192, 65536, 105, '7nm',
     'DDR4-3200', 2, 128,
     FALSE, NULL, '4.0', 24,
     '2020-11-05', 799.00, TRUE),

    -- Intel Core i9-14900K
    ('Intel Core i9-14900K', 2, 7, 8, 'Raptor Lake Refresh', '14th Gen',
     24, 32, 8, 16, 3200, 6000,
     2176, 32768, 36864, 253, 'Intel 7',
     'DDR4-3200, DDR5-5600', 2, 192,
     TRUE, 'Intel UHD Graphics 770', '5.0', 20,
     '2023-10-17', 589.00, TRUE),

    -- Intel Core i7-14700K
    ('Intel Core i7-14700K', 2, 8, 8, 'Raptor Lake Refresh', '14th Gen',
     20, 28, 8, 12, 3400, 5600,
     1664, 28672, 33792, 253, 'Intel 7',
     'DDR4-3200, DDR5-5600', 2, 192,
     TRUE, 'Intel UHD Graphics 770', '5.0', 20,
     '2023-10-17', 409.00, TRUE),

    -- Intel Core i5-14600K
    ('Intel Core i5-14600K', 2, 9, 8, 'Raptor Lake Refresh', '14th Gen',
     14, 20, 6, 8, 3500, 5300,
     1152, 20480, 24576, 181, 'Intel 7',
     'DDR4-3200, DDR5-5600', 2, 192,
     TRUE, 'Intel UHD Graphics 770', '5.0', 20,
     '2023-10-17', 319.00, TRUE),

    -- Intel Core Ultra 9 285K
    ('Intel Core Ultra 9 285K', 2, 10, 9, 'Arrow Lake', 'Core Ultra 200',
     24, 24, 8, 16, 3700, 5700,
     2176, 40960, 36864, 125, 'Intel 3',
     'DDR5-6400', 2, 192,
     FALSE, NULL, '5.0', 20,
     '2024-10-24', 589.00, TRUE);

-- Insert common benchmarks
INSERT INTO benchmarks (name, description, unit, higher_is_better) VALUES
    ('Cinebench R23 Single', 'Single-threaded CPU rendering test', 'pts', TRUE),
    ('Cinebench R23 Multi', 'Multi-threaded CPU rendering test', 'pts', TRUE),
    ('Geekbench 6 Single', 'Single-core performance benchmark', 'pts', TRUE),
    ('Geekbench 6 Multi', 'Multi-core performance benchmark', 'pts', TRUE),
    ('PassMark Single', 'PassMark single-thread rating', 'pts', TRUE),
    ('PassMark Multi', 'PassMark multi-thread rating', 'pts', TRUE);
