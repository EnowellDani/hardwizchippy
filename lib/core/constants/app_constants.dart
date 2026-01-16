/// Application-wide constants
class AppConstants {
  AppConstants._();

  /// Application name
  static const String appName = 'HardWizChippy';

  /// Application description
  static const String appDescription =
      'Your ad-free CPU, GPU and SoC specifications database by KBitWare';

  /// Application version
  static const String appVersion = '1.0.0';

  /// Default animation duration
  static const Duration defaultAnimationDuration = Duration(milliseconds: 300);

  /// Default page size for pagination
  static const int defaultPageSize = 20;

  /// Maximum cache age in days
  static const int maxCacheAgeDays = 7;
}
