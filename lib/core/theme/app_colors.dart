import 'package:flutter/material.dart';

/// Application color palette
class AppColors {
  AppColors._();

  // Brand Colors
  static const Color primary = Color(0xFF1E88E5); // Blue
  static const Color secondary = Color(0xFF26A69A); // Teal
  static const Color accent = Color(0xFFFF7043); // Deep Orange

  // Manufacturer Colors
  static const Color amd = Color(0xFFED1C24);
  static const Color intel = Color(0xFF0071C5);

  // Light Theme Colors
  static const Color backgroundLight = Color(0xFFF5F5F5);
  static const Color surfaceLight = Colors.white;
  static const Color textPrimaryLight = Color(0xFF212121);
  static const Color textSecondaryLight = Color(0xFF757575);

  // Dark Theme Colors
  static const Color backgroundDark = Color(0xFF121212);
  static const Color surfaceDark = Color(0xFF1E1E1E);
  static const Color textPrimaryDark = Color(0xFFE0E0E0);
  static const Color textSecondaryDark = Color(0xFF9E9E9E);

  /// Get manufacturer color by name
  static Color getManufacturerColor(String manufacturer) {
    switch (manufacturer.toLowerCase()) {
      case 'amd':
        return amd;
      case 'intel':
        return intel;
      default:
        return primary;
    }
  }
}
