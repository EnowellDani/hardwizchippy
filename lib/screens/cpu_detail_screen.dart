import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/core.dart';
import '../models/models.dart';
import '../providers/providers.dart';

class CpuDetailScreen extends StatefulWidget {
  final int cpuId;

  const CpuDetailScreen({super.key, required this.cpuId});

  @override
  State<CpuDetailScreen> createState() => _CpuDetailScreenState();
}

class _CpuDetailScreenState extends State<CpuDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CpuProvider>().loadCpuDetails(widget.cpuId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Consumer<CpuProvider>(
        builder: (context, provider, child) {
          if (provider.selectedCpuState == LoadingState.loading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.selectedCpuState == LoadingState.error ||
              provider.selectedCpu == null) {
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
                  const Text('Failed to load CPU details'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () =>
                        provider.loadCpuDetails(widget.cpuId),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          final cpu = provider.selectedCpu!;
          return _buildContent(context, cpu, provider);
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context, Cpu cpu, CpuProvider provider) {
    final manufacturerColor = AppColors.getManufacturerColor(
      cpu.manufacturerName ?? '',
    );

    return CustomScrollView(
      slivers: [
        // App Bar
        SliverAppBar(
          expandedHeight: 200,
          pinned: true,
          flexibleSpace: FlexibleSpaceBar(
            title: Text(
              cpu.name,
              style: const TextStyle(fontSize: 16),
            ),
            background: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    manufacturerColor,
                    manufacturerColor.withValues(alpha: 0.7),
                  ],
                ),
              ),
              child: Center(
                child: Icon(
                  Icons.memory,
                  size: 80,
                  color: Colors.white.withValues(alpha: 0.3),
                ),
              ),
            ),
          ),
          actions: [
            IconButton(
              icon: Icon(
                provider.isFavorite(cpu.id)
                    ? Icons.favorite
                    : Icons.favorite_outline,
              ),
              onPressed: () => provider.toggleFavorite(cpu.id),
            ),
            if (cpu.techpowerupUrl != null)
              IconButton(
                icon: const Icon(Icons.open_in_new),
                onPressed: () async {
                  final uri = Uri.parse(cpu.techpowerupUrl!);
                  if (await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                },
              ),
          ],
        ),

        // Content
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Quick Specs Card
                _buildQuickSpecsCard(cpu),

                const SizedBox(height: 16),

                // Core Configuration
                _buildSpecSection(
                  title: 'Core Configuration',
                  icon: Icons.memory,
                  specs: [
                    if (cpu.isHybrid) ...[
                      _SpecItem('Architecture', 'Hybrid (P+E Cores)'),
                      _SpecItem('P-Cores', '${cpu.pCores}'),
                      _SpecItem('E-Cores', '${cpu.eCores}'),
                      _SpecItem('Total Cores', '${cpu.cores}'),
                    ] else ...[
                      _SpecItem('Cores', '${cpu.cores ?? 'N/A'}'),
                    ],
                    _SpecItem('Threads', '${cpu.threads ?? 'N/A'}'),
                  ],
                ),

                const SizedBox(height: 16),

                // Clock Speeds
                _buildSpecSection(
                  title: 'Clock Speeds',
                  icon: Icons.speed,
                  specs: [
                    _SpecItem('Base Clock', cpu.formattedBaseClock),
                    _SpecItem('Boost Clock', cpu.formattedBoostClock),
                    if (cpu.pCoreBoostClock != null)
                      _SpecItem(
                        'P-Core Boost',
                        '${(cpu.pCoreBoostClock! / 1000).toStringAsFixed(2)} GHz',
                      ),
                    if (cpu.eCoreBoostClock != null)
                      _SpecItem(
                        'E-Core Boost',
                        '${(cpu.eCoreBoostClock! / 1000).toStringAsFixed(2)} GHz',
                      ),
                  ],
                ),

                const SizedBox(height: 16),

                // Cache
                _buildSpecSection(
                  title: 'Cache',
                  icon: Icons.storage,
                  specs: [
                    if (cpu.l1Cache != null)
                      _SpecItem('L1 Cache', '${cpu.l1Cache} KB'),
                    if (cpu.l2Cache != null)
                      _SpecItem(
                        'L2 Cache',
                        cpu.l2Cache! >= 1024
                            ? '${(cpu.l2Cache! / 1024).toStringAsFixed(0)} MB'
                            : '${cpu.l2Cache} KB',
                      ),
                    _SpecItem('L3 Cache', cpu.formattedL3Cache),
                  ],
                ),

                const SizedBox(height: 16),

                // Power
                _buildSpecSection(
                  title: 'Power',
                  icon: Icons.bolt,
                  specs: [
                    _SpecItem('TDP', cpu.tdp != null ? '${cpu.tdp}W' : 'N/A'),
                    if (cpu.basePower != null)
                      _SpecItem('Base Power', '${cpu.basePower}W'),
                    if (cpu.maxTurboPower != null)
                      _SpecItem('Max Turbo Power', '${cpu.maxTurboPower}W'),
                  ],
                ),

                const SizedBox(height: 16),

                // Manufacturing
                _buildSpecSection(
                  title: 'Manufacturing',
                  icon: Icons.precision_manufacturing,
                  specs: [
                    _SpecItem('Process', cpu.processNode ?? 'N/A'),
                    if (cpu.transistorsMillion != null)
                      _SpecItem(
                        'Transistors',
                        '${cpu.transistorsMillion} million',
                      ),
                    if (cpu.dieSizeMm2 != null)
                      _SpecItem('Die Size', '${cpu.dieSizeMm2} mm²'),
                  ],
                ),

                const SizedBox(height: 16),

                // Memory Support
                if (cpu.memoryType != null || cpu.maxMemoryGb != null)
                  _buildSpecSection(
                    title: 'Memory Support',
                    icon: Icons.developer_board,
                    specs: [
                      if (cpu.memoryType != null)
                        _SpecItem('Memory Type', cpu.memoryType!),
                      if (cpu.memoryChannels != null)
                        _SpecItem('Memory Channels', '${cpu.memoryChannels}'),
                      if (cpu.maxMemoryGb != null)
                        _SpecItem('Max Memory', '${cpu.maxMemoryGb} GB'),
                    ],
                  ),

                if (cpu.memoryType != null || cpu.maxMemoryGb != null)
                  const SizedBox(height: 16),

                // Platform
                _buildSpecSection(
                  title: 'Platform',
                  icon: Icons.computer,
                  specs: [
                    _SpecItem('Socket', cpu.socketName ?? 'N/A'),
                    if (cpu.pcieVersion != null)
                      _SpecItem('PCIe', 'Gen ${cpu.pcieVersion}'),
                    if (cpu.pcieLanes != null)
                      _SpecItem('PCIe Lanes', '${cpu.pcieLanes}'),
                  ],
                ),

                const SizedBox(height: 16),

                // Graphics
                _buildSpecSection(
                  title: 'Graphics',
                  icon: Icons.videocam,
                  specs: [
                    _SpecItem(
                      'Integrated GPU',
                      cpu.hasIntegratedGpu ? 'Yes' : 'No',
                    ),
                    if (cpu.integratedGpuName != null)
                      _SpecItem('GPU Name', cpu.integratedGpuName!),
                  ],
                ),

                const SizedBox(height: 16),

                // Release Info
                _buildSpecSection(
                  title: 'Release Info',
                  icon: Icons.calendar_today,
                  specs: [
                    _SpecItem('Launch Date', cpu.launchDate ?? 'N/A'),
                    _SpecItem(
                      'MSRP',
                      cpu.launchMsrp != null
                          ? '\$${cpu.launchMsrp!.toStringAsFixed(0)}'
                          : 'N/A',
                    ),
                    _SpecItem(
                      'Status',
                      cpu.isDiscontinued
                          ? 'Discontinued'
                          : (cpu.isReleased ? 'Available' : 'Unreleased'),
                    ),
                  ],
                ),

                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildQuickSpecsCard(Cpu cpu) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildQuickSpec(
              icon: Icons.memory,
              label: 'Cores',
              value: cpu.isHybrid ? cpu.hybridCoreString : '${cpu.cores ?? '-'}',
            ),
            _buildQuickSpec(
              icon: Icons.speed,
              label: 'Boost',
              value: cpu.formattedBoostClock,
            ),
            _buildQuickSpec(
              icon: Icons.bolt,
              label: 'TDP',
              value: cpu.tdp != null ? '${cpu.tdp}W' : '-',
            ),
            _buildQuickSpec(
              icon: Icons.attach_money,
              label: 'MSRP',
              value: cpu.launchMsrp != null
                  ? '\$${cpu.launchMsrp!.toStringAsFixed(0)}'
                  : '-',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickSpec({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Column(
      children: [
        Icon(icon, size: 24, color: Theme.of(context).colorScheme.primary),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  Widget _buildSpecSection({
    required String title,
    required IconData icon,
    required List<_SpecItem> specs,
  }) {
    // Filter out specs with N/A values for cleaner display
    final filteredSpecs = specs.where((s) => s.value != 'N/A').toList();
    if (filteredSpecs.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const Divider(),
            ...filteredSpecs.map(
              (spec) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      spec.label,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    Text(
                      spec.value,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SpecItem {
  final String label;
  final String value;

  _SpecItem(this.label, this.value);
}
