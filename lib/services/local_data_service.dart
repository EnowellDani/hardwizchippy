import 'dart:convert';
import 'package:flutter/services.dart';
import '../models/cpu.dart';

class LocalDataService {
  static final LocalDataService _instance = LocalDataService._internal();
  factory LocalDataService() => _instance;
  LocalDataService._internal();

  List<Cpu>? _cachedCpus;
  bool _isLoaded = false;

  Future<void> loadData() async {
    if (_isLoaded) return;

    try {
      final jsonString = await rootBundle.loadString('assets/data/cpu_database.json');
      final jsonData = json.decode(jsonString) as Map<String, dynamic>;
      final cpuList = jsonData['cpus'] as List;

      _cachedCpus = cpuList.map((cpu) => _parseCpuFromJson(cpu)).toList();
      _isLoaded = true;
    } catch (e) {
      throw Exception('Failed to load CPU database: $e');
    }
  }

  Cpu _parseCpuFromJson(Map<String, dynamic> json) {
    // Support both nested (v2) and flat (v1) JSON formats
    final general = json['general'] as Map<String, dynamic>?;
    final coresData = json['cores'] as Map<String, dynamic>?;
    final cache = json['cache'] as Map<String, dynamic>?;
    final memory = json['memory'] as Map<String, dynamic>?;
    final graphics = json['graphics'] as Map<String, dynamic>?;
    final pcie = json['pcie'] as Map<String, dynamic>?;
    final features = json['features'] as Map<String, dynamic>?;
    final benchmarksData = json['benchmarks'] as Map<String, dynamic>?;
    final gamingData = json['gaming'] as List?;

    // Determine if this is v2 (nested) or v1 (flat) format
    final isNested = general != null || coresData != null;

    // Parse structured benchmarks if available
    CpuBenchmarks? structuredBenchmarks;
    if (benchmarksData != null) {
      structuredBenchmarks = CpuBenchmarks.fromJson(benchmarksData);
    }

    // Parse gaming benchmarks if available
    List<GamingBenchmark>? gamingBenchmarks;
    if (gamingData != null) {
      gamingBenchmarks = gamingData
          .map((g) => GamingBenchmark.fromJson(g as Map<String, dynamic>))
          .toList();
    }

    // Extract values with nested/flat fallback
    String? getString(String nestedKey, String flatKey, [Map<String, dynamic>? nestedMap]) {
      if (isNested && nestedMap != null) {
        return nestedMap[nestedKey] as String?;
      }
      return json[flatKey] as String?;
    }

    int? getInt(String nestedKey, String flatKey, [Map<String, dynamic>? nestedMap]) {
      if (isNested && nestedMap != null) {
        return nestedMap[nestedKey] as int?;
      }
      return json[flatKey] as int?;
    }

    double? getDouble(String nestedKey, String flatKey, [Map<String, dynamic>? nestedMap]) {
      if (isNested && nestedMap != null) {
        final value = nestedMap[nestedKey];
        return (value as num?)?.toDouble();
      }
      final value = json[flatKey];
      return (value as num?)?.toDouble();
    }

    bool getBool(String nestedKey, String flatKey, bool defaultValue, [Map<String, dynamic>? nestedMap]) {
      if (isNested && nestedMap != null) {
        return nestedMap[nestedKey] as bool? ?? defaultValue;
      }
      return json[flatKey] as bool? ?? defaultValue;
    }

    return Cpu(
      id: json['id'] as int? ?? json.hashCode,
      name: json['name'] as String? ?? 'Unknown',
      manufacturerName: json['manufacturer'] as String? ?? general?['manufacturer'] as String?,

      // General info
      codename: getString('codename', 'codename', coresData),
      generation: json['generation'] as String?,
      launchDate: getString('launch_date', 'launch_date', general),
      launchMsrp: getDouble('launch_msrp', 'launch_msrp', general),
      currentPrice: getDouble('current_price', 'current_price', general),
      fabProcessor: getString('fab_processor', 'fab_processor', general),
      processNode: getString('process_node', 'process_node', general),
      transistorsMillion: getInt('transistors_million', 'transistors_million', general),
      dieSizeMm2: getDouble('die_size_mm2', 'die_size_mm2', general),
      tdp: getInt('tdp', 'tdp', general),
      basePower: getInt('base_power', 'base_power', general),
      maxTurboPower: getInt('max_turbo_power', 'max_turbo_power', general),
      socketName: getString('socket', 'socket', general),

      // Core info
      microarchitecture: getString('microarchitecture', 'microarchitecture', coresData),
      coreStepping: getString('stepping', 'stepping', coresData),
      cores: getInt('cores', 'cores', coresData),
      threads: getInt('threads', 'threads', coresData),
      pCores: getInt('p_cores', 'p_cores', coresData),
      eCores: getInt('e_cores', 'e_cores', coresData),
      baseClock: getDouble('base_clock', 'base_clock', coresData),
      boostClock: getDouble('boost_clock', 'boost_clock', coresData),
      pCoreBaseClock: getDouble('p_core_base_clock', 'p_core_base_clock', coresData),
      pCoreBoostClock: getDouble('p_core_boost_clock', 'p_core_boost_clock', coresData),
      eCoreBaseClock: getDouble('e_core_base_clock', 'e_core_base_clock', coresData),
      eCoreBoostClock: getDouble('e_core_boost_clock', 'e_core_boost_clock', coresData),
      multiplier: getDouble('multiplier', 'multiplier', coresData),
      turboMultiplier: getDouble('turbo_multiplier', 'turbo_multiplier', coresData),
      unlockedMultiplier: getBool('unlocked', 'unlocked_multiplier', false, coresData),

      // Cache
      l1Cache: getInt('l1', 'l1_cache', cache),
      l1CacheInstruction: getInt('l1_instruction', 'l1_cache_instruction', cache),
      l1CacheData: getInt('l1_data', 'l1_cache_data', cache),
      l2Cache: getInt('l2', 'l2_cache', cache),
      l3Cache: getInt('l3', 'l3_cache', cache),

      // Memory
      memoryType: getString('type', 'memory_type', memory),
      memoryBandwidth: getDouble('bandwidth', 'memory_bandwidth', memory),
      memoryChannels: getInt('channels', 'memory_channels', memory),
      maxMemoryGb: getInt('max_size', 'max_memory_gb', memory),
      eccSupported: getBool('ecc', 'ecc_supported', false, memory),

      // Graphics (iGPU)
      hasIntegratedGpu: isNested
          ? (graphics?['name'] as String?) != null
          : json['has_integrated_gpu'] as bool? ?? false,
      integratedGpuName: getString('name', 'integrated_gpu_name', graphics),
      graphicsBaseFreq: getInt('base_freq', 'graphics_base_freq', graphics),
      graphicsTurboFreq: getInt('turbo_freq', 'graphics_turbo_freq', graphics),
      graphicsCoreConfig: getString('core_config', 'graphics_core_config', graphics),

      // PCIe
      pcieVersion: getString('revision', 'pcie_version', pcie),
      pcieLanes: getInt('lanes', 'pcie_lanes', pcie),
      pcieConfig: getString('config', 'pcie_config', pcie),

      // Features
      dataWidth: getInt('data_width', 'data_width', features),

      // URLs and images
      imageUrl: json['image_url'] as String?,
      techpowerupUrl: json['techpowerup_url'] as String?,
      manufacturerLogo: json['manufacturer_logo'] as String?,

      // Status
      isReleased: json['is_released'] as bool? ?? true,
      isDiscontinued: json['is_discontinued'] as bool? ?? false,

      // Benchmarks
      structuredBenchmarks: structuredBenchmarks,
      gamingBenchmarks: gamingBenchmarks,
    );
  }

