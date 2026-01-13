import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/cpu.dart';
import '../services/api_service.dart';

enum LoadingState { initial, loading, loaded, error }

class CpuProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();

  // CPU List State
  List<Cpu> _cpus = [];
  LoadingState _cpuListState = LoadingState.initial;
  String? _cpuListError;
  int _currentPage = 1;
  int _totalPages = 1;
  int _totalCpus = 0;

  // Search State
  List<Cpu> _searchResults = [];
  LoadingState _searchState = LoadingState.initial;
  String _searchQuery = '';

  // Filter State
  int? _selectedManufacturerId;
  int? _selectedSocketId;
  int? _minCores;
  int? _maxCores;
  bool? _hasIgpu;
  String _sortBy = 'name';
  String _sortOrder = 'ASC';

  // Reference Data
  List<Manufacturer> _manufacturers = [];
  List<Socket> _sockets = [];

  // Selected CPU for detail view
  Cpu? _selectedCpu;
  LoadingState _selectedCpuState = LoadingState.initial;

  // Favorites
  Set<int> _favoriteIds = {};

  // Getters
  List<Cpu> get cpus => _cpus;
  LoadingState get cpuListState => _cpuListState;
  String? get cpuListError => _cpuListError;
  int get currentPage => _currentPage;
  int get totalPages => _totalPages;
  int get totalCpus => _totalCpus;
  bool get hasMore => _currentPage < _totalPages;

  List<Cpu> get searchResults => _searchResults;
  LoadingState get searchState => _searchState;
  String get searchQuery => _searchQuery;
  bool get isSearching => _searchQuery.isNotEmpty;

  int? get selectedManufacturerId => _selectedManufacturerId;
  int? get selectedSocketId => _selectedSocketId;
  int? get minCores => _minCores;
  int? get maxCores => _maxCores;
  bool? get hasIgpu => _hasIgpu;
  String get sortBy => _sortBy;
  String get sortOrder => _sortOrder;
  bool get hasFilters =>
      _selectedManufacturerId != null ||
      _selectedSocketId != null ||
      _minCores != null ||
      _maxCores != null ||
      _hasIgpu != null;

  List<Manufacturer> get manufacturers => _manufacturers;
  List<Socket> get sockets => _sockets;

  Cpu? get selectedCpu => _selectedCpu;
  LoadingState get selectedCpuState => _selectedCpuState;

  Set<int> get favoriteIds => _favoriteIds;
  List<Cpu> get favoriteCpus =>
      _cpus.where((cpu) => _favoriteIds.contains(cpu.id)).toList();

  // Initialize
  Future<void> initialize() async {
    await _loadFavorites();
    await loadManufacturers();
    await loadSockets();
    await loadCpus();
  }

  // Load CPUs
  Future<void> loadCpus({bool refresh = false}) async {
    if (refresh) {
      _currentPage = 1;
      _cpus = [];
    }

    if (_cpuListState == LoadingState.loading) return;

    _cpuListState = LoadingState.loading;
    _cpuListError = null;
    notifyListeners();

    try {
      final response = await _apiService.getCpus(
        page: _currentPage,
        manufacturerId: _selectedManufacturerId,
        socketId: _selectedSocketId,
        minCores: _minCores,
        maxCores: _maxCores,
        hasIgpu: _hasIgpu,
        sortBy: _sortBy,
        sortOrder: _sortOrder,
      );

      if (refresh) {
        _cpus = response.data;
      } else {
        _cpus.addAll(response.data);
      }

      _totalPages = response.totalPages;
      _totalCpus = response.total;
      _cpuListState = LoadingState.loaded;
    } catch (e) {
      _cpuListError = e.toString();
      _cpuListState = LoadingState.error;
    }

    notifyListeners();
  }

  // Load More CPUs
  Future<void> loadMoreCpus() async {
    if (!hasMore || _cpuListState == LoadingState.loading) return;

    _currentPage++;
    await loadCpus();
  }

  // Refresh CPUs
  Future<void> refreshCpus() async {
    await loadCpus(refresh: true);
  }

  // Search CPUs
  Future<void> searchCpus(String query) async {
    _searchQuery = query;

    if (query.isEmpty) {
      _searchResults = [];
      _searchState = LoadingState.initial;
      notifyListeners();
      return;
    }

    if (query.length < 2) return;

    _searchState = LoadingState.loading;
    notifyListeners();

    try {
      final response = await _apiService.searchCpus(query);
      _searchResults = response.data;
      _searchState = LoadingState.loaded;
    } catch (e) {
      _searchState = LoadingState.error;
    }

    notifyListeners();
  }

  // Clear Search
  void clearSearch() {
    _searchQuery = '';
    _searchResults = [];
    _searchState = LoadingState.initial;
    notifyListeners();
  }

  // Get CPU Details
  Future<void> loadCpuDetails(int id) async {
    _selectedCpuState = LoadingState.loading;
    notifyListeners();

    try {
      _selectedCpu = await _apiService.getCpuById(id);
      _selectedCpuState = LoadingState.loaded;
    } catch (e) {
      _selectedCpuState = LoadingState.error;
    }

    notifyListeners();
  }

  // Clear Selected CPU
  void clearSelectedCpu() {
    _selectedCpu = null;
    _selectedCpuState = LoadingState.initial;
    notifyListeners();
  }

  // Filters
  void setManufacturerFilter(int? manufacturerId) {
    _selectedManufacturerId = manufacturerId;
    // Reset socket filter when manufacturer changes
    if (manufacturerId != null) {
      loadSockets(manufacturerId: manufacturerId);
    }
    notifyListeners();
    refreshCpus();
  }

  void setSocketFilter(int? socketId) {
    _selectedSocketId = socketId;
    notifyListeners();
    refreshCpus();
  }

  void setCoreFilter({int? min, int? max}) {
    _minCores = min;
    _maxCores = max;
    notifyListeners();
    refreshCpus();
  }

  void setIgpuFilter(bool? hasIgpu) {
    _hasIgpu = hasIgpu;
    notifyListeners();
    refreshCpus();
  }

  void setSorting(String sortBy, String sortOrder) {
    _sortBy = sortBy;
    _sortOrder = sortOrder;
    notifyListeners();
    refreshCpus();
  }

  void clearFilters() {
    _selectedManufacturerId = null;
    _selectedSocketId = null;
    _minCores = null;
    _maxCores = null;
    _hasIgpu = null;
    _sortBy = 'name';
    _sortOrder = 'ASC';
    notifyListeners();
    refreshCpus();
  }

  // Reference Data
  Future<void> loadManufacturers() async {
    try {
      _manufacturers = await _apiService.getManufacturers();
      notifyListeners();
    } catch (e) {
      debugPrint('Error loading manufacturers: $e');
    }
  }

  Future<void> loadSockets({int? manufacturerId}) async {
    try {
      _sockets = await _apiService.getSockets(manufacturerId: manufacturerId);
      notifyListeners();
    } catch (e) {
      debugPrint('Error loading sockets: $e');
    }
  }

  // Favorites
  Future<void> _loadFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    final favorites = prefs.getStringList('favorite_cpus') ?? [];
    _favoriteIds = favorites.map((id) => int.parse(id)).toSet();
    notifyListeners();
  }

  Future<void> _saveFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(
      'favorite_cpus',
      _favoriteIds.map((id) => id.toString()).toList(),
    );
  }

  bool isFavorite(int cpuId) => _favoriteIds.contains(cpuId);

  Future<void> toggleFavorite(int cpuId) async {
    if (_favoriteIds.contains(cpuId)) {
      _favoriteIds.remove(cpuId);
    } else {
      _favoriteIds.add(cpuId);
    }
    await _saveFavorites();
    notifyListeners();
  }
}
