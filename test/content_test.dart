import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fluent_app/data/content_sources.dart';
import 'package:fluent_app/data/course_catalog.dart';
import 'package:fluent_app/models/course.dart';

class _ContentAssets extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async =>
      ByteData.sublistView(await File(key).readAsBytes());
}

void main() {
  test(
    'trilhas A1–C1 têm estudo, referências e respostas consistentes',
    () async {
      final courses = await CourseCatalog.load(bundle: _ContentAssets());
      final sources = await ContentSource.load(bundle: _ContentAssets());
      final sourceIds = sources.map((source) => source.id).toSet();
      expect(courses.map((course) => course.id), [
        'en-starter',
        'en-a1',
        'en-a2',
        'en-b1',
        'en-b2',
        'en-c1',
      ]);
      for (final course in courses.skip(1)) {
        expect(course.contentVersion, 1);
        expect(course.coverage, isNotEmpty);
        expect(course.units, hasLength(4));
        expect(course.lessons, hasLength(12));
        for (final lesson in course.lessons) {
          expect(lesson.studyNotes, isNotEmpty, reason: lesson.id);
          expect(
            lesson.sourceIds.every(sourceIds.contains),
            isTrue,
            reason: lesson.id,
          );
          expect(lesson.exercises, hasLength(6));
          expect(
            lesson.exercises.map((e) => e.type).toSet(),
            containsAll(ExerciseType.values),
          );
          for (final exercise in lesson.exercises) {
            if (course.id == 'en-b2' || course.id == 'en-c1') {
              expect(exercise.context, isNotEmpty, reason: exercise.id);
            }
            expect(
              exercise.accepts(exercise.answer),
              isTrue,
              reason: exercise.id,
            );
            expect(exercise.accepts(''), isFalse);
            if (exercise.type == ExerciseType.choice) {
              expect(
                exercise.options.where(exercise.accepts),
                hasLength(1),
                reason: exercise.id,
              );
              expect(
                exercise.options.map(Exercise.normalize).toSet().length,
                exercise.options.length,
              );
            }
          }
        }
      }
    },
  );

  test('texto compartilhado acompanha cada exercício fora da lição', () {
    final lesson = Lesson.fromJson({
      'id': 'reading',
      'title': 'Leitura',
      'description': 'Inferência',
      'readingPassage': 'The shop closes at six.',
      'exercises': [
        {
          'id': 'reading-e1',
          'type': 'typed',
          'prompt': 'What time does the shop close?',
          'answer': 'six',
          'explanation': 'O texto indica six.',
        },
        {
          'id': 'reading-e2',
          'type': 'choice',
          'prompt': 'Is the shop open at seven?',
          'answer': 'No',
          'options': ['Yes', 'No'],
          'explanation': 'Seven é depois do fechamento.',
        },
      ],
    });
    expect(lesson.exercises.last.context, 'The shop closes at six.');
    expect(lesson.exercises.first.context, lesson.exercises.last.context);
  });

  test('campos novos são opcionais para cursos existentes', () {
    final json =
        jsonDecode(File('assets/courses/en_starter.json').readAsStringSync())
            as Map<String, dynamic>;
    final course = Course.fromJson(json);
    expect(course.contentVersion, 1);
    expect(course.coverage, isEmpty);
    expect(course.lessons.first.studyNotes, isEmpty);
    expect(course.lessons.first.sourceIds, isEmpty);
    for (final version in [0, -1, 1.5, '1']) {
      expect(
        () => Course.fromJson({...json, 'contentVersion': version}),
        throwsFormatException,
      );
    }
    final lesson = json['units'][0]['lessons'][0] as Map<String, dynamic>;
    expect(
      () => Lesson.fromJson({
        ...lesson,
        'sourceIds': [42],
      }),
      throwsFormatException,
    );
  });

  test('registro mantém autoria e links seguros das fontes', () async {
    final sources = await ContentSource.load(bundle: _ContentAssets());
    expect(sources, hasLength(6));
    final json =
        (jsonDecode(File('assets/content/sources.json').readAsStringSync())
                as Map<String, dynamic>)['sources'][0]
            as Map<String, dynamic>;
    for (final url in [
      'http://example.com',
      'javascript:alert(1)',
      'https:///path',
      'https://reader@example.com',
    ]) {
      expect(
        () => ContentSource.fromJson({...json, 'url': url}),
        throwsFormatException,
      );
    }
  });
}
