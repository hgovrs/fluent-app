import 'dart:convert';

import 'package:flutter/services.dart';

class ContentSource {
  const ContentSource({
    required this.id,
    required this.title,
    required this.institution,
    required this.authors,
    required this.url,
    required this.license,
    required this.licenseUrl,
    required this.description,
    required this.limitations,
  });

  final String id;
  final String title;
  final String institution;
  final String authors;
  final String url;
  final String license;
  final String licenseUrl;
  final String description;
  final String limitations;

  factory ContentSource.fromJson(Map<String, dynamic> json) {
    String text(String key) {
      final value = json[key];
      if (value is! String || value.trim().isEmpty) {
        throw FormatException('Referência inválida: $key');
      }
      return value;
    }

    String link(String key) {
      final value = text(key);
      final uri = Uri.tryParse(value);
      if (uri == null ||
          uri.scheme != 'https' ||
          uri.host.isEmpty ||
          uri.userInfo.isNotEmpty) {
        throw FormatException('Link de referência inválido: $key');
      }
      return value;
    }

    return ContentSource(
      id: text('id'),
      title: text('title'),
      institution: text('institution'),
      authors: text('authors'),
      url: link('url'),
      license: text('license'),
      licenseUrl: link('licenseUrl'),
      description: text('description'),
      limitations: text('limitations'),
    );
  }

  static Future<List<ContentSource>> load({AssetBundle? bundle}) async {
    final json = jsonDecode(
      await (bundle ?? rootBundle).loadString('assets/content/sources.json'),
    );
    if (json is! Map<String, dynamic> ||
        json['schemaVersion'] != 1 ||
        json['sources'] is! List ||
        (json['sources'] as List).isEmpty) {
      throw const FormatException('Registro de fontes inválido.');
    }
    final result = <ContentSource>[];
    final ids = <String>{};
    for (final item in json['sources'] as List) {
      if (item is! Map<String, dynamic>) {
        throw const FormatException('Referência inválida.');
      }
      final source = ContentSource.fromJson(item);
      if (!ids.add(source.id)) {
        throw const FormatException('Referência duplicada.');
      }
      result.add(source);
    }
    return List.unmodifiable(result);
  }
}
