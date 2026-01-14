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
    return Cpu(
      id: json.hashCode, // Generate ID from hash since JSON doesn't have IDs
      name: json['name'] as String? ?? 'Unknown',
      codename: json['codename'] as String?,
      cores: json['cores'] as int?,
      threads: json['cores'] as int?, // Approximate threads = cores for now
      baseClock: (json['base_clock'] as num?)?.toDouble(),
      boostClock: (json['boost_clock'] as num?)?.toDouble(),
      l3Cache: json['l3_cache'] as int?,
      tdp: json['tdp'] as int?,
      processNode: json['process_node'] as String?,
      socketName: json['socket'] as String?,
      launchDate: json['launch_date'] as String?,
      manufacturerName: json['manufacturer'] as String?,
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
