import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/core.dart';
import '../models/models.dart';
import '../providers/providers.dart';

/// Clean, CPU-L style CPU card with performance optimizations
class CpuCard extends StatelessWidget {
  final Cpu cpu;
  final VoidCallback? onTap;

  const CpuCard({
    super.key,
    required this.cpu,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: _CpuCardContent(cpu: cpu, onTap: onTap),
    );
  }
}

class _CpuCardContent extends StatelessWidget {
  final Cpu cpu;
  final VoidCallback? onTap;

  const _CpuCardContent({required this.cpu, this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final manufacturerColor = AppColors.getManufacturerColor(
      cpu.manufacturerName ?? '',
    );

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: isDark ? 0 : 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isDark
            ? BorderSide(color: Colors.grey.shade800, width: 1)
            : BorderSide.none,
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Manufacturer color bar
              Container(
                width: 4,
                height: 56,
                decoration: BoxDecoration(
                  color: manufacturerColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 12),

              // Main content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // CPU Name
                    Text(
                      cpu.name,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: isDark ? Colors.white : Colors.black87,
                        height: 1.2,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),

                    // Specs row
                    _buildSpecsRow(context, isDark),

                    // Additional info
                    if (_hasAdditionalInfo) ...[
                      const SizedBox(height: 8),
                      _buildInfoRow(context, isDark),
                    ],
                  ],
                ),
              ),

              // Favorite button
              _FavoriteButton(cpuId: cpu.id),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSpecsRow(BuildContext context, bool isDark) {
    final textColor = isDark ? Colors.grey.shade400 : Colors.grey.shade600;
    final specs = <String>[];

    if (cpu.cores != null) {
      specs.add('${cpu.cores}C${cpu.threads != null && cpu.threads != cpu.cores ? "/${cpu.threads}T" : ""}');
    }

    if (cpu.boostClock != null) {
      final ghz = cpu.boostClock! / 1000;
      specs.add('${ghz.toStringAsFixed(1)} GHz');
    }

    if (cpu.tdp != null) {
      specs.add('${cpu.tdp}W');
    }

    return Text(
      specs.join(' • '),
      style: TextStyle(
        fontSize: 13,
        color: textColor,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  Widget _buildInfoRow(BuildContext context, bool isDark) {
    final chipBg = isDark
        ? Colors.grey.shade800
        : Colors.grey.shade100;
    final chipFg = isDark
        ? Colors.grey.shade400
        : Colors.grey.shade700;

    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: [
        if (cpu.processNode != null)
          _InfoChip(label: cpu.processNode!, bgColor: chipBg, fgColor: chipFg),
        if (cpu.l3Cache != null)
          _InfoChip(label: cpu.formattedL3Cache, bgColor: chipBg, fgColor: chipFg),
        if (cpu.socketName != null && cpu.socketName!.isNotEmpty)
          _InfoChip(label: cpu.socketName!, bgColor: chipBg, fgColor: chipFg),
        if (cpu.hasIntegratedGpu)
          _InfoChip(
            label: 'iGPU',
            bgColor: isDark ? Colors.green.shade900.withValues(alpha: 0.5) : Colors.green.shade50,
            fgColor: isDark ? Colors.green.shade300 : Colors.green.shade700,
          ),
      ],
    );
  }

  bool get _hasAdditionalInfo =>
      cpu.processNode != null ||
      cpu.l3Cache != null ||
      (cpu.socketName != null && cpu.socketName!.isNotEmpty) ||
      cpu.hasIntegratedGpu;
}

/// Optimized favorite button with Selector
class _FavoriteButton extends StatelessWidget {
  final int cpuId;

  const _FavoriteButton({required this.cpuId});

  @override
  Widget build(BuildContext context) {
    return Selector<CpuProvider, bool>(
      selector: (_, provider) => provider.isFavorite(cpuId),
      builder: (context, isFavorite, child) {
        return GestureDetector(
          onTap: () => context.read<CpuProvider>().toggleFavorite(cpuId),
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              transitionBuilder: (child, animation) {
                return ScaleTransition(scale: animation, child: child);
              },
              child: Icon(
                isFavorite ? Icons.favorite_rounded : Icons.favorite_outline_rounded,
                key: ValueKey(isFavorite),
                color: isFavorite ? Colors.red.shade400 : Colors.grey.shade400,
                size: 22,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Small info chip
class _InfoChip extends StatelessWidget {
  final String label;
  final Color bgColor;
  final Color fgColor;

  const _InfoChip({
    required this.label,
    required this.bgColor,
    required this.fgColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          color: fgColor,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
