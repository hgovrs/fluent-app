import 'dart:convert';

import 'package:fluent_app/data/course_catalog.dart';
import 'package:fluent_app/models/course.dart';
import 'package:fluent_app/screens/home_screen.dart';
import 'package:fluent_app/services/cloud_service.dart';
import 'package:fluent_app/services/progress_store.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:fluent_app/theme.dart';
import 'package:fluent_app/widgets/course_picker_button.dart';
import 'package:fluent_app/widgets/selection_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/load_brand_fonts.dart';

// These home interactions must not call any cloud operation.
class _LocalCloud extends Fake implements CloudService {}

Future<LearningController> _pumpHome(
  WidgetTester tester, {
  List<Course>? courses,
  ProgressStore? store,
  double textScale = 1,
}) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(320, 740);
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  final controller = LearningController(
    courses: courses ?? (await tester.runAsync(CourseCatalog.load))!,
    store:
        store ??
        ProgressStore(read: () async => null, write: (_) async => true),
  );
  await controller.load();
  addTearDown(controller.dispose);
  await tester.pumpWidget(
    MaterialApp(
      theme: fluentTheme,
      home: HomeScreen(controller: controller, cloud: _LocalCloud()),
    ),
  );
  await tester.pumpAndSettle();
  return controller;
}

Future<void> _openPicker(WidgetTester tester) async {
  final picker = find.byKey(const ValueKey('course-picker'));
  await tester.ensureVisible(picker);
  await tester.pumpAndSettle();
  await tester.tap(picker);
  await tester.pumpAndSettle();
}

Future<void> _pickCourse(WidgetTester tester, String id) async {
  await _openPicker(tester);
  final option = find.byKey(ValueKey('course-option-$id'));
  await tester.scrollUntilVisible(
    option,
    160,
    scrollable: find.descendant(
      of: find.byType(BottomSheet),
      matching: find.byType(Scrollable),
    ),
  );
  await tester.pumpAndSettle();
  expect(tester.getSize(option).height, greaterThanOrEqualTo(48));
  expect(option.hitTestable(), findsOneWidget);
  await tester.tap(option);
  await tester.pumpAndSettle();
}

