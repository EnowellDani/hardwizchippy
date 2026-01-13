import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/theme_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // App Info Section
          _buildSectionHeader(context, 'About'),
          _buildAppInfoTile(context),

          const Divider(),

          // Theme Section
          _buildSectionHeader(context, 'Appearance'),
          _buildThemeTile(context),

          const Divider(),

          // Data Section
          _buildSectionHeader(context, 'Data'),
          _buildDataSourceTile(context),

          const Divider(),

          // Developer Section
          _buildSectionHeader(context, 'Developer'),
          _buildDeveloperTile(context),

          const SizedBox(height: 32),

          // Version info
          Center(
            child: Text(
              'HardWizChippy v1.0.0',
              style: TextStyle(
                color: Colors.grey.shade500,
                fontSize: 12,
              ),
            ),
          ),
          Center(
            child: Text(
              'Made with spite by KBitWare',
              style: TextStyle(
                color: Colors.grey.shade500,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: TextStyle(
          color: Theme.of(context).colorScheme.primary,
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildAppInfoTile(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(
          Icons.memory,
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
      title: const Text('HardWizChippy'),
      subtitle: const Text('Ad-free CPU/GPU/SoC database'),
    );
  }

  Widget _buildThemeTile(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return RadioGroup<ThemeMode>(
          groupValue: themeProvider.themeMode,
          onChanged: (value) {
            if (value != null) themeProvider.setThemeMode(value);
          },
          child: Column(
            children: [
              RadioListTile<ThemeMode>(
                title: const Text('System default'),
                subtitle: const Text('Follow system theme'),
                value: ThemeMode.system,
              ),
              RadioListTile<ThemeMode>(
                title: const Text('Light'),
                subtitle: const Text('Always use light theme'),
                value: ThemeMode.light,
              ),
              RadioListTile<ThemeMode>(
                title: const Text('Dark'),
                subtitle: const Text('Always use dark theme'),
                value: ThemeMode.dark,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDataSourceTile(BuildContext context) {
    return ListTile(
      leading: const Icon(Icons.storage),
      title: const Text('Data Source'),
      subtitle: const Text('TechPowerUp CPU Database'),
      trailing: const Icon(Icons.open_in_new),
      onTap: () async {
        final uri = Uri.parse('https://www.techpowerup.com/cpu-specs/');
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
      },
    );
  }

  Widget _buildDeveloperTile(BuildContext context) {
    return ListTile(
      leading: const Icon(Icons.code),
      title: const Text('KBitWare'),
      subtitle: const Text('Developer'),
      trailing: const Icon(Icons.open_in_new),
      onTap: () {
        // TODO: Add KBitWare website/GitHub link
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('KBitWare - Coming soon!'),
          ),
        );
      },
    );
  }
}
