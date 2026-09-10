import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../lib/models/course.dart';
import '../lib/services/progress_store.dart';
import '../lib/state/learning_controller.dart';

Course _course(String id) => Course(
      id: id,
      title: 'Curso $id',
      sourceLanguage: 'pt-BR',
      targetLanguage: id,
      level: 'A1',
      units: [
        CourseUnit(
          id: '$id-unit',
          title: 'Unidade',
          description: 'Uma unidade.',
          lessons: List.generate(
            3,
            (i) => Lesson(
              id: '$id-lesson-$i',
              title: 'Lição $i',
              description: 'Uma lição.',
              exercises: List.generate(
                2,
                (j) => Exercise(
                  id: '$id-exercise-$i-$j',
                  type: ExerciseType.typed,
                  prompt: 'Olá',
                  answer: 'Hello',
                  explanation: 'Hello significa olá.',
                ),
              ),
            ),
          ),
        ),
      ],
    );

Map<String, bool> _answers(Lesson lesson, {bool correct = true}) =>
    {for (final exercise in lesson.exercises) exercise.id: correct};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late DateTime now;
  late String? saved;
  late ProgressStore store;
  late LearningController controller;
  late List<Course> courses;

  setUp(() {
    now = DateTime(2026, 9, 10, 12);
    saved = null;
    store = ProgressStore(
      read: () async => saved,
      write: (value) async {
        saved = value;
        return true;
      },
    );
    courses = [_course('en'), _course('es')];
    controller = LearningController(
        courses: courses, store: store, now: () => now);
  });

  tearDown(() => controller.dispose());

  test('somente a primeira lição começa disponível', () async {
    await controller.load();
    final lessons = controller.course.lessons;
    expect(controller.nextLesson, lessons.first);
    expect(controller.isUnlocked(lessons.first), isTrue);
    expect(controller.isUnlocked(lessons[1]), isFalse);
    await expectLater(controller.completeLesson(lessons[1], _answers(lessons[1])),
        throwsArgumentError);
    await controller.completeLesson(lessons.first, _answers(lessons.first));
    expect(controller.isCompleted(lessons.first), isTrue);
    expect(controller.isUnlocked(lessons[1]), isTrue);
    expect(controller.nextLesson, lessons[1]);
    for (final lesson in lessons.skip(1)) {
      await controller.completeLesson(lesson, _answers(lesson));
    }
    expect(controller.nextLesson, isNull);
    expect(controller.progress.completedLessonIds, hasLength(3));
  });

  test('pontua acertos mais bônus apenas na primeira conclusão', () async {
    final lesson = controller.course.lessons.first;
    await controller.completeLesson(lesson, {
      lesson.exercises.first.id: true,
      lesson.exercises.last.id: false,
    });
    expect(controller.progress.totalXp, 30);
    expect(controller.progress.dailyXp, 30);
    expect(controller.goalReached, isTrue);
    await controller.completeLesson(lesson, _answers(lesson));
    expect(controller.progress.totalXp, 30);
    now = DateTime(2026, 9, 11);
    await controller.completeLesson(lesson, _answers(lesson));
    expect(controller.progress.totalXp, 30);
    expect(controller.progress.dailyXp, 0);
    expect(controller.progress.streak, 2);
  });

  test('rejeita resultados parciais e IDs estranhos sem mudar progresso',
      () async {
    final lesson = controller.course.lessons.first;
    await expectLater(controller.completeLesson(lesson, {}), throwsArgumentError);
    await expectLater(
      controller.completeLesson(lesson,
          {lesson.exercises.first.id: true, 'unknown': true}),
      throwsArgumentError,
    );
    await expectLater(
      controller.completeLesson(courses.last.lessons.first,
          _answers(courses.last.lessons.first)),
      throwsArgumentError,
    );
    expect(controller.progress.totalXp, 0);
    expect(saved, isNull);
  });

  test('erros entram na fila hoje e vocabulário aprendido amanhã', () async {
    final lesson = controller.course.lessons.first;
    await controller.completeLesson(lesson, {
      lesson.exercises.first.id: false,
      lesson.exercises.last.id: true,
    });
    expect(controller.dueExercises.map((e) => e.id),
        [lesson.exercises.first.id]);
    now = DateTime(2026, 9, 11);
    expect(controller.dueExercises, hasLength(2));
    await controller.completeReview(
        {for (final exercise in controller.dueExercises) exercise.id: true});
    expect(controller.progress.reviewedCount, 2);
    expect(controller.progress.totalXp, 30);
    expect(controller.dueExercises, isEmpty);
    expect(controller.progress.streak, 2);
    await expectLater(controller.completeReview({lesson.exercises.first.id: true}),
        throwsArgumentError);
  });

  test('repetição espaçada progride em 1, 3, 7, 14, 30 dias e reinicia no erro',
      () async {
    final lesson = controller.course.lessons.first;
    await controller.completeLesson(lesson, _answers(lesson, correct: false));
    final id = lesson.exercises.first.id;
    for (final interval in [1, 3, 7, 14, 30, 30]) {
      await controller.completeReview({id: true});
      final schedule = controller.progress.reviews[id]!;
      expect(schedule.intervalDays, interval);
      now = now.add(Duration(days: interval));
    }
    await controller.completeReview({id: false});
    expect(controller.progress.reviews[id]!.intervalDays, 1);
    expect(controller.progress.reviews[id]!.successCount, 0);
    now = now.add(const Duration(days: 1));
    await controller.completeReview({id: true});
    expect(controller.progress.reviews[id]!.intervalDays, 1);
    expect(controller.progress.totalXp, 20);
  });

  test('curso, meta, fila e pontuação ficam isolados e persistem', () async {
    final lesson = controller.course.lessons.first;
    await controller.setDailyGoal(50);
    await controller.completeLesson(lesson, _answers(lesson, correct: false));
    await controller.selectCourse('es');
    expect(controller.progress.totalXp, 0);
    expect(controller.progress.dailyGoal, 30);
    expect(controller.dueExercises, isEmpty);
    expect(controller.isCompleted(lesson), isFalse);
    await controller.setDailyGoal(20);
    final restored = LearningController(
        courses: courses, store: store, now: () => now);
    addTearDown(restored.dispose);
    await restored.load();
    expect(restored.course.id, 'es');
    expect(restored.progress.dailyGoal, 20);
    await restored.selectCourse('en');
    expect(restored.progress.dailyGoal, 50);
    expect(restored.progress.totalXp, 20);
    expect(restored.dueExercises, hasLength(2));
    expect(restored.isCompleted(lesson), isTrue);
    expect(restored.exportProgress(), jsonDecode(saved!));
  });

  test('implementação padrão usa shared_preferences', () async {
    SharedPreferences.setMockInitialValues({});
    final first = LearningController(courses: courses, store: ProgressStore());
    final second = LearningController(courses: courses, store: ProgressStore());
    addTearDown(first.dispose);
    addTearDown(second.dispose);
    await first.completeLesson(
        first.course.lessons.first, _answers(first.course.lessons.first));
    await second.load();
    expect(second.progress.totalXp, 40);
    expect(second.progress.completedLessonIds, hasLength(1));
  });

  test('meta inválida e curso desconhecido são rejeitados', () async {
    await expectLater(controller.setDailyGoal(0), throwsArgumentError);
    await expectLater(controller.setDailyGoal(1001), throwsArgumentError);
    await expectLater(controller.selectCourse('unknown'), throwsArgumentError);
    expect(controller.progress.dailyGoal, 30);
  });

  test('restauração explícita é idempotente e não soma XP duplicado', () async {
    final lesson = controller.course.lessons.first;
    await controller.completeLesson(lesson, _answers(lesson));
    final remote = controller.exportProgress();
    await controller.completeLesson(
        controller.course.lessons[1], _answers(controller.course.lessons[1]));
    await controller.mergeRemote(remote);
    await controller.mergeRemote(remote);
    expect(controller.progress.totalXp, 80);
    expect(controller.progress.completedLessonIds, hasLength(2));
    expect(controller.course.id, 'en');
    expect(controller.progress.dailyXp, 80);
  });

  test('importação inválida é atômica e preserva dados locais', () async {
    final lesson = controller.course.lessons.first;
    await controller.completeLesson(lesson, _answers(lesson));
    final before = controller.exportProgress();
    final remote =
        jsonDecode(jsonEncode(before)) as Map<String, dynamic>;
    remote['courses']['es']['totalXp'] = -1;
    await expectLater(controller.mergeRemote(remote), throwsFormatException);
    expect(controller.exportProgress(), before);
    remote['schemaVersion'] = 99;
    await expectLater(controller.mergeRemote(remote), throwsFormatException);
  });

  test('dados corrompidos não derrubam o app nem são sobrescritos ao carregar',
      () async {
    for (final raw in [
      '{broken',
      '[]',
      '{"schemaVersion":99,"courses":{},"selectedCourseId":"en"}',
      '{"schemaVersion":1,"courses":{"en":42},"selectedCourseId":"en"}',
    ]) {
      saved = raw;
      await controller.load();
      expect(controller.storageError, isNotNull);
      expect(controller.progress.totalXp, 0);
      expect(saved, raw);
    }
  });

  test('IDs desconhecidos no progresso salvo são rejeitados', () async {
    final remote = controller.exportProgress();
    remote['courses']['en']['completedLessonIds'] = ['unknown'];
    await expectLater(controller.mergeRemote(remote), throwsFormatException);
    expect(controller.progress.completedLessonIds, isEmpty);
  });

  test('falha de persistência mantém a sessão e recuperação limpa aviso',
      () async {
    var succeeds = false;
    final unreliable = LearningController(
      courses: courses,
      store: ProgressStore(
          read: () async => null, write: (_) async => succeeds),
      now: () => now,
    );
    addTearDown(unreliable.dispose);
    final lesson = unreliable.course.lessons.first;
    await unreliable.completeLesson(lesson, _answers(lesson));
    expect(unreliable.storageError, isNotNull);
    expect(unreliable.progress.totalXp, 40);
    succeeds = true;
    await unreliable.setDailyGoal(50);
    expect(unreliable.storageError, isNull);
  });
}
