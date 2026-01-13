class ApiConfig {
  // For development with Laragon (localhost)
  // Change this to your production server URL when deploying
  static const String baseUrl = 'http://localhost/hardwizchippy_api';

  // For Android emulator, use 10.0.2.2 instead of localhost
  static const String androidEmulatorUrl =
      'http://10.0.2.2/hardwizchippy_api';

  // For iOS simulator, localhost works fine
  static const String iosSimulatorUrl = 'http://localhost/hardwizchippy_api';

  // API Endpoints
  static const String cpusEndpoint = '/cpus';
  static const String manufacturersEndpoint = '/manufacturers';
  static const String socketsEndpoint = '/sockets';
  static const String familiesEndpoint = '/families';
  static const String healthEndpoint = '/health';

  // Timeout durations
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
