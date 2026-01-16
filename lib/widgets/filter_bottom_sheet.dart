import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/providers.dart';

/// Bottom sheet for filtering CPU list
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
                  Container(
                    margin: const EdgeInsets.symmetric(vertical: 12),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Filters', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                        TextButton(
                          onPressed: provider.hasFilters ? () { provider.clearFilters(); Navigator.pop(context); } : null,
                          child: const Text('Clear All'),
                        ),
                      ],
                    ),
                  ),
                  const Divider(),
                  Expanded(
                    child: ListView(
                      controller: scrollController,
                      padding: const EdgeInsets.all(16),
                      children: [
                        _buildSectionTitle('Manufacturer'),
                        Wrap(
                          spacing: 8,
                          children: [
                            _buildFilterChip(label: 'All', selected: provider.selectedManufacturer == null, onSelected: (_) => provider.setManufacturerFilter(null)),
                            ...provider.manufacturers.map((m) => _buildFilterChip(label: m, selected: provider.selectedManufacturer == m, onSelected: (_) => provider.setManufacturerFilter(m))),
                          ],
                        ),
                        const SizedBox(height: 24),
                        _buildSectionTitle('Socket'),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _buildFilterChip(label: 'All', selected: provider.selectedSocket == null, onSelected: (_) => provider.setSocketFilter(null)),
                            ...provider.sockets.take(20).map((s) => _buildFilterChip(label: s, selected: provider.selectedSocket == s, onSelected: (_) => provider.setSocketFilter(s))),
                          ],
                        ),
                        const SizedBox(height: 24),
                        _buildSectionTitle('Sort By'),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _buildSortChip(label: 'Name', sortBy: 'name', provider: provider),
                            _buildSortChip(label: 'Cores', sortBy: 'cores', provider: provider),
                            _buildSortChip(label: 'Clock Speed', sortBy: 'boost_clock', provider: provider),
                            _buildSortChip(label: 'TDP', sortBy: 'tdp', provider: provider),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Expanded(child: _buildOrderButton(label: 'Ascending', icon: Icons.arrow_upward, selected: provider.sortOrder == 'ASC', onTap: () => provider.setSorting(provider.sortBy, 'ASC'))),
                            const SizedBox(width: 12),
                            Expanded(child: _buildOrderButton(label: 'Descending', icon: Icons.arrow_downward, selected: provider.sortOrder == 'DESC', onTap: () => provider.setSorting(provider.sortBy, 'DESC'))),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Apply Filters'))),
                  ),
                ],
              );
            },
          );
        },
      ),
    );
  }

  Widget _buildSectionTitle(String title) => Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)));
  Widget _buildFilterChip({required String label, required bool selected, required ValueChanged<bool> onSelected}) => FilterChip(label: Text(label), selected: selected, onSelected: onSelected);
  Widget _buildSortChip({required String label, required String sortBy, required CpuProvider provider}) => FilterChip(label: Text(label), selected: provider.sortBy == sortBy, onSelected: (_) => provider.setSorting(sortBy, provider.sortOrder));
  Widget _buildOrderButton({required String label, required IconData icon, required bool selected, required VoidCallback onTap}) => OutlinedButton.icon(onPressed: onTap, icon: Icon(icon, size: 18), label: Text(label), style: OutlinedButton.styleFrom(backgroundColor: selected ? Theme.of(context).colorScheme.primaryContainer : null));
}
