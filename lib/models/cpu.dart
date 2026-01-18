/// CPU Model - Schema v5 "Triple Threat Merge"
///
/// Supports data from:
/// - Source A: TechPowerUp (Nerd Specs)
/// - Source B: NanoReview (Benchmarks & Gaming)
/// - Source C: Intel ARK / AMD (General Info)
class Cpu {
  final int id;
  final String name;
  final String? nameNormalized;
  final String? codename;
  final String? generation;
  final int? cores;
  final int? threads;
  final int? pCores;
  final int? eCores;
  final int? lpCores; // Low-power cores (Arrow Lake+)
  final double? baseClock;
  final double? boostClock;
  final double? pCoreBaseClock;
  final double? pCoreBoostClock;
  final double? eCoreBaseClock;
  final double? eCoreBoostClock;
  final double? allCoreBoost;
  final int? l1Cache;
  final int? l2Cache;
  final int? l3Cache;
  final double? l3CacheMb; // L3 in MB for modern CPUs
  final int? tdp;
  final int? basePower;
  final int? maxTurboPower;
  final String? processNode;
  final int? transistorsMillion;
  final double? dieSizeMm2;
  final String? memoryType;
  final int? memoryChannels;
  final int? maxMemoryGb;
  final bool hasIntegratedGpu;
  final String? integratedGpuName;
  final String? pcieVersion;
  final int? pcieLanes;
  final String? launchDate;
  final String? launchQuarter; // e.g., "Q4'2024"
  final double? launchMsrp;
  final bool isReleased;
  final bool isDiscontinued;
  final String? imageUrl;
  final String? techpowerupUrl;
  final String? nanoreviewUrl;
  final String? intelArkUrl;
  final String? manufacturerName;
  final String? manufacturerLogo;
  final String? socketName;
  final int? socketReleaseYear;
  final String? familyName;
  final String? familyCodename;
  final List<CpuBenchmark>? benchmarks;

  // =========================================================================
  // NERD SPECS (TechPowerUp - "The Big Part")
  // =========================================================================
  final bool isMcm; // Multi-Chip Module
  final int? mcmChipletCount;
  final String? mcmConfig; // e.g., "2x CCD + 1x IOD"
  final String? voltageRange; // e.g., "0.65V - 1.45V"
  final double? maxVoltage;
  final double? minVoltage;
  final String? foundry; // TSMC, Intel, Samsung

  // =========================================================================
  // ENHANCED FIELDS
  // =========================================================================
  final double? currentPrice;
  final String? microarchitecture;
  final String? coreStepping;
  final double? multiplier;
  final double? turboMultiplier;
  final bool unlockedMultiplier;
  final int? l1CacheInstruction;
  final int? l1CacheData;
  final String? fabProcessor;
  final int? dataWidth;
  final double? memoryBandwidth;
  final bool eccSupported;
  final int? graphicsBaseFreq;
  final int? graphicsTurboFreq;
  final String? graphicsCoreConfig;
  final String? pcieConfig;
  final String? marketSegment; // desktop, laptop, server, etc.
  final String? status; // announced, launched, available, eol, legacy
  final String? productCode; // Intel/AMD product code

  // =========================================================================
  // BENCHMARKS & GAMING (NanoReview)
  // =========================================================================
  final CpuBenchmarks? structuredBenchmarks;
  final List<GamingBenchmark>? gamingBenchmarks;
  final GamingAggregate? gamingAggregate; // NanoReview's 5-game average

