import 'package:fluent_app/models/course.dart';
import 'package:fluent_app/screens/lesson_screen.dart';
import 'package:fluent_app/services/progress_store.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:fluent_app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/pump_fluent_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('opens the real course offline and navigates the main tabs', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await pumpFluentApp(tester);
    expect(find.text('Um pouco hoje.\nUm mundo amanhã.'), findsOneWidget);
    expect(find.text('Começar lição'), findsOneWidget);
    await tester.tap(find.text('Revisar'));
    await tester.pumpAndSettle();
    expect(find.text('Tudo em dia por aqui!'), findsOneWidget);
    await tester.tap(find.text('Meu espaço'));
    await tester.pumpAndSettle();
    expect(find.text('Seu espaço.'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('checks all exercise types and saves only at session end', (tester) async {
    final exercises = [
      Exercise(
        id: 'choice', type: ExerciseType.choice, prompt: 'Como se diz olá?',
        answer: 'Hello', options: ['Hello', 'Goodbye'], explanation: 'Hello é uma saudação.',
      ),
      Exercise(
        id: 'typed', type: ExerciseType.typed, prompt: 'Escreva obrigado.',
        answer: 'Thank you', explanation: 'Thank you expressa gratidão.',
      ),
      Exercise(
        id: 'order', type: ExerciseType.wordOrder, prompt: 'Organize: eu estou bem.',
        answer: 'I am fine', options: ['fine', 'I', 'am'], explanation: 'I am fine significa estou bem.',
      ),
    ];
    final lesson = Lesson(id: 'lesson', title: 'Primeiros passos', description: 'Saudações', exercises: exercises);
    final controller = LearningController(
      courses: [
        Course(
          id: 'en', title: 'Inglês', sourceLanguage: 'pt-BR', targetLanguage: 'en', level: 'A1',
          units: [CourseUnit(id: 'unit', title: 'Começo', description: 'Começo', lessons: [lesson])],
        ),
      ],
      store: ProgressStore(read: () async => null, write: (_) async => true),
    );
    await controller.load();
    await tester.pumpWidget(MaterialApp(
      theme: fluentTheme,
      home: LessonScreen(controller: controller, exercises: exercises, lesson: lesson),
    ));
    await tester.tap(find.text('Goodbye'));
    await tester.pump();
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(find.text('Vamos aprender com essa!'), findsOneWidget);
    expect(controller.progress.completedLessonIds, isEmpty);
    await tester.scrollUntilVisible(find.text('Continuar'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '  THANK YOU!  ');
    await tester.pump();
    await tester.ensureVisible(find.text('Verificar'));
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(find.text('Muito bem!'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Continuar'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    for (final word in ['I', 'am', 'fine']) {
      await tester.tap(find.widgetWithText(ActionChip, word));
      await tester.pump();
    }
    await tester.ensureVisible(find.text('Verificar'));
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Continuar'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    expect(find.text('Mais um passo dado!'), findsOneWidget);
    expect(find.text('2/3'), findsOneWidget);
    expect(controller.isCompleted(lesson), isTrue);
    expect(controller.dueExercises.map((e) => e.id), contains('choice'));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
}