Future<void> _focusWithTab(
  WidgetTester tester,
  bool Function(BuildContext context) matches,
) async {
  for (var attempt = 0; attempt < 20; attempt++) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pumpAndSettle();
    final context = FocusManager.instance.primaryFocus?.context;
    if (context != null && matches(context)) return;
  }
  fail('The requested control was not reachable with the keyboard.');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(loadBrandFonts);

  testWidgets('every track keeps the next action visible on a compact phone', (
    tester,
  ) async {
    final controller = await _pumpHome(tester);
    for (final course in controller.courses) {
      await _pickCourse(tester, course.id);
      expect(controller.course.id, course.id);
      expect(find.byType(BottomSheet), findsNothing);
      expect(find.byType(DropdownButtonFormField<String>), findsNothing);
      expect(find.text(course.title), findsOneWidget);
      if (course.coverage.isNotEmpty) {
        expect(find.text(course.coverage), findsNothing);
        expect(find.text('Prática parcial, sem certificação.'), findsOneWidget);
      }
      final button = find.widgetWithText(PrimaryButton, 'Começar lição');
      final navigationTop = tester.getTopLeft(find.byType(NavigationBar)).dy;
      expect(
        tester.getBottomLeft(button).dy,
        lessThan(navigationTop),
        reason: '${course.id}: the primary action must not require scrolling',
      );
      expect(tester.getTopLeft(button).dy, greaterThan(0));
      final welcome = tester.widget<Text>(
        find.text('Um pouco hoje.\nUm mundo amanhã.'),
      );
      expect(welcome.style!.fontFamily, kFontBody);
      expect(welcome.textAlign, TextAlign.center);
      expect(
        tester.getCenter(find.text('Um pouco hoje.\nUm mundo amanhã.')).dx,
        closeTo(160, 0.5),
      );
      expect(
        tester.getSize(find.byKey(const ValueKey('course-picker'))).height,
        greaterThanOrEqualTo(48),
      );
      expect(tester.takeException(), isNull);
    }
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('long descriptions remain available on demand with large text', (
    tester,
  ) async {
    final controller = await _pumpHome(tester, textScale: 2);
    final course = controller.courses.last;
    await _pickCourse(tester, course.id);
    expect(find.text(course.coverage), findsNothing);
    await _openPicker(tester);
    final details = find.text('Sobre a trilha atual');
    await tester.tap(details);
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text(course.coverage), findsOneWidget);
    expect(find.text(course.level), findsOneWidget);
    await tester.tap(find.widgetWithText(TextButton, 'Fechar'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Fechar seleção de trilha'));
    await tester.pumpAndSettle();

    final lesson = controller.nextLesson!;
    final info = find.byTooltip('Detalhes da próxima lição');
    await tester.ensureVisible(info);
    await tester.pumpAndSettle();
    expect(info.hitTestable(), findsOneWidget);
    await tester.tap(info);
    await tester.pumpAndSettle();
    expect(find.text(lesson.description), findsOneWidget);
    expect(controller.progress.completedLessonIds, isEmpty);
    expect(tester.takeException(), isNull);
    await tester.tap(find.widgetWithText(TextButton, 'Fechar'));
    await tester.pumpAndSettle();
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'switching tracks preserves local progress and cancelling is inert',
    (tester) async {
      String? saved;
      final controller = await _pumpHome(
        tester,
        store: ProgressStore(
          read: () async => saved,
          write: (value) async {
            saved = value;
            return true;
          },
        ),
      );
      final original = controller.course;
      final lesson = original.lessons.first;
      await controller.completeLesson(lesson, {
        for (final exercise in lesson.exercises) exercise.id: true,
      });
      await controller.setDailyGoal(40);
      await tester.pumpAndSettle();
      final progress = controller.exportProgress();
      await _openPicker(tester);
      final selected = tester.widget<SelectionTile>(
        find.byKey(ValueKey('course-option-${original.id}')),
      );
      expect(selected.selected, isTrue);
      await tester.tap(find.byTooltip('Fechar seleção de trilha'));
      await tester.pumpAndSettle();
      expect(controller.exportProgress(), progress);

      await _pickCourse(tester, controller.courses.last.id);
      expect(controller.progress.completedLessonIds, isEmpty);
      await _pickCourse(tester, original.id);
      expect(controller.isCompleted(lesson), isTrue);
      expect(controller.progress.dailyGoal, 40);
      expect(controller.nextLesson!.id, original.lessons[1].id);
      expect(
        (jsonDecode(saved!) as Map<String, dynamic>)['selectedCourseId'],
        original.id,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets('track selection works with keyboard and touch-sized targets', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      final controller = await _pumpHome(tester);
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await _focusWithTab(
        tester,
        (context) =>
            context.findAncestorWidgetOfExactType<CoursePickerButton>() != null,
      );
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(find.byType(BottomSheet), findsOneWidget);
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      final nextCourse = controller.courses[1];
      await _focusWithTab(
        tester,
        (context) =>
            context.findAncestorWidgetOfExactType<SelectionTile>()?.key ==
            ValueKey('course-option-${nextCourse.id}'),
      );
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(controller.course.id, nextCourse.id);
      expect(find.byType(BottomSheet), findsNothing);
      expect(tester.takeException(), isNull);
    } finally {
      semantics.dispose();
      await tester.pumpWidget(const SizedBox());
    }
  });

  testWidgets('a single track exposes its details without a redundant picker', (
    tester,
  ) async {
    final courses = (await tester.runAsync(CourseCatalog.load))!;
    final controller = await _pumpHome(tester, courses: [courses[1]]);
    expect(find.text('Trocar trilha'), findsNothing);
    expect(find.text('Sobre esta trilha'), findsOneWidget);
    await _openPicker(tester);
    expect(find.byType(BottomSheet), findsNothing);
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text(controller.course.coverage), findsOneWidget);
    await tester.tap(find.widgetWithText(TextButton, 'Fechar'));
    await tester.pumpAndSettle();
    expect(find.text('Começar lição'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