  List<Cpu> getAllCpus() {
    return _cachedCpus ?? [];
  }

  PaginatedResponse<Cpu> getCpus({
    int page = 1,
    int limit = 20,
    String? manufacturer,
    String? socket,
    int? minCores,
    int? maxCores,
    String sortBy = 'name',
    String sortOrder = 'ASC',
  }) {
    var cpus = List<Cpu>.from(_cachedCpus ?? []);

    // Apply filters
    if (manufacturer != null && manufacturer.isNotEmpty) {
      cpus = cpus.where((cpu) =>
          cpu.manufacturerName?.toUpperCase() == manufacturer.toUpperCase()
      ).toList();
    }

    if (socket != null && socket.isNotEmpty) {
      cpus = cpus.where((cpu) =>
          cpu.socketName?.toLowerCase().contains(socket.toLowerCase()) ?? false
      ).toList();
    }

    if (minCores != null) {
      cpus = cpus.where((cpu) => (cpu.cores ?? 0) >= minCores).toList();
    }

    if (maxCores != null) {
      cpus = cpus.where((cpu) => (cpu.cores ?? 0) <= maxCores).toList();
    }

    // Sort
    cpus.sort((a, b) {
      int comparison;
      switch (sortBy) {
        case 'cores':
          comparison = (a.cores ?? 0).compareTo(b.cores ?? 0);
          break;
        case 'base_clock':
          comparison = (a.baseClock ?? 0).compareTo(b.baseClock ?? 0);
          break;
        case 'boost_clock':
          comparison = (a.boostClock ?? 0).compareTo(b.boostClock ?? 0);
          break;
        case 'tdp':
          comparison = (a.tdp ?? 0).compareTo(b.tdp ?? 0);
          break;
        case 'name':
        default:
          comparison = a.name.compareTo(b.name);
      }
      return sortOrder == 'DESC' ? -comparison : comparison;
    });

    // Paginate
    final total = cpus.length;
    final totalPages = (total / limit).ceil();
    final startIndex = (page - 1) * limit;
    final endIndex = startIndex + limit;

    final paginatedCpus = cpus.sublist(
      startIndex.clamp(0, total),
      endIndex.clamp(0, total),
    );

    return PaginatedResponse(
      data: paginatedCpus,
      currentPage: page,
      perPage: limit,
      total: total,
      totalPages: totalPages,
    );
  }

