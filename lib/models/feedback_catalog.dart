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

class FeedbackVoice {
  FeedbackVoice({
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
  FeedbackCatalog(List<FeedbackVoice> voices)
    : voices = List.unmodifiable(voices);

  static const off = 'off';
  final List<FeedbackVoice> voices;

  FeedbackVoice? voice(String id) {
    for (final voice in voices) {
      if (voice.id == id) return voice;
    }
    return null;
  }

  factory FeedbackCatalog.fromJson(Map<String, dynamic> json) {
    final items = json['voices'];
    if (json['schemaVersion'] != 2 || items is! List || items.isEmpty) {
      throw const FormatException('Catálogo de feedback inválido.');
    }
    final voices = <FeedbackVoice>[];
    final voiceIds = <String>{};
    for (final item in items) {
      if (item is! Map<String, dynamic>) {
        throw const FormatException('Voz inválida.');
      }
      final id = _id(item['id']);
      if (id == off || !voiceIds.add(id)) {
        throw const FormatException('ID de voz reservado ou duplicado.');
      }
      final entries = item['clips'];
      if (entries is! List || entries.isEmpty) {
        throw const FormatException('Voz sem frases.');
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
        clips.add(
          FeedbackClip(
            id: clipId,
            category: category,
            text: _text(entry['text']),
            assetPath: 'assets/audio_feedback/${id}_$clipId.mp3',
          ),
        );
      }
      if (!FeedbackCategory.values.every(
        (category) => clips.any((clip) => clip.category == category),
      )) {
        throw const FormatException('Voz deve ter frases de acerto e erro.');
      }
      voices.add(
        FeedbackVoice(
          id: id,
          name: _text(item['name']),
          description: _text(item['description']),
          clips: clips,
        ),
      );
    }
    final paths = voices.expand((voice) => voice.clips).map((c) => c.assetPath);
    if (paths.toSet().length != paths.length) {
      throw const FormatException('Nomes de arquivos de áudio duplicados.');
    }
    return FeedbackCatalog(voices);
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

  FeedbackClip pick(FeedbackVoice voice, FeedbackCategory category) {
    final key = '${voice.id}/${category.name}';
    final clips = voice.clips
        .where((clip) => clip.category == category)
        .toList();
    final candidates = clips.length > 1
        ? clips.where((clip) => clip.id != _previous[key]).toList()
        : clips;
    final selected = candidates[_random.nextInt(candidates.length)];
    _previous[key] = selected.id;
    return selected;
  }
}
