import 'dart:math';

enum FeedbackCategory { correct, incorrect }

class FeedbackClip {
  const FeedbackClip({
    required this.id,
    required this.category,
    required this.text,
    required this.assetPath,
  });

  final String id;
  final FeedbackCategory category;
  final String text;
  final String assetPath;
}

class FeedbackTheme {
  FeedbackTheme({
    required this.id,
    required this.name,
    required this.description,
    required List<FeedbackClip> clips,
  }) : clips = List.unmodifiable(clips);

  final String id;
  final String name;
  final String description;
  final List<FeedbackClip> clips;
}

class FeedbackCatalog {
  FeedbackCatalog(List<FeedbackTheme> themes)
      : themes = List.unmodifiable(themes);

  static const off = 'off';
  final List<FeedbackTheme> themes;

  FeedbackTheme? theme(String id) {
    for (final theme in themes) {
      if (theme.id == id) return theme;
    }
    return null;
  }

  factory FeedbackCatalog.fromJson(Map<String, dynamic> json) {
    final items = json['themes'];
    if (json['schemaVersion'] != 1 || items is! List || items.isEmpty) {
      throw const FormatException('Catálogo de feedback inválido.');
    }
    final themes = <FeedbackTheme>[];
    final themeIds = <String>{};
    for (final item in items) {
      if (item is! Map<String, dynamic>) {
        throw const FormatException('Tema inválido.');
      }
      final id = _id(item['id']);
      if (id == off || !themeIds.add(id)) {
        throw const FormatException('ID de tema reservado ou duplicado.');
      }
      final entries = item['clips'];
      if (entries is! List || entries.isEmpty) {
        throw const FormatException('Tema sem frases.');
      }
      final clips = <FeedbackClip>[];
      final clipIds = <String>{};
      for (final entry in entries) {
        if (entry is! Map<String, dynamic>) {
          throw const FormatException('Frase inválida.');
        }
        final clipId = _id(entry['id']);
        if (!clipIds.add(clipId)) {
          throw const FormatException('ID de frase duplicado.');
        }
        final category = switch (entry['category']) {
          'correct' => FeedbackCategory.correct,
          'incorrect' => FeedbackCategory.incorrect,
          _ => throw const FormatException('Categoria desconhecida.'),
        };
        clips.add(FeedbackClip(
          id: clipId,
          category: category,
          text: _text(entry['text']),
          assetPath: 'assets/audio_feedback/${id}_$clipId.mp3',
        ));
      }
      if (!FeedbackCategory.values.every(
          (category) => clips.any((clip) => clip.category == category))) {
        throw const FormatException('Tema deve ter frases de acerto e erro.');
      }
      themes.add(FeedbackTheme(
        id: id,
        name: _text(item['name']),
        description: _text(item['description']),
        clips: clips,
      ));
    }
    final paths = themes.expand((theme) => theme.clips).map((c) => c.assetPath);
    if (paths.toSet().length != paths.length) {
      throw const FormatException('Nomes de arquivos de áudio duplicados.');
    }
    return FeedbackCatalog(themes);
  }

  static String _id(dynamic value) {
    if (value is! String ||
        value.length > 64 ||
        !RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(value)) {
      throw const FormatException('ID de feedback inválido.');
    }
    return value;
  }

  static String _text(dynamic value) {
    if (value is! String || value.trim().isEmpty || value.length > 500) {
      throw const FormatException('Texto de feedback inválido.');
    }
    return value.trim();
  }
}

class FeedbackPicker {
  FeedbackPicker({Random? random}) : _random = random ?? Random();

  final Random _random;
  final Map<String, String> _previous = {};

  FeedbackClip pick(FeedbackTheme theme, FeedbackCategory category) {
    final key = '${theme.id}/${category.name}';
    final clips = theme.clips.where((clip) => clip.category == category).toList();
    final candidates = clips.length > 1
        ? clips.where((clip) => clip.id != _previous[key]).toList()
        : clips;
    final selected = candidates[_random.nextInt(candidates.length)];
    _previous[key] = selected.id;
    return selected;
  }
}
