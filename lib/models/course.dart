enum ExerciseType { choice, typed, wordOrder }

class Exercise {
  Exercise({
    required this.id,
    required this.type,
    required this.prompt,
    required this.answer,
    this.acceptedAnswers = const [],
    this.options = const [],
    required this.explanation,
    this.context = '',
  });

  final String id;
  final ExerciseType type;
  final String prompt;
  final String answer;
  final List<String> acceptedAnswers;
  final List<String> options;
  final String explanation;
  final String context;

  static String normalize(String value) => value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'''[.,!?;:"“”'’¿¡]'''), '')
      .replaceAll(RegExp(r'\s+'), ' ');

  bool accepts(String input) {
    final normalized = normalize(input);
    return normalized.isNotEmpty &&
        [
          answer,
          ...acceptedAnswers,
        ].any((candidate) => normalize(candidate) == normalized);
  }

  factory Exercise.fromJson(Map<String, dynamic> json, {String context = ''}) {
    final exercise = Exercise(
      id: _text(json, 'id'),
      type: ExerciseType.values.byName(_text(json, 'type')),
      prompt: _text(json, 'prompt'),
      answer: _text(json, 'answer'),
      acceptedAnswers: _strings(json['acceptedAnswers'] ?? []),
      options: _strings(json['options'] ?? []),
      explanation: _text(json, 'explanation'),
      context: context,
    );
    if (Exercise.normalize(exercise.answer).isEmpty ||
        (exercise.type == ExerciseType.choice &&
            (exercise.options.length < 2 ||
                !exercise.options.any(exercise.accepts))) ||
        (exercise.type == ExerciseType.wordOrder &&
            !_sameWords(exercise.options, exercise.answer))) {
      throw FormatException('Exercício inválido: ${exercise.id}');
    }
    return exercise;
  }

  static bool _sameWords(List<String> options, String answer) {
    final expected = normalize(answer).split(' ')..sort();
    final actual = options.map(normalize).toList()..sort();
    return actual.isNotEmpty &&
        actual.length == expected.length &&
        List.generate(
          actual.length,
          (i) => actual[i] == expected[i],
        ).every((value) => value);
  }
}

class Lesson {
  Lesson({
    required this.id,
    required this.title,
    required this.description,
    required this.exercises,
    this.studyNotes = '',
    this.sourceIds = const [],
  });

  final String id;
  final String title;
  final String description;
  final List<Exercise> exercises;
  final String studyNotes;
  final List<String> sourceIds;

  factory Lesson.fromJson(Map<String, dynamic> json) {
    final passage = json.containsKey('readingPassage')
        ? _text(json, 'readingPassage')
        : '';
    return Lesson(
      id: _text(json, 'id'),
      title: _text(json, 'title'),
      description: _text(json, 'description'),
      studyNotes: json.containsKey('studyNotes')
          ? _text(json, 'studyNotes')
          : '',
      sourceIds: _strings(json['sourceIds'] ?? []),
      exercises: _objects(json, 'exercises')
          .map((exercise) => Exercise.fromJson(exercise, context: passage))
          .toList(growable: false),
    );
  }
}

class CourseUnit {
  CourseUnit({
    required this.id,
    required this.title,
    required this.description,
    required this.lessons,
  });

  final String id;
  final String title;
  final String description;
  final List<Lesson> lessons;

  factory CourseUnit.fromJson(Map<String, dynamic> json) => CourseUnit(
    id: _text(json, 'id'),
    title: _text(json, 'title'),
    description: _text(json, 'description'),
    lessons: _objects(
      json,
      'lessons',
    ).map(Lesson.fromJson).toList(growable: false),
  );
}

class Course {
  Course({
    required this.id,
    required this.title,
    required this.sourceLanguage,
    required this.targetLanguage,
    required this.level,
    required this.units,
    this.coverage = '',
    this.contentVersion = 1,
  });

  final String id;
  final String title;
  final String sourceLanguage;
  final String targetLanguage;
  final String level;
  final List<CourseUnit> units;
  final String coverage;
  final int contentVersion;

  List<Lesson> get lessons =>
      units.expand((unit) => unit.lessons).toList(growable: false);

  factory Course.fromJson(Map<String, dynamic> json) {
    final version = json['contentVersion'] ?? 1;
    if (version is! int || version < 1) {
      throw const FormatException('Versão de conteúdo inválida.');
    }
    final course = Course(
      id: _text(json, 'id'),
      title: _text(json, 'title'),
      sourceLanguage: _text(json, 'sourceLanguage'),
      targetLanguage: _text(json, 'targetLanguage'),
      level: _text(json, 'level'),
      coverage: json.containsKey('coverage') ? _text(json, 'coverage') : '',
      contentVersion: version,
      units: _objects(
        json,
        'units',
      ).map(CourseUnit.fromJson).toList(growable: false),
    );
    final ids = <String>{};
    for (final unit in course.units) {
      if (!ids.add(unit.id)) throw const FormatException('ID duplicado.');
      for (final lesson in unit.lessons) {
        if (!ids.add(lesson.id)) throw const FormatException('ID duplicado.');
        for (final exercise in lesson.exercises) {
          if (!ids.add(exercise.id)) {
            throw const FormatException('ID duplicado.');
          }
        }
      }
    }
    return course;
  }
}

String _text(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String || value.trim().isEmpty) {
    throw FormatException('Campo inválido: $key');
  }
  return value;
}

List<String> _strings(dynamic value) {
  if (value is! List ||
      value.any((item) => item is! String || item.trim().isEmpty)) {
    throw const FormatException('Lista de textos inválida.');
  }
  return List<String>.unmodifiable(value.cast<String>());
}

List<Map<String, dynamic>> _objects(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! List || value.isEmpty) {
    throw FormatException('Lista inválida: $key');
  }
  return value
      .map((item) {
        if (item is! Map<String, dynamic>) {
          throw FormatException('Objeto inválido: $key');
        }
        return item;
      })
      .toList(growable: false);
}
