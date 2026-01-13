class Cpu {
  final int id;
  final String name;
  final String? codename;
  final String? generation;
  final int? cores;
  final int? threads;
  final int? pCores;
  final int? eCores;
  final double? baseClock;
  final double? boostClock;
  final double? pCoreBaseClock;
  final double? pCoreBoostClock;
  final double? eCoreBaseClock;
  final double? eCoreBoostClock;
  final int? l1Cache;
  final int? l2Cache;
  final int? l3Cache;
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
  final double? launchMsrp;
  final bool isReleased;
  final bool isDiscontinued;
  final String? imageUrl;
  final String? techpowerupUrl;
  final String? manufacturerName;
  final String? manufacturerLogo;
  final String? socketName;
  final int? socketReleaseYear;
  final String? familyName;
  final String? familyCodename;
  final List<CpuBenchmark>? benchmarks;

  Cpu({
    required this.id,
    required this.name,
    this.codename,
    this.generation,
    this.cores,
    this.threads,
    this.pCores,
    this.eCores,
    this.baseClock,
    this.boostClock,
    this.pCoreBaseClock,
    this.pCoreBoostClock,
    this.eCoreBaseClock,
    this.eCoreBoostClock,
    this.l1Cache,
    this.l2Cache,
    this.l3Cache,
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
    this.launchMsrp,
    this.isReleased = true,
    this.isDiscontinued = false,
    this.imageUrl,
    this.techpowerupUrl,
    this.manufacturerName,
    this.manufacturerLogo,
    this.socketName,
    this.socketReleaseYear,
    this.familyName,
    this.familyCodename,
    this.benchmarks,
  });

  factory Cpu.fromJson(Map<String, dynamic> json) {
    return Cpu(
      id: json['id'] as int,
      name: json['name'] as String,
      codename: json['codename'] as String?,
      generation: json['generation'] as String?,
      cores: json['cores'] as int?,
      threads: json['threads'] as int?,
      pCores: json['p_cores'] as int?,
      eCores: json['e_cores'] as int?,
      baseClock: (json['base_clock'] as num?)?.toDouble(),
      boostClock: (json['boost_clock'] as num?)?.toDouble(),
      pCoreBaseClock: (json['p_core_base_clock'] as num?)?.toDouble(),
      pCoreBoostClock: (json['p_core_boost_clock'] as num?)?.toDouble(),
      eCoreBaseClock: (json['e_core_base_clock'] as num?)?.toDouble(),
      eCoreBoostClock: (json['e_core_boost_clock'] as num?)?.toDouble(),
      l1Cache: json['l1_cache'] as int?,
      l2Cache: json['l2_cache'] as int?,
      l3Cache: json['l3_cache'] as int?,
      tdp: json['tdp'] as int?,
      basePower: json['base_power'] as int?,
      maxTurboPower: json['max_turbo_power'] as int?,
      processNode: json['process_node'] as String?,
      transistorsMillion: json['transistors_million'] as int?,
      dieSizeMm2: (json['die_size_mm2'] as num?)?.toDouble(),
      memoryType: json['memory_type'] as String?,
      memoryChannels: json['memory_channels'] as int?,
      maxMemoryGb: json['max_memory_gb'] as int?,
      hasIntegratedGpu: json['has_integrated_gpu'] as bool? ?? false,
      integratedGpuName: json['integrated_gpu_name'] as String?,
      pcieVersion: json['pcie_version'] as String?,
      pcieLanes: json['pcie_lanes'] as int?,
      launchDate: json['launch_date'] as String?,
      launchMsrp: (json['launch_msrp'] as num?)?.toDouble(),
      isReleased: json['is_released'] as bool? ?? true,
      isDiscontinued: json['is_discontinued'] as bool? ?? false,
      imageUrl: json['image_url'] as String?,
      techpowerupUrl: json['techpowerup_url'] as String?,
      manufacturerName: json['manufacturer_name'] as String?,
      manufacturerLogo: json['manufacturer_logo'] as String?,
      socketName: json['socket_name'] as String?,
      socketReleaseYear: json['socket_release_year'] as int?,
      familyName: json['family_name'] as String?,
      familyCodename: json['family_codename'] as String?,
      benchmarks: json['benchmarks'] != null
          ? (json['benchmarks'] as List)
              .map((b) => CpuBenchmark.fromJson(b))
              .toList()
          : null,
    );
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
  String get formattedBaseClock =>
      baseClock != null ? '${(baseClock! / 1000).toStringAsFixed(2)} GHz' : 'N/A';

  String get formattedBoostClock =>
      boostClock != null ? '${(boostClock! / 1000).toStringAsFixed(2)} GHz' : 'N/A';

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

  bool get isAmd =>
      manufacturerName?.toLowerCase() == 'amd';

  bool get isIntel =>
      manufacturerName?.toLowerCase() == 'intel';
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
