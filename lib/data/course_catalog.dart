import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/course.dart';

class CourseCatalog {
  static Future<List<Course>> load({AssetBundle? bundle}) async {
    final assets = bundle ?? rootBundle;
    final manifest =
        jsonDecode(await assets.loadString('assets/courses/catalog.json'));
    if (manifest is! Map<String, dynamic> ||
        manifest['courses'] is! List ||
        (manifest['courses'] as List).isEmpty) {
      throw const FormatException('Catálogo inválido.');
    }
    final courses = <Course>[];
    final ids = <String>{};
    for (final path in manifest['courses'] as List) {
      if (path is! String ||
          !path.startsWith('assets/courses/') ||
          path.contains('..')) {
        throw const FormatException('Caminho de curso inválido.');
      }
      final json = jsonDecode(await assets.loadString(path));
      if (json is! Map<String, dynamic>) {
        throw const FormatException('Curso inválido.');
      }
      final course = Course.fromJson(json);
      if (!ids.add(course.id)) {
        throw const FormatException('Curso duplicado.');
      }
      courses.add(course);
    }
    return List.unmodifiable(courses);
  }
}
