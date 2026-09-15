import 'package:fluent_app/data/content_sources.dart';
import 'package:fluent_app/models/course.dart';
import 'package:fluent_app/screens/lesson_screen.dart';
import 'package:fluent_app/screens/sources_screen.dart';
import 'package:fluent_app/services/progress_store.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:fluent_app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('material de estudo pode ser consultado sem responder', (tester) async {
    final lesson = Lesson(
      id: 'study-lesson',
      title: 'Estudo',
      description: 'Saudações',
      studyNotes: 'Use hello para cumprimentar.',
      sourceIds: ['communication-beginnings'],
      exercises: [
        Exercise(id: 'study-exercise', type: ExerciseType.choice,
          prompt: 'Cumprimente.', answer: 'Hello', options: ['Hello', 'Bye'],
          explanation: 'Hello é uma saudação.'),
      ],
    );
    final controller = LearningController(
      courses: [
        Course(id: 'study-course', title: 'Estudo', sourceLanguage: 'pt-BR',
          targetLanguage: 'en', level: 'Prática',
          units: [CourseUnit(id: 'study-unit', title: 'Estudo',
            description: 'Estudo', lessons: [lesson])]),
      ],
      store: ProgressStore(read: () async => null, write: (_) async => true),
    );
    await tester.pumpWidget(MaterialApp(
      theme: fluentTheme,
      home: LessonScreen(controller: controller, exercises: lesson.exercises, lesson: lesson),
    ));
    await tester.tap(find.byTooltip('Material de estudo'));
    await tester.pumpAndSettle();
    expect(find.text('Use hello para cumprimentar.'), findsOneWidget);
    expect(controller.progress.completedLessonIds, isEmpty);
    await tester.tap(find.text('Voltar à prática'));
    await tester.pumpAndSettle();
    expect(find.text('Cumprimente.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });

  testWidgets('referências filtradas ficam disponíveis offline', (tester) async {
    final sources = await ContentSource.load();
    await tester.pumpWidget(MaterialApp(
      theme: fluentTheme,
      home: const SourcesScreen(sourceIds: ['communication-beginnings']),
    ));
    await tester.pumpAndSettle();
    expect(find.text(sources.singleWhere((s) => s.id == 'communication-beginnings').title),
        findsOneWidget);
    expect(find.text(sources.singleWhere((s) => s.id == 'bc-reads').title), findsNothing);
    expect(find.textContaining('CC BY-NC 4.0'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
