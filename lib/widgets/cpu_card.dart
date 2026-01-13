import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/theme.dart';
import '../models/cpu.dart';
import '../providers/cpu_provider.dart';

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
    final manufacturerColor = AppTheme.getManufacturerColor(
      cpu.manufacturerName ?? '',
    );

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row with name and favorite button
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Manufacturer indicator
                  Container(
                    width: 4,
                    height: 48,
                    decoration: BoxDecoration(
                      color: manufacturerColor,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // CPU name and details
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          cpu.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${cpu.manufacturerName ?? ''} ${cpu.socketName != null ? '• ${cpu.socketName}' : ''}',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Favorite button
                  Consumer<CpuProvider>(
                    builder: (context, provider, child) {
                      final isFavorite = provider.isFavorite(cpu.id);
                      return IconButton(
                        icon: Icon(
                          isFavorite ? Icons.favorite : Icons.favorite_outline,
                          color: isFavorite ? Colors.red : Colors.grey,
                        ),
                        onPressed: () => provider.toggleFavorite(cpu.id),
                      );
                    },
                  ),
                ],
              ),

              const SizedBox(height: 12),

              // Specs row
              Row(
                children: [
                  _buildSpecChip(
                    icon: Icons.memory,
                    label: cpu.coreThreadString,
                  ),
                  const SizedBox(width: 8),
                  if (cpu.boostClock != null)
                    _buildSpecChip(
                      icon: Icons.speed,
                      label: cpu.formattedBoostClock,
                    ),
                  const SizedBox(width: 8),
                  if (cpu.tdp != null)
                    _buildSpecChip(
                      icon: Icons.bolt,
                      label: '${cpu.tdp}W',
                    ),
                ],
              ),

              // Additional info row
              if (cpu.processNode != null || cpu.l3Cache != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (cpu.processNode != null)
                      _buildInfoChip(cpu.processNode!),
                    if (cpu.l3Cache != null) ...[
                      const SizedBox(width: 8),
                      _buildInfoChip('L3: ${cpu.formattedL3Cache}'),
                    ],
                    if (cpu.hasIntegratedGpu) ...[
                      const SizedBox(width: 8),
                      _buildInfoChip('iGPU'),
                    ],
                  ],
                ),
              ],

              // Price if available
              if (cpu.launchMsrp != null) ...[
                const SizedBox(height: 8),
                Text(
                  'MSRP: \$${cpu.launchMsrp!.toStringAsFixed(0)}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Colors.green.shade700,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSpecChip({required IconData icon, required String label}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.grey.shade700),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade700,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          color: Colors.blue.shade700,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