  Cpu({
    required this.id,
    required this.name,
    this.nameNormalized,
    this.codename,
    this.generation,
    this.cores,
    this.threads,
    this.pCores,
    this.eCores,
    this.lpCores,
    this.baseClock,
    this.boostClock,
    this.pCoreBaseClock,
    this.pCoreBoostClock,
    this.eCoreBaseClock,
    this.eCoreBoostClock,
    this.allCoreBoost,
    this.l1Cache,
    this.l2Cache,
    this.l3Cache,
    this.l3CacheMb,
    this.tdp,
    this.basePower,
    this.maxTurboPower,
    this.processNode,
    this.transistorsMillion,
    this.dieSizeMm2,
    this.memoryType,
    this.memoryChannels,
    this.maxMemoryGb,
    this.hasIntegratedGpu = false,
    this.integratedGpuName,
    this.pcieVersion,
    this.pcieLanes,
    this.launchDate,
    this.launchQuarter,
    this.launchMsrp,
    this.isReleased = true,
    this.isDiscontinued = false,
    this.imageUrl,
    this.techpowerupUrl,
    this.nanoreviewUrl,
    this.intelArkUrl,
    this.manufacturerName,
    this.manufacturerLogo,
    this.socketName,
    this.socketReleaseYear,
    this.familyName,
    this.familyCodename,
    this.benchmarks,
    // Nerd Specs
    this.isMcm = false,
    this.mcmChipletCount,
    this.mcmConfig,
    this.voltageRange,
    this.maxVoltage,
    this.minVoltage,
    this.foundry,
    // Enhanced fields
    this.currentPrice,
    this.microarchitecture,
    this.coreStepping,
    this.multiplier,
    this.turboMultiplier,
    this.unlockedMultiplier = false,
    this.l1CacheInstruction,
    this.l1CacheData,
    this.fabProcessor,
    this.dataWidth,
    this.memoryBandwidth,
    this.eccSupported = false,
    this.graphicsBaseFreq,
    this.graphicsTurboFreq,
    this.graphicsCoreConfig,
    this.pcieConfig,
    this.marketSegment,
    this.status,
    this.productCode,
    // Benchmarks & Gaming
    this.structuredBenchmarks,
    this.gamingBenchmarks,
    this.gamingAggregate,
  });

  /// Factory constructor with comprehensive null-safety.
  /// Handles missing data gracefully - the "iJB Secret" approach.
  factory Cpu.fromJson(Map<String, dynamic> json) {
    return Cpu(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? 'Unknown CPU',
      nameNormalized: json['name_normalized'] as String?,
      codename: json['codename'] as String?,
      generation: json['generation'] as String?,
      cores: _parseInt(json['cores']),
      threads: _parseInt(json['threads']),
      pCores: _parseInt(json['p_cores']),
      eCores: _parseInt(json['e_cores']),
      lpCores: _parseInt(json['lp_cores']),
      baseClock: _parseDouble(json['base_clock']),
      boostClock: _parseDouble(json['boost_clock']),
      pCoreBaseClock: _parseDouble(json['p_core_base_clock']),
      pCoreBoostClock: _parseDouble(json['p_core_boost_clock']),
      eCoreBaseClock: _parseDouble(json['e_core_base_clock']),
      eCoreBoostClock: _parseDouble(json['e_core_boost_clock']),
      allCoreBoost: _parseDouble(json['all_core_boost_ghz']),
      l1Cache: _parseInt(json['l1_cache']),
      l2Cache: _parseInt(json['l2_cache']),
      l3Cache: _parseInt(json['l3_cache']),
      l3CacheMb: _parseDouble(json['l3_cache_mb']),
      tdp: _parseInt(json['tdp']),
      basePower: _parseInt(json['base_power']),
      maxTurboPower: _parseInt(json['max_turbo_power']),
      processNode: json['process_node'] as String?,
      transistorsMillion: _parseInt(json['transistors_million']),
      dieSizeMm2: _parseDouble(json['die_size_mm2']),
      memoryType: json['memory_type'] as String?,
      memoryChannels: _parseInt(json['memory_channels']),
      maxMemoryGb: _parseInt(json['max_memory_gb']),
      hasIntegratedGpu: json['has_integrated_gpu'] as bool? ?? false,
      integratedGpuName: json['integrated_gpu_name'] as String?,
      pcieVersion: json['pcie_version'] as String?,
      pcieLanes: _parseInt(json['pcie_lanes']),
      launchDate: json['launch_date'] as String?,
      launchQuarter: json['launch_quarter'] as String?,
      launchMsrp: _parseDouble(json['launch_msrp']),
      isReleased: json['is_released'] as bool? ?? true,
      isDiscontinued: json['is_discontinued'] as bool? ?? false,
      imageUrl: json['image_url'] as String?,
      techpowerupUrl: json['techpowerup_url'] as String?,
      nanoreviewUrl: json['nanoreview_url'] as String?,
      intelArkUrl: json['intel_ark_url'] as String?,
      manufacturerName: json['manufacturer_name'] as String?,
      manufacturerLogo: json['manufacturer_logo'] as String?,
      socketName: json['socket_name'] as String?,
      socketReleaseYear: _parseInt(json['socket_release_year']),
      familyName: json['family_name'] as String?,
      familyCodename: json['family_codename'] as String?,
      benchmarks: _parseBenchmarkList(json['benchmarks']),
      // Nerd Specs (TechPowerUp)
      isMcm: json['is_mcm'] as bool? ?? false,
      mcmChipletCount: _parseInt(json['mcm_chiplet_count']),
      mcmConfig: json['mcm_config'] as String?,
      voltageRange: json['voltage_range'] as String?,
      maxVoltage: _parseDouble(json['max_voltage']),
      minVoltage: _parseDouble(json['min_voltage']),
      foundry: json['foundry'] as String?,
      // Enhanced fields
      currentPrice: _parseDouble(json['current_price']),
      microarchitecture: json['microarchitecture'] as String?,
      coreStepping: json['core_stepping'] as String?,
      multiplier: _parseDouble(json['base_multiplier']),
      turboMultiplier: _parseDouble(json['turbo_multiplier']),
      unlockedMultiplier:
          json['unlocked_multiplier'] as bool? ??
          json['is_unlocked'] as bool? ??
          false,
      l1CacheInstruction: _parseInt(json['l1_cache_instruction']),
      l1CacheData: _parseInt(json['l1_cache_data']),
      fabProcessor: json['fab_processor'] as String?,
      dataWidth: _parseInt(json['data_width']),
      memoryBandwidth: _parseDouble(json['memory_bandwidth']),
      eccSupported:
          json['ecc_supported'] as bool? ??
          json['ecc_support'] as bool? ??
          false,
      graphicsBaseFreq:
          _parseInt(json['graphics_base_freq']) ??
          _parseInt(json['igpu_base_mhz']),
      graphicsTurboFreq:
          _parseInt(json['graphics_turbo_freq']) ??
          _parseInt(json['igpu_boost_mhz']),
      graphicsCoreConfig: json['graphics_core_config'] as String?,
      pcieConfig: json['pcie_config'] as String?,
      marketSegment: json['market_segment'] as String?,
      status: json['status'] as String?,
      productCode: json['product_code'] as String?,
      // Structured Benchmarks (NanoReview)
      structuredBenchmarks: json['structured_benchmarks'] != null
          ? CpuBenchmarks.fromJson(
              json['structured_benchmarks'] as Map<String, dynamic>,
            )
          : null,
      // Gaming benchmarks list
      gamingBenchmarks: _parseGamingList(json['gaming_benchmarks']),
      // Gaming aggregate (NanoReview 5-game average)
      gamingAggregate: json['gaming_aggregate'] != null
          ? GamingAggregate.fromJson(
              json['gaming_aggregate'] as Map<String, dynamic>,
            )
          : _parseGamingAggregateFromList(json['gaming_benchmarks']),
    );
  }

