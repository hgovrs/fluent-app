import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../lib/data/course_catalog.dart';
import '../lib/models/course.dart';
import '../lib/models/learning_progress.dart';
import '../lib/services/progress_store.dart';

class _DiskAssets extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async {
    final bytes = await File(key).readAsBytes();
    return ByteData.sublistView(bytes);
  }
}

void main() {
  group('conteúdo original do catálogo', () {
    test('carrega quatro unidades e doze lições completas', () async {
      final courses = await CourseCatalog.load(bundle: _DiskAssets());
      expect(courses, hasLength(1));
      final course = courses.single;
      expect(course.sourceLanguage, 'pt-BR');
      expect(course.targetLanguage, 'en');
      expect(course.units, hasLength(4));
      expect(course.lessons, hasLength(12));
      final ids = <String>{};
      for (final lesson in course.lessons) {
        expect(lesson.exercises.length, greaterThanOrEqualTo(5));
        expect(lesson.exercises.map((e) => e.type).toSet(),
            containsAll(ExerciseType.values));
        for (final exercise in lesson.exercises) {
          expect(ids.add(exercise.id), isTrue);
          expect(exercise.accepts(exercise.answer), isTrue);
          expect(exercise.accepts('resposta incorreta'), isFalse);
          expect(exercise.explanation, isNotEmpty);
          for (final answer in exercise.acceptedAnswers) {
            expect(exercise.accepts(answer), isTrue);
          }
        }
      }
      expect(ids.length, greaterThanOrEqualTo(60));
    });

    test('rejeita IDs duplicados e perguntas sem opção correta', () {
      final json = jsonDecode(
          File('assets/courses/en_starter.json').readAsStringSync())
          as Map<String, dynamic>;
      final exercises = json['units'][0]['lessons'][0]['exercises'] as List;
      exercises[1]['id'] = exercises[0]['id'];
      expect(() => Course.fromJson(json), throwsFormatException);
      expect(
        () => Exercise.fromJson({
          'id': 'bad',
          'type': 'choice',
          'prompt': 'Escolha',
          'answer': 'yes',
          'options': ['no', 'maybe'],
          'explanation': 'Sim.',
        }),
        throwsFormatException,
      );
    });

    test('ordenação valida o conjunto de palavras, inclusive repetidas', () {
      final json = <String, dynamic>{
        'id': 'order',
        'type': 'wordOrder',
        'prompt': 'Monte a frase',
        'answer': 'I am what I am',
        'options': ['am', 'what', 'I', 'am', 'I'],
        'explanation': 'As palavras repetidas também são necessárias.',
      };
      expect(Exercise.fromJson(json).accepts('I am what I am.'), isTrue);
      json['options'] = ['am', 'what', 'I'];
      expect(() => Exercise.fromJson(json), throwsFormatException);
    });
  });

  group('respostas determinísticas', () {
    final exercise = Exercise(
      id: 'answer',
      type: ExerciseType.typed,
      prompt: 'Eu sou Ana.',
      answer: 'I am Ana',
      acceptedAnswers: ["I'm Ana"],
      explanation: 'As duas formas estão corretas.',
    );

    test('aceita espaços, caixa, pontuação e contração explícita', () {
      for (final answer in [
        '  I AM ANA! ',
        'I   am\nAna.',
        '“I am Ana.”',
        "I'm Ana",
        'I’m Ana',
      ]) {
        expect(exercise.accepts(answer), isTrue, reason: answer);
      }
    });

    test('não usa correspondência parcial nem aproximação', () {
      for (final answer in ['', '!!!', 'Ana', 'I am Anna', 'Ana am I']) {
        expect(exercise.accepts(answer), isFalse, reason: answer);
      }
    });
  });

  group('progresso e calendário', () {
    test('serialização mantém todos os dados e usa somente JSON', () {
      final progress = LearningProgress(
        totalXp: 70,
        dailyGoal: 40,
        completedLessonIds: {'lesson'},
        activity: {'2026-09-10': 70},
        reviews: {
          'exercise': const ReviewSchedule(
              dueDate: '2026-09-11', intervalDays: 1, successCount: 0),
        },
        reviewedCount: 2,
        now: () => DateTime(2026, 9, 10),
      );
      final saved = jsonDecode(jsonEncode(progress.toJson()))
          as Map<String, dynamic>;
      final restored = LearningProgress.fromJson(
          saved, now: () => DateTime(2026, 9, 10));
      expect(restored.toJson(), progress.toJson());
      expect(restored.dailyXp, 70);
      expect(restored.streak, 1);
      expect(() => restored.completedLessonIds.add('other'),
          throwsUnsupportedError);
    });

    test('sequência permanece ontem, expira após um dia perdido', () {
      var now = DateTime(2026, 9, 10, 23, 59);
      final progress = LearningProgress(
        activity: {'2026-09-09': 20, '2026-09-10': 0},
        now: () => now,
      );
      expect(progress.streak, 2);
      now = DateTime(2026, 9, 11);
      expect(progress.streak, 2);
      expect(progress.dailyXp, 0);
      now = DateTime(2026, 9, 12);
      expect(progress.streak, 0);
    });

    test('calendário atravessa ano, fevereiro bissexto e mudanças de hora', () {
      for (final example in [
        ['2025-12-31', '2026-01-01'],
        ['2024-02-29', '2024-03-01'],
        ['2026-03-08', '2026-03-09'],
        ['2026-11-01', '2026-11-02'],
      ]) {
        final date = parseCalendarDate(example.last);
        final progress = LearningProgress(
          activity: {example.first: 0, example.last: 10},
          now: () => DateTime(date.year, date.month, date.day, 23, 59),
        );
        expect(progress.streak, 2, reason: example.join(', '));
      }
      expect(() => parseCalendarDate('2026-02-30'), throwsFormatException);
      expect(() => parseCalendarDate('2026-2-1'), throwsFormatException);
      expect(calendarDate(calendarDay(DateTime(2026, 3, 8, 23))
          .add(const Duration(days: 1))), '2026-03-09');
    });

    test('rejeita dados armazenados negativos, fracionados e malformados', () {
      for (final invalid in [
        {'totalXp': -1},
        {'totalXp': 2.5},
        {'dailyGoal': 0},
        {'dailyGoal': 1001},
        {'completedLessonIds': [42]},
        {'activity': {'2026-02-30': 10}},
        {'activity': {'2026-09-10': -5}},
        {'reviews': {'e': null}},
        {
          'reviews': {
            'e': {'dueDate': '2026-09-10', 'intervalDays': 31, 'successCount': 1}
          }
        },
        {'reviewedCount': 'five'},
      ]) {
        expect(
          () => LearningProgress.fromJson(
              {...LearningProgress().toJson(), ...invalid}),
          throwsFormatException,
          reason: invalid.toString(),
        );
      }
    });
  });

  group('armazenamento offline', () {
    test('ida e volta e escritas em ordem', () async {
      String? saved;
      final writes = <int>[];
      final store = ProgressStore(
        read: () async => saved,
        write: (value) async {
          await Future<void>.delayed(Duration.zero);
          saved = value;
          writes.add((jsonDecode(value) as Map)['value'] as int);
          return true;
        },
      );
      expect(await store.load(), isNull);
      await Future.wait([store.save({'value': 1}), store.save({'value': 2})]);
      expect(writes, [1, 2]);
      expect(await store.load(), {'value': 2});
    });

    test('falha de escrita não impede próxima tentativa', () async {
      var attempts = 0;
      final store = ProgressStore(
        read: () async => null,
        write: (_) async => ++attempts > 1,
      );
      await expectLater(store.save({'value': 1}), throwsStateError);
      await store.save({'value': 2});
      expect(attempts, 2);
    });

    test('rejeita JSON quebrado ou envelope que não é objeto', () async {
      for (final raw in ['{invalid', '[]', 'null', '"hello"']) {
        final store = ProgressStore(read: () async => raw);
        await expectLater(store.load(), throwsFormatException);
      }
    });
  });
}
