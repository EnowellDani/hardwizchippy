import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/core.dart';
import '../models/models.dart';
import '../providers/providers.dart';
import '../widgets/widgets.dart';
import 'cpu_detail_screen.dart';

class CpuListScreen extends StatefulWidget {
  const CpuListScreen({super.key});

  @override
  State<CpuListScreen> createState() => _CpuListScreenState();
}

class _CpuListScreenState extends State<CpuListScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();
  final Map<int, ScrollController> _scrollControllers = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    // Create scroll controllers for each tab
    for (int i = 0; i < 3; i++) {
      _scrollControllers[i] = ScrollController();
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    for (final controller in _scrollControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  void _navigateToDetail(Cpu cpu) {
    Navigator.push(
      context,
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            CpuDetailScreen(cpuId: cpu.id),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          const begin = Offset(1.0, 0.0);
          const end = Offset.zero;
          const curve = Curves.easeInOutCubic;
          var tween = Tween(begin: begin, end: end).chain(
            CurveTween(curve: curve),
          );
          return SlideTransition(
            position: animation.drive(tween),
            child: child,
          );
        },
        transitionDuration: const Duration(milliseconds: 300),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: NestedScrollView(
        headerSliverBuilder: (context, innerBoxIsScrolled) {
          return [
            // App Bar with search
            SliverAppBar(
              floating: true,
              snap: true,
              title: const Text('HardWizChippy'),
              centerTitle: true,
              elevation: 0,
              bottom: PreferredSize(
                preferredSize: const Size.fromHeight(108),
                child: Column(
                  children: [
                    // Search Bar
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: SearchBarWidget(
                        controller: _searchController,
                        onChanged: (query) {
                          context.read<CpuProvider>().searchCpus(query);
                        },
                        onClear: () {
                          _searchController.clear();
                          context.read<CpuProvider>().clearSearch();
                        },
                      ),
                    ),
                    // Manufacturer Tabs
                    _buildManufacturerTabs(isDark),
                  ],
                ),
              ),
            ),
          ];
        },
        body: Consumer<CpuProvider>(
          builder: (context, provider, child) {
            // Show search results if searching
            if (provider.isSearching) {
              return _buildSearchResults(provider);
            }

            // Show tabbed CPU lists
            return TabBarView(
              controller: _tabController,
              children: [
                _buildCpuList(provider, null), // All
                _buildCpuList(provider, 'AMD'), // AMD
                _buildCpuList(provider, 'Intel'), // Intel
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildManufacturerTabs(bool isDark) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: isDark ? Colors.grey.shade900 : Colors.grey.shade200,
        borderRadius: BorderRadius.circular(12),
      ),
      child: TabBar(
        controller: _tabController,
        indicator: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          color: isDark ? Colors.grey.shade800 : Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        indicatorSize: TabBarIndicatorSize.tab,
        indicatorPadding: const EdgeInsets.all(4),
        dividerColor: Colors.transparent,
        labelColor: isDark ? Colors.white : Colors.black87,
        unselectedLabelColor: isDark ? Colors.grey.shade500 : Colors.grey.shade600,
        labelStyle: const TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
        unselectedLabelStyle: const TextStyle(
          fontWeight: FontWeight.w500,
          fontSize: 13,
        ),
        tabs: [
          const Tab(
            height: 36,
            child: Text('All'),
          ),
          Tab(
            height: 36,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: AppColors.amd,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text('AMD'),
              ],
            ),
          ),
          Tab(
            height: 36,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: AppColors.intel,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text('Intel'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResults(CpuProvider provider) {
    if (provider.searchState == LoadingState.loading) {
      return const CpuListShimmer();
    }

    if (provider.searchResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No CPUs found for "${provider.searchQuery}"',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Try a different search term',
              style: TextStyle(
                color: Colors.grey.shade500,
                fontSize: 13,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: provider.searchResults.length,
      itemBuilder: (context, index) {
        final cpu = provider.searchResults[index];
        return CpuCard(
          cpu: cpu,
          onTap: () => _navigateToDetail(cpu),
        );
      },
    );
  }

  Widget _buildCpuList(CpuProvider provider, String? manufacturer) {
    // Filter CPUs by manufacturer
    List<Cpu> cpus;
    if (manufacturer == null) {
      cpus = provider.cpus;
    } else {
      cpus = provider.cpus
          .where((cpu) =>
              cpu.manufacturerName?.toUpperCase() == manufacturer.toUpperCase())
          .toList();
    }

    if (provider.cpuListState == LoadingState.loading && cpus.isEmpty) {
      return const CpuListShimmer();
    }

    if (provider.cpuListState == LoadingState.error && cpus.isEmpty) {
      return _buildErrorState(provider);
    }

    if (cpus.isEmpty) {
      return _buildEmptyState(manufacturer);
    }

    final tabIndex = manufacturer == null ? 0 : (manufacturer == 'AMD' ? 1 : 2);

    return RefreshIndicator(
      onRefresh: () => provider.refreshCpus(),
      color: manufacturer == 'AMD'
          ? AppColors.amd
          : (manufacturer == 'Intel' ? AppColors.intel : AppColors.primary),
      child: ListView.builder(
        controller: _scrollControllers[tabIndex],
        padding: const EdgeInsets.all(16),
        itemCount: cpus.length,
        itemBuilder: (context, index) {
          final cpu = cpus[index];
          return RepaintBoundary(
            child: CpuCard(
              cpu: cpu,
              onTap: () => _navigateToDetail(cpu),
            ),
          );
        },
      ),
    );
  }

  Widget _buildErrorState(CpuProvider provider) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 64,
              color: Colors.red.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to load CPUs',
              style: TextStyle(
                color: Colors.grey.shade700,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              provider.cpuListError ?? 'An error occurred',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => provider.refreshCpus(),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(String? manufacturer) {
    final color = manufacturer == 'AMD'
        ? AppColors.amd
        : (manufacturer == 'Intel' ? AppColors.intel : AppColors.primary);

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.memory_rounded,
            size: 64,
            color: color.withValues(alpha: 0.5),
          ),
          const SizedBox(height: 16),
          Text(
            manufacturer != null
                ? 'No $manufacturer CPUs found'
                : 'No CPUs found',
            style: TextStyle(
              color: Colors.grey.shade600,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}