  // =========================================================================
  // HELPER METHODS FOR SAFE PARSING
  // =========================================================================

  /// Safely parse int from various types
  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  /// Safely parse double from various types
  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Parse benchmark list with null safety
  static List<CpuBenchmark>? _parseBenchmarkList(dynamic value) {
    if (value == null) return null;
    if (value is! List) return null;
    try {
      return value
          .map((b) => CpuBenchmark.fromJson(b as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return null;
    }
  }

  /// Parse gaming benchmark list with null safety
  static List<GamingBenchmark>? _parseGamingList(dynamic value) {
    if (value == null) return null;
    if (value is! List) return null;
    try {
      return value
          .map((g) => GamingBenchmark.fromJson(g as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return null;
    }
  }

  /// Extract gaming aggregate from gaming benchmarks list (fallback)
  static GamingAggregate? _parseGamingAggregateFromList(dynamic value) {
    if (value == null) return null;
    if (value is! List || value.isEmpty) return null;
    try {
      // Try to find 1080p entry
      final entry = value.firstWhere(
        (g) => g['resolution'] == '1080p',
        orElse: () => value.first,
      );
      return GamingAggregate.fromJson(entry as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'codename': codename,
      'generation': generation,
      'cores': cores,
      'threads': threads,
      'p_cores': pCores,
      'e_cores': eCores,
      'base_clock': baseClock,
      'boost_clock': boostClock,
      'l1_cache': l1Cache,
      'l2_cache': l2Cache,
      'l3_cache': l3Cache,
      'tdp': tdp,
      'process_node': processNode,
      'has_integrated_gpu': hasIntegratedGpu,
      'integrated_gpu_name': integratedGpuName,
      'launch_date': launchDate,
      'launch_msrp': launchMsrp,
      'manufacturer_name': manufacturerName,
      'socket_name': socketName,
    };
  }

  // Helper methods
  String get formattedBaseClock => baseClock != null
      ? '${(baseClock! / 1000).toStringAsFixed(2)} GHz'
      : 'N/A';

  String get formattedBoostClock => boostClock != null
      ? '${(boostClock! / 1000).toStringAsFixed(2)} GHz'
      : 'N/A';

  String get formattedL3Cache {
    if (l3Cache == null) return 'N/A';
    if (l3Cache! >= 1024) {
      return '${(l3Cache! / 1024).toStringAsFixed(0)} MB';
    }
    return '$l3Cache KB';
  }

  String get coreThreadString {
    if (cores == null) return 'N/A';
    if (threads != null && threads != cores) {
      return '$cores Cores / $threads Threads';
    }
    return '$cores Cores';
  }

  String get hybridCoreString {
    if (pCores != null && eCores != null) {
      return '${pCores}P + ${eCores}E Cores';
    }
    return coreThreadString;
  }

  bool get isHybrid => pCores != null && eCores != null;

  bool get isAmd => manufacturerName?.toLowerCase() == 'amd';

  bool get isIntel => manufacturerName?.toLowerCase() == 'intel';

  // =========================================================================
  // NERD SPECS HELPERS (The "Big Part" Display)
  // =========================================================================

  /// Check if nerd specs data is available
  bool get hasNerdSpecs => transistorsMillion != null || dieSizeMm2 != null;

  /// Formatted transistor count
  String get formattedTransistors {
    if (transistorsMillion == null) return 'N/A';
    if (transistorsMillion! >= 1000) {
      return '${(transistorsMillion! / 1000).toStringAsFixed(1)} Billion';
    }
    return '$transistorsMillion Million';
  }

  /// Formatted die size
  String get formattedDieSize {
    if (dieSizeMm2 == null) return 'N/A';
    return '${dieSizeMm2!.toStringAsFixed(0)} mm²';
  }

  /// MCM display string
  String get mcmDisplay {
    if (!isMcm) return 'Monolithic';
    if (mcmConfig != null && mcmConfig!.isNotEmpty) return mcmConfig!;
    if (mcmChipletCount != null) return '$mcmChipletCount Chiplets';
    return 'Multi-Chip';
  }

  /// Check if benchmarks are available
  bool get hasBenchmarks =>
      structuredBenchmarks != null && structuredBenchmarks!.hasData;

  /// Check if gaming data is available
  bool get hasGamingData =>
      gamingAggregate != null && gamingAggregate!.hasData ||
      (gamingBenchmarks != null && gamingBenchmarks!.isNotEmpty);

  /// Get primary benchmark (Cinebench R23 Multi) for quick comparison
  int? get primaryBenchmark => structuredBenchmarks?.cinebenchR23Multi;

  /// Get gaming score for quick comparison
  int? get primaryGamingScore => gamingAggregate?.gamingScore;
}

class CpuBenchmark {
  final String name;
  final String? unit;
  final bool higherIsBetter;
  final double? score;

  CpuBenchmark({
    required this.name,
    this.unit,
    this.higherIsBetter = true,
    this.score,
  });

  factory CpuBenchmark.fromJson(Map<String, dynamic> json) {
    return CpuBenchmark(
      name: json['name'] as String,
      unit: json['unit'] as String?,
      higherIsBetter: json['higher_is_better'] as bool? ?? true,
      score: (json['score'] as num?)?.toDouble(),
    );
  }
}

class Manufacturer {
  final int id;
  final String name;
  final String? logoUrl;
  final int cpuCount;

  Manufacturer({
    required this.id,
    required this.name,
    this.logoUrl,
    this.cpuCount = 0,
  });

  factory Manufacturer.fromJson(Map<String, dynamic> json) {
    return Manufacturer(
      id: json['id'] as int,
      name: json['name'] as String,
      logoUrl: json['logo_url'] as String?,
      cpuCount: json['cpu_count'] as int? ?? 0,
    );
  }
}

class Socket {
  final int id;
  final String name;
  final int manufacturerId;
  final String? manufacturerName;
  final int? releaseYear;
  final int cpuCount;

  Socket({
    required this.id,
    required this.name,
    required this.manufacturerId,
    this.manufacturerName,
    this.releaseYear,
    this.cpuCount = 0,
  });

  factory Socket.fromJson(Map<String, dynamic> json) {
    return Socket(
      id: json['id'] as int,
      name: json['name'] as String,
      manufacturerId: json['manufacturer_id'] as int,
      manufacturerName: json['manufacturer_name'] as String?,
      releaseYear: json['release_year'] as int?,
      cpuCount: json['cpu_count'] as int? ?? 0,
    );
  }
}

class CpuFamily {
  final int id;
  final String name;
  final int manufacturerId;
  final String? manufacturerName;
  final String? codename;
  final String? generation;
  final int cpuCount;

  CpuFamily({
    required this.id,
    required this.name,
    required this.manufacturerId,
    this.manufacturerName,
    this.codename,
    this.generation,
    this.cpuCount = 0,
  });

  factory CpuFamily.fromJson(Map<String, dynamic> json) {
    return CpuFamily(
      id: json['id'] as int,
      name: json['name'] as String,
      manufacturerId: json['manufacturer_id'] as int,
      manufacturerName: json['manufacturer_name'] as String?,
      codename: json['codename'] as String?,
      generation: json['generation'] as String?,
      cpuCount: json['cpu_count'] as int? ?? 0,
    );
  }
}

class PaginatedResponse<T> {
  final List<T> data;
  final int currentPage;
  final int perPage;
  final int total;
  final int totalPages;

  PaginatedResponse({
    required this.data,
    required this.currentPage,
    required this.perPage,
    required this.total,
    required this.totalPages,
  });

  bool get hasMore => currentPage < totalPages;
}

/// Structured benchmark scores from NanoReview/NotebookCheck
class CpuBenchmarks {
  // Cinebench R23
  final int? cinebenchR23Single;
  final int? cinebenchR23Multi;
  // Cinebench R24
  final int? cinebenchR24Single;
  final int? cinebenchR24Multi;
  // Geekbench 6
  final int? geekbench6Single;
  final int? geekbench6Multi;
  // PassMark
  final int? passmarkSingle;
  final int? passmarkMulti;
  // 3DMark
  final int? threeDMarkTimespyCpu;
  // Content Creation
  final int? handbrakeH264;
  final int? handbrakeH265;
  final int? blenderClassroom;
  // Productivity
  final int? sevenZipCompress;
  final int? sevenZipDecompress;
  // Web
  final double? speedometerScore;

  CpuBenchmarks({
    this.cinebenchR23Single,
    this.cinebenchR23Multi,
    this.cinebenchR24Single,
    this.cinebenchR24Multi,
    this.geekbench6Single,
    this.geekbench6Multi,
    this.passmarkSingle,
    this.passmarkMulti,
    this.threeDMarkTimespyCpu,
    this.handbrakeH264,
    this.handbrakeH265,
    this.blenderClassroom,
    this.sevenZipCompress,
    this.sevenZipDecompress,
    this.speedometerScore,
  });

  /// Null-safe factory that handles nested structure from export
  factory CpuBenchmarks.fromJson(Map<String, dynamic> json) {
    // Handle nested structure: {"cinebench_r23": {"single": 123, "multi": 456}}
    final cb23 = json['cinebench_r23'] as Map<String, dynamic>?;
    final cb24 = json['cinebench_r24'] as Map<String, dynamic>?;
    final gb6 = json['geekbench6'] as Map<String, dynamic>?;
    final pm = json['passmark'] as Map<String, dynamic>?;
    final dm = json['3dmark'] as Map<String, dynamic>?;
    final cc = json['content_creation'] as Map<String, dynamic>?;
    final prod = json['productivity'] as Map<String, dynamic>?;

    return CpuBenchmarks(
      // Try nested first, then flat
      cinebenchR23Single:
          _parseInt(cb23?['single']) ?? _parseInt(json['cinebench_r23_single']),
      cinebenchR23Multi:
          _parseInt(cb23?['multi']) ?? _parseInt(json['cinebench_r23_multi']),
      cinebenchR24Single:
          _parseInt(cb24?['single']) ?? _parseInt(json['cinebench_r24_single']),
      cinebenchR24Multi:
          _parseInt(cb24?['multi']) ?? _parseInt(json['cinebench_r24_multi']),
      geekbench6Single:
          _parseInt(gb6?['single']) ?? _parseInt(json['geekbench6_single']),
      geekbench6Multi:
          _parseInt(gb6?['multi']) ?? _parseInt(json['geekbench6_multi']),
      passmarkSingle:
          _parseInt(pm?['single']) ?? _parseInt(json['passmark_single']),
      passmarkMulti:
          _parseInt(pm?['multi']) ?? _parseInt(json['passmark_multi']),
      threeDMarkTimespyCpu:
          _parseInt(dm?['timespy_cpu']) ??
          _parseInt(json['3dmark']) ??
          _parseInt(json['timespy_cpu']),
      handbrakeH264:
          _parseInt(cc?['handbrake_h264']) ??
          _parseInt(json['handbrake_video']?.toInt()),
      handbrakeH265: _parseInt(cc?['handbrake_h265']),
      blenderClassroom: _parseInt(cc?['blender_classroom']),
      sevenZipCompress:
          _parseInt(prod?['zip_compress']) ??
          _parseInt(json['7zip_compression']),
      sevenZipDecompress: _parseInt(prod?['zip_decompress']),
      speedometerScore: _parseDouble(json['speedometer_web']),
    );
  }

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Check if any benchmark data exists
  bool get isEmpty =>
      cinebenchR23Single == null &&
      cinebenchR23Multi == null &&
      cinebenchR24Single == null &&
      cinebenchR24Multi == null &&
      geekbench6Single == null &&
      geekbench6Multi == null;

  /// Check if benchmarks have data
  bool get hasData => !isEmpty;
}

/// Gaming benchmark data for a single game
class GamingBenchmark {
  final String gameName;
  final String resolution;
  final String? settings;
  final double avgFps;
  final double? onePercentLow;
  final double? pointOnePercentLow;
  final String? gpuUsed;

  GamingBenchmark({
    required this.gameName,
    required this.resolution,
    this.settings,
    required this.avgFps,
    this.onePercentLow,
    this.pointOnePercentLow,
    this.gpuUsed,
  });

  factory GamingBenchmark.fromJson(Map<String, dynamic> json) {
    return GamingBenchmark(
      gameName:
          json['game'] as String? ??
          json['game_name'] as String? ??
          'Unknown Game',
      resolution: json['resolution'] as String? ?? '1080p',
      settings: json['settings'] as String?,
      avgFps: _parseDouble(json['avg_fps']) ?? 0.0,
      onePercentLow:
          _parseDouble(json['1_low']) ?? _parseDouble(json['fps_1_percent']),
      pointOnePercentLow:
          _parseDouble(json['0.1_low']) ?? _parseDouble(json['fps_01_percent']),
      gpuUsed: json['gpu'] as String? ?? json['gpu_used'] as String?,
    );
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }
}

/// Gaming aggregate data from NanoReview (5-game average)
/// This is the "Gaming FPS" section for modern CPUs
class GamingAggregate {
  final String resolution;
  final String? gpuUsed;
  final double? avgFps;
  final double? fps1Percent;
  final double? fps01Percent;
  final int? gamingScore; // NanoReview's gaming score (0-100)

  GamingAggregate({
    required this.resolution,
    this.gpuUsed,
    this.avgFps,
    this.fps1Percent,
    this.fps01Percent,
    this.gamingScore,
  });

  factory GamingAggregate.fromJson(Map<String, dynamic> json) {
    return GamingAggregate(
      resolution:
          json['resolution'] as String? ??
          json['test_resolution'] as String? ??
          '1080p',
      gpuUsed: json['gpu_used'] as String? ?? json['test_gpu'] as String?,
      avgFps: _parseDouble(json['avg_fps']),
      fps1Percent: _parseDouble(json['fps_1_percent']),
      fps01Percent: _parseDouble(json['fps_01_percent']),
      gamingScore: _parseInt(json['gaming_score']),
    );
  }

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Check if any gaming data exists
  bool get hasData => avgFps != null || gamingScore != null;

  /// Format average FPS for display
  String get formattedAvgFps =>
      avgFps != null ? '${avgFps!.toStringAsFixed(1)} FPS' : 'N/A';

  /// Format 1% low for display
  String get formatted1PercentLow =>
      fps1Percent != null ? '${fps1Percent!.toStringAsFixed(1)} FPS' : 'N/A';
}
