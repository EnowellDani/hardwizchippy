import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';
import '../services/services.dart';

/// State enumeration for loading operations
enum LoadingState { initial, loading, loaded, error }

/// Provider for managing CPU data and state
class CpuProvider with ChangeNotifier {
  final LocalDataService _dataService = LocalDataService();

  // CPU List State
  List<Cpu> _cpus = [];
  List<Cpu> _allCpus = [];
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
  String? _selectedManufacturer;
  String? _selectedSocket;
  int? _minCores;
  int? _maxCores;
  String _sortBy = 'name';
  String _sortOrder = 'ASC';

  // Reference Data
  List<String> _manufacturers = [];
  List<String> _sockets = [];

  // Selected CPU
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

  String? get selectedManufacturer => _selectedManufacturer;
  String? get selectedSocket => _selectedSocket;
  int? get minCores => _minCores;
  int? get maxCores => _maxCores;
  String get sortBy => _sortBy;
  String get sortOrder => _sortOrder;
  bool get hasFilters =>
      _selectedManufacturer != null ||
      _selectedSocket != null ||
      _minCores != null ||
      _maxCores != null;

  List<String> get manufacturers => _manufacturers;
  List<String> get sockets => _sockets;

  Cpu? get selectedCpu => _selectedCpu;
  LoadingState get selectedCpuState => _selectedCpuState;

  Set<int> get favoriteIds => _favoriteIds;
  List<Cpu> get favoriteCpus =>
      _allCpus.where((cpu) => _favoriteIds.contains(cpu.id)).toList();

  // Initialize
  Future<void> initialize() async {
    _cpuListState = LoadingState.loading;
    notifyListeners();

    try {
      await _dataService.loadData();
      await _loadFavorites();
      _manufacturers = _dataService.getManufacturers();
      _sockets = _dataService.getSockets();
      _allCpus = _dataService.getAllCpus();
      await loadCpus();
    } catch (e) {
      _cpuListError = e.toString();
      _cpuListState = LoadingState.error;
      notifyListeners();
    }
  }

  Future<void> loadCpus({bool refresh = false}) async {
    if (refresh) {
      _currentPage = 1;
      _cpus = [];
    }

    _cpuListState = LoadingState.loading;
    _cpuListError = null;
    notifyListeners();

    try {
      final response = _dataService.getCpus(
        page: _currentPage,
        manufacturer: _selectedManufacturer,
        socket: _selectedSocket,
        minCores: _minCores,
        maxCores: _maxCores,
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

  Future<void> loadMoreCpus() async {
    if (!hasMore || _cpuListState == LoadingState.loading) return;
    _currentPage++;
    await loadCpus();
  }

  Future<void> refreshCpus() async {
    await loadCpus(refresh: true);
  }

  void searchCpus(String query) {
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

    final response = _dataService.searchCpus(query);
    _searchResults = response.data;
    _searchState = LoadingState.loaded;
    notifyListeners();
  }

  void clearSearch() {
    _searchQuery = '';
    _searchResults = [];
    _searchState = LoadingState.initial;
    notifyListeners();
  }

  void selectCpu(Cpu cpu) {
    _selectedCpu = cpu;
    _selectedCpuState = LoadingState.loaded;
    notifyListeners();
  }

  void loadCpuDetails(int id) {
    _selectedCpuState = LoadingState.loading;
    notifyListeners();
    _selectedCpu = _dataService.getCpuById(id);
    _selectedCpuState = _selectedCpu != null ? LoadingState.loaded : LoadingState.error;
    notifyListeners();
  }

  void clearSelectedCpu() {
    _selectedCpu = null;
    _selectedCpuState = LoadingState.initial;
    notifyListeners();
  }

  void setManufacturerFilter(String? manufacturer) {
    _selectedManufacturer = manufacturer;
    _sockets = _dataService.getSockets(manufacturer: manufacturer);
    _selectedSocket = null;
    notifyListeners();
    refreshCpus();
  }

  void setSocketFilter(String? socket) {
    _selectedSocket = socket;
    notifyListeners();
    refreshCpus();
  }

  void setCoreFilter({int? min, int? max}) {
    _minCores = min;
    _maxCores = max;
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
    _selectedManufacturer = null;
    _selectedSocket = null;
    _minCores = null;
    _maxCores = null;
    _sortBy = 'name';
    _sortOrder = 'ASC';
    _sockets = _dataService.getSockets();
    notifyListeners();
    refreshCpus();
  }

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
