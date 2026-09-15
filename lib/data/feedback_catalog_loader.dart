import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/feedback_catalog.dart';

class FeedbackCatalogLoader {
  static Future<FeedbackCatalog> load({AssetBundle? bundle}) async {
    final json = jsonDecode(await (bundle ?? rootBundle)
        .loadString('assets/audio_feedback/catalog.json'));
    if (json is! Map<String, dynamic>) {
      throw const FormatException('Catálogo de feedback inválido.');
    }
    return FeedbackCatalog.fromJson(json);
  }
}
