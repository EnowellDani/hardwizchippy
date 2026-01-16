import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../core/core.dart';
import '../models/models.dart';

/// Custom exception for API errors
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// Service for handling API requests
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String get baseUrl {
    if (kIsWeb) {
      return ApiConstants.baseUrl;
    }
    if (Platform.isAndroid) {
      return ApiConstants.androidEmulatorUrl;
    }
    return ApiConstants.baseUrl;
  }

  Future<Map<String, dynamic>> _get(String endpoint,
      {Map<String, String>? queryParams}) async {
    try {
      final uri = Uri.parse('$baseUrl$endpoint').replace(
        queryParameters: queryParams,
      );

      final response = await http
          .get(uri)
          .timeout(ApiConstants.connectionTimeout);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        final errorBody = json.decode(response.body);
        throw ApiException(
          errorBody['message'] ?? 'Request failed',
          statusCode: response.statusCode,
        );
      }
    } on SocketException {
      throw ApiException('No internet connection. Please check your network.');
    } on FormatException {
      throw ApiException('Invalid response from server.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('An unexpected error occurred: $e');
    }
  }

  // CPU Endpoints

  Future<PaginatedResponse<Cpu>> getCpus({
    int page = 1,
    int limit = 20,
    int? manufacturerId,
    int? socketId,
    int? minCores,
    int? maxCores,
    int? minTdp,
    int? maxTdp,
    bool? hasIgpu,
    String sortBy = 'name',
    String sortOrder = 'ASC',
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'limit': limit.toString(),
      'sort_by': sortBy,
      'sort_order': sortOrder,
    };

    if (manufacturerId != null) {
      queryParams['manufacturer_id'] = manufacturerId.toString();
    }
    if (socketId != null) {
      queryParams['socket_id'] = socketId.toString();
    }
    if (minCores != null) {
      queryParams['min_cores'] = minCores.toString();
    }
    if (maxCores != null) {
      queryParams['max_cores'] = maxCores.toString();
    }
    if (minTdp != null) {
      queryParams['min_tdp'] = minTdp.toString();
    }
    if (maxTdp != null) {
      queryParams['max_tdp'] = maxTdp.toString();
    }
    if (hasIgpu != null) {
      queryParams['has_igpu'] = hasIgpu.toString();
    }

    final response = await _get(ApiConstants.cpusEndpoint, queryParams: queryParams);

    final data = (response['data'] as List)
        .map((json) => Cpu.fromJson(json))
        .toList();

    final pagination = response['pagination'] as Map<String, dynamic>;

    return PaginatedResponse(
      data: data,
      currentPage: pagination['current_page'] as int,
      perPage: pagination['per_page'] as int,
      total: pagination['total'] as int,
      totalPages: pagination['total_pages'] as int,
    );
  }

  Future<Cpu> getCpuById(int id) async {
    final response = await _get('${ApiConstants.cpusEndpoint}/$id');
    return Cpu.fromJson(response['data']);
  }

  Future<PaginatedResponse<Cpu>> searchCpus(
    String query, {
    int page = 1,
    int limit = 20,
  }) async {
    final queryParams = {
      'q': query,
      'page': page.toString(),
      'limit': limit.toString(),
    };

    final response =
        await _get('${ApiConstants.cpusEndpoint}/search', queryParams: queryParams);

    final data = (response['data'] as List)
        .map((json) => Cpu.fromJson(json))
        .toList();

    final pagination = response['pagination'] as Map<String, dynamic>;

    return PaginatedResponse(
      data: data,
      currentPage: pagination['current_page'] as int,
      perPage: pagination['per_page'] as int,
      total: pagination['total'] as int,
      totalPages: pagination['total_pages'] as int,
    );
  }

  // Manufacturer Endpoints

  Future<List<Manufacturer>> getManufacturers() async {
    final response = await _get(ApiConstants.manufacturersEndpoint);
    return (response['data'] as List)
        .map((json) => Manufacturer.fromJson(json))
        .toList();
  }

  // Socket Endpoints

  Future<List<Socket>> getSockets({int? manufacturerId}) async {
    final queryParams = <String, String>{};
    if (manufacturerId != null) {
      queryParams['manufacturer_id'] = manufacturerId.toString();
    }

    final response =
        await _get(ApiConstants.socketsEndpoint, queryParams: queryParams);
    return (response['data'] as List)
        .map((json) => Socket.fromJson(json))
        .toList();
  }

  // Family Endpoints

  Future<List<CpuFamily>> getFamilies({int? manufacturerId}) async {
    final queryParams = <String, String>{};
    if (manufacturerId != null) {
      queryParams['manufacturer_id'] = manufacturerId.toString();
    }

    final response =
        await _get(ApiConstants.familiesEndpoint, queryParams: queryParams);
    return (response['data'] as List)
        .map((json) => CpuFamily.fromJson(json))
        .toList();
  }

  // Health Check

  Future<bool> healthCheck() async {
    try {
      final response = await _get(ApiConstants.healthEndpoint);
      return response['status'] == 'ok';
    } catch (e) {
      return false;
    }
  }
}