  Cpu? getCpuById(int id) {
    try {
      return _cachedCpus?.firstWhere((cpu) => cpu.id == id);
    } catch (e) {
      return null;
    }
  }

  Cpu? getCpuByName(String name) {
    try {
      return _cachedCpus?.firstWhere(
        (cpu) => cpu.name.toLowerCase() == name.toLowerCase(),
      );
    } catch (e) {
      return null;
    }
  }

  PaginatedResponse<Cpu> searchCpus(String query, {int page = 1, int limit = 20}) {
    if (query.isEmpty || query.length < 2) {
      return PaginatedResponse(
        data: [],
        currentPage: 1,
        perPage: limit,
        total: 0,
        totalPages: 0,
      );
    }

    final queryLower = query.toLowerCase();
    var results = (_cachedCpus ?? []).where((cpu) {
      return cpu.name.toLowerCase().contains(queryLower) ||
          (cpu.codename?.toLowerCase().contains(queryLower) ?? false) ||
          (cpu.manufacturerName?.toLowerCase().contains(queryLower) ?? false);
    }).toList();

    // Sort by relevance (name starts with query first)
    results.sort((a, b) {
      final aStartsWith = a.name.toLowerCase().startsWith(queryLower);
      final bStartsWith = b.name.toLowerCase().startsWith(queryLower);
      if (aStartsWith && !bStartsWith) return -1;
      if (!aStartsWith && bStartsWith) return 1;
      return a.name.compareTo(b.name);
    });

    // Paginate
    final total = results.length;
    final totalPages = (total / limit).ceil();
    final startIndex = (page - 1) * limit;
    final endIndex = startIndex + limit;

    final paginatedResults = results.sublist(
      startIndex.clamp(0, total),
      endIndex.clamp(0, total),
    );

    return PaginatedResponse(
      data: paginatedResults,
      currentPage: page,
      perPage: limit,
      total: total,
      totalPages: totalPages,
    );
  }

  List<String> getManufacturers() {
    final manufacturers = (_cachedCpus ?? [])
        .map((cpu) => cpu.manufacturerName)
        .whereType<String>()
        .toSet()
        .toList();
    manufacturers.sort();
    return manufacturers;
  }

  List<String> getSockets({String? manufacturer}) {
    var cpus = _cachedCpus ?? [];

    if (manufacturer != null && manufacturer.isNotEmpty) {
      cpus = cpus.where((cpu) =>
          cpu.manufacturerName?.toUpperCase() == manufacturer.toUpperCase()
      ).toList();
    }

    final sockets = cpus
        .map((cpu) => cpu.socketName)
        .whereType<String>()
        .where((s) => s.isNotEmpty && s != '-')
        .toSet()
        .toList();
    sockets.sort();
    return sockets;
  }

  int get totalCpuCount => _cachedCpus?.length ?? 0;
}
