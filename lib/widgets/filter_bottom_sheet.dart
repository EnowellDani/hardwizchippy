import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/cpu_provider.dart';

class FilterBottomSheet extends StatefulWidget {
  const FilterBottomSheet({super.key});

  @override
  State<FilterBottomSheet> createState() => _FilterBottomSheetState();
}

class _FilterBottomSheetState extends State<FilterBottomSheet> {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) {
          return Consumer<CpuProvider>(
            builder: (context, provider, child) {
              return Column(
                children: [
                  // Handle
                  Container(
                    margin: const EdgeInsets.symmetric(vertical: 12),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),

                  // Header
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Filters',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        TextButton(
                          onPressed: provider.hasFilters
                              ? () {
                                  provider.clearFilters();
                                  Navigator.pop(context);
                                }
                              : null,
                          child: const Text('Clear All'),
                        ),
                      ],
                    ),
                  ),

                  const Divider(),

                  // Filter options
                  Expanded(
                    child: ListView(
                      controller: scrollController,
                      padding: const EdgeInsets.all(16),
                      children: [
                        // Manufacturer Filter
                        _buildSectionTitle('Manufacturer'),
                        Wrap(
                          spacing: 8,
                          children: [
                            _buildFilterChip(
                              label: 'All',
                              selected: provider.selectedManufacturerId == null,
                              onSelected: (_) =>
                                  provider.setManufacturerFilter(null),
                            ),
                            ...provider.manufacturers.map(
                              (m) => _buildFilterChip(
                                label: m.name,
                                selected:
                                    provider.selectedManufacturerId == m.id,
                                onSelected: (_) =>
                                    provider.setManufacturerFilter(m.id),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 24),

                        // Socket Filter
                        _buildSectionTitle('Socket'),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _buildFilterChip(
                              label: 'All',
                              selected: provider.selectedSocketId == null,
                              onSelected: (_) => provider.setSocketFilter(null),
                            ),
                            ...provider.sockets.map(
                              (s) => _buildFilterChip(
                                label: s.name,
                                selected: provider.selectedSocketId == s.id,
                                onSelected: (_) =>
                                    provider.setSocketFilter(s.id),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 24),

                        // iGPU Filter
                        _buildSectionTitle('Integrated GPU'),
                        Wrap(
                          spacing: 8,
                          children: [
                            _buildFilterChip(
                              label: 'All',
                              selected: provider.hasIgpu == null,
                              onSelected: (_) => provider.setIgpuFilter(null),
                            ),
                            _buildFilterChip(
                              label: 'With iGPU',
                              selected: provider.hasIgpu == true,
                              onSelected: (_) => provider.setIgpuFilter(true),
                            ),
                            _buildFilterChip(
                              label: 'Without iGPU',
                              selected: provider.hasIgpu == false,
                              onSelected: (_) => provider.setIgpuFilter(false),
                            ),
                          ],
                        ),

                        const SizedBox(height: 24),

                        // Sort Options
                        _buildSectionTitle('Sort By'),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _buildSortChip(
                              label: 'Name',
                              sortBy: 'name',
                              provider: provider,
                            ),
                            _buildSortChip(
                              label: 'Cores',
                              sortBy: 'cores',
                              provider: provider,
                            ),
                            _buildSortChip(
                              label: 'Clock Speed',
                              sortBy: 'boost_clock',
                              provider: provider,
                            ),
                            _buildSortChip(
                              label: 'TDP',
                              sortBy: 'tdp',
                              provider: provider,
                            ),
                            _buildSortChip(
                              label: 'Launch Date',
                              sortBy: 'launch_date',
                              provider: provider,
                            ),
                            _buildSortChip(
                              label: 'Price',
                              sortBy: 'launch_msrp',
                              provider: provider,
                            ),
                          ],
                        ),

                        const SizedBox(height: 16),

                        // Sort Order
                        Row(
                          children: [
                            Expanded(
                              child: _buildOrderButton(
                                label: 'Ascending',
                                icon: Icons.arrow_upward,
                                selected: provider.sortOrder == 'ASC',
                                onTap: () => provider.setSorting(
                                  provider.sortBy,
                                  'ASC',
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: _buildOrderButton(
                                label: 'Descending',
                                icon: Icons.arrow_downward,
                                selected: provider.sortOrder == 'DESC',
                                onTap: () => provider.setSorting(
                                  provider.sortBy,
                                  'DESC',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  // Apply button
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Apply Filters'),
                      ),
                    ),
                  ),
                ],
              );
            },
          );
        },
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildFilterChip({
    required String label,
    required bool selected,
    required ValueChanged<bool> onSelected,
  }) {
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: onSelected,
    );
  }

  Widget _buildSortChip({
    required String label,
    required String sortBy,
    required CpuProvider provider,
  }) {
    final isSelected = provider.sortBy == sortBy;
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => provider.setSorting(sortBy, provider.sortOrder),
    );
  }

  Widget _buildOrderButton({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return OutlinedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: OutlinedButton.styleFrom(
        backgroundColor: selected
            ? Theme.of(context).colorScheme.primaryContainer
            : null,
      ),
    );
  }
}
