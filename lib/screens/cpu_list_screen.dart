import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/cpu.dart';
import '../providers/cpu_provider.dart';
import '../widgets/cpu_card.dart';
import '../widgets/filter_bottom_sheet.dart';
import '../widgets/search_bar_widget.dart';
import 'cpu_detail_screen.dart';

class CpuListScreen extends StatefulWidget {
  const CpuListScreen({super.key});

  @override
  State<CpuListScreen> createState() => _CpuListScreenState();
}

class _CpuListScreenState extends State<CpuListScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      final provider = context.read<CpuProvider>();
      if (!provider.isSearching) {
        provider.loadMoreCpus();
      }
    }
  }

  void _navigateToDetail(Cpu cpu) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CpuDetailScreen(cpuId: cpu.id),
      ),
    );
  }

  void _showFilterBottomSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => const FilterBottomSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('HardWizChippy'),
        actions: [
          Consumer<CpuProvider>(
            builder: (context, provider, child) {
              return Badge(
                isLabelVisible: provider.hasFilters,
                child: IconButton(
                  icon: const Icon(Icons.filter_list),
                  onPressed: _showFilterBottomSheet,
                  tooltip: 'Filters',
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.all(16),
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

          // CPU List
          Expanded(
            child: Consumer<CpuProvider>(
              builder: (context, provider, child) {
                // Show search results if searching
                if (provider.isSearching) {
                  return _buildSearchResults(provider);
                }

                // Show main CPU list
                return _buildCpuList(provider);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResults(CpuProvider provider) {
    if (provider.searchState == LoadingState.loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (provider.searchResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No CPUs found for "${provider.searchQuery}"',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16),
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

  Widget _buildCpuList(CpuProvider provider) {
    if (provider.cpuListState == LoadingState.loading && provider.cpus.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (provider.cpuListState == LoadingState.error && provider.cpus.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              provider.cpuListError ?? 'Failed to load CPUs',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => provider.refreshCpus(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (provider.cpus.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.memory,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No CPUs found',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 16,
              ),
            ),
            if (provider.hasFilters) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => provider.clearFilters(),
                child: const Text('Clear filters'),
              ),
            ],
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => provider.refreshCpus(),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: provider.cpus.length + (provider.hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == provider.cpus.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          final cpu = provider.cpus[index];
          return CpuCard(
            cpu: cpu,
            onTap: () => _navigateToDetail(cpu),
          );
        },
      ),
    );
  }
}
