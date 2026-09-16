import 'package:fluent_app/data/content_sources.dart';
import 'package:fluent_app/data/course_catalog.dart';
import 'package:fluent_app/screens/home_screen.dart';
import 'package:fluent_app/screens/lesson_screen.dart';
import 'package:fluent_app/screens/profile_screen.dart';
import 'package:fluent_app/services/cloud_service.dart';
import 'package:fluent_app/services/progress_store.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:fluent_app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/load_brand_fonts.dart';
import 'support/pump_fluent_app.dart';

void _viewport(WidgetTester tester, Size size, {double textScale = 1}) {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = size;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  tester.platformDispatcher.platformBrightnessTestValue = Brightness.light;
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
}

Future<void> _tapText(WidgetTester tester, String text) async {
  final target = find.text(text);
  if (target.evaluate().isEmpty) {
    final scrollable = find.byType(Scrollable).first;
    tester.state<ScrollableState>(scrollable).position.jumpTo(0);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(target, 200, scrollable: scrollable);
  }
  await tester.ensureVisible(target);
  await tester.pumpAndSettle();
  await tester.tap(target);
  await tester.pumpAndSettle();
  expect(tester.takeException(), isNull);
}

Future<LearningController> _controller(WidgetTester tester) async {
  final courses = await tester.runAsync(CourseCatalog.load);
  final controller = LearningController(
    courses: courses!,
    store: ProgressStore(read: () async => null, write: (_) async => true),
  );
  await controller.load();
  addTearDown(controller.dispose);
  return controller;
}

class _CloudPreview extends Fake implements CloudService {
  _CloudPreview({this.signedIn = false})
    : email = signedIn ? 'learner@example.test' : null;

  final _changes = ChangeNotifier();
  int signIns = 0;
  int backups = 0;
  Map<String, dynamic>? savedProgress;

  @override
  bool get available => true;
  @override
  bool busy = false;
  @override
  bool signedIn;
  @override
  String? email;
  @override
  String? error;

  @override
  void addListener(VoidCallback listener) => _changes.addListener(listener);
  @override
  void removeListener(VoidCallback listener) =>
      _changes.removeListener(listener);
  @override
  void dispose() => _changes.dispose();

  void showBusy(bool value) {
    busy = value;
    _changes.notifyListeners();
  }

  @override
  Future<bool> signIn(String email, String password) async {
    signIns++;
    this.email = email;
    signedIn = true;
    _changes.notifyListeners();
    return true;
  }

  @override
  Future<bool> backup(Map<String, dynamic> progress) async {
    backups++;
    savedProgress = progress;
    return true;
  }
}

Widget _profile(LearningController controller, CloudService cloud) =>
    MaterialApp(
      theme: fluentTheme,
      home: Scaffold(
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [ProfileScreen(controller: controller, cloud: cloud)],
        ),
      ),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(loadBrandFonts);

  for (final (name, size, scale) in [
    ('compact phone', const Size(320, 740), 1.0),
    ('phone', const Size(390, 844), 1.0),
    ('desktop', const Size(1100, 800), 1.0),
    ('large text', const Size(390, 844), 2.0),
  ]) {
    testWidgets('all screens stay dark and usable on $name', (tester) async {
      _viewport(tester, size, textScale: scale);
      SharedPreferences.setMockInitialValues({});
      await pumpFluentApp(tester);
      expect(tester.takeException(), isNull);
      final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
      expect(app.themeMode, ThemeMode.dark);
      expect(app.theme, same(app.darkTheme));
      final home = tester.widget<HomeScreen>(find.byType(HomeScreen));
      expect(
        Theme.of(tester.element(find.byType(HomeScreen))).brightness,
        Brightness.dark,
      );
      expect(
        tester.widget<Text>(find.text('fluent')).style!.fontFamily,
        kFontBrand,
      );
      final welcome = tester.widget<Text>(
        find.text('Um pouco hoje.\nUm mundo amanhã.'),
      );
      expect(welcome.style!.fontFamily, kFontBody);
      expect(welcome.textAlign, TextAlign.center);
      final lastLesson = home.controller.course.lessons.last;
      await tester.scrollUntilVisible(find.text(lastLesson.title), 400);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      final scroller = tester.state<ScrollableState>(
        find.byType(Scrollable).first,
      );
      scroller.position.jumpTo(0);
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('Fontes e licenças'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await pumpAssetRoute<List<ContentSource>>(
        tester,
        () => tester.tap(find.text('Fontes e licenças')),
      );
      expect(find.byType(SelectableText), findsWidgets);
      for (final text in tester.widgetList<SelectableText>(
        find.byType(SelectableText),
      )) {
        expect(text.style!.color, kBrandPurpleLight);
      }
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();

      await tester.tap(
        find.byTooltip(
          'Voz do feedback: ${home.controller.feedbackVoice?.name ?? 'Sem áudio'}',
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Voz do feedback'), findsOneWidget);
      final sheet = tester.widget<Material>(
        find
            .descendant(
              of: find.byType(BottomSheet),
              matching: find.byType(Material),
            )
            .first,
      );
      expect(sheet.color, kOverlaySurface);
      expect(tester.takeException(), isNull);
      await _tapText(tester, 'Sem áudio');

      await _tapText(tester, 'Começar lição');
      final lesson = tester.widget<LessonScreen>(find.byType(LessonScreen));
      final exercise = lesson.exercises.first;
      final answer = exercise.options.firstWhere(exercise.accepts);
      await _tapText(tester, answer);
      final selected = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, answer),
      );
      expect(
        selected.style!.backgroundColor!.resolve({}),
        kSurfacePurpleRaised,
      );
      expect(selected.style!.foregroundColor!.resolve({}), kBrandPurpleLight);
      await _tapText(tester, 'Verificar');
      expect(find.text('Muito bem!'), findsOneWidget);
      expect(
        tester.widget<Text>(find.text('Muito bem!')).style!.color,
        kBrandPurpleLight,
      );
      expect(home.controller.progress.completedLessonIds, isEmpty);
      await tester.tap(find.byTooltip('Sair da prática'));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(tester.takeException(), isNull);
      await _tapText(tester, 'Sair');
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(home.controller.progress.completedLessonIds, isEmpty);

      await _tapText(tester, 'Revisar');
      expect(find.text('Tudo em dia por aqui!'), findsOneWidget);
      expect(
        tester
            .widget<ElevatedButton>(
              find.ancestor(
                of: find.text('Revisar agora'),
                matching: find.byWidgetPredicate(
                  (widget) => widget is ElevatedButton,
                ),
              ),
            )
            .onPressed,
        isNull,
      );
      await _tapText(tester, 'Meu espaço');
      expect(find.text('Seu espaço.'), findsOneWidget);
      await _tapText(tester, '10 XP');
      expect(home.controller.progress.dailyGoal, 10);
      final goal = tester.widget<ChoiceChip>(
        find.widgetWithText(ChoiceChip, '10 XP'),
      );
      expect(goal.selected, isTrue);
      expect(goal.labelStyle!.color, kBrandPurpleLight);
      final dropdown = find.byType(DropdownButtonFormField<String>);
      await tester.ensureVisible(dropdown);
      await tester.tap(dropdown);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }

  testWidgets('auth validation and busy state keep their behavior and colors', (
    tester,
  ) async {
    _viewport(tester, const Size(390, 844));
    final controller = await _controller(tester);
    final cloud = _CloudPreview();
    addTearDown(cloud.dispose);
    await tester.pumpWidget(_profile(controller, cloud));
    await _tapText(tester, 'Entrar');
    expect(cloud.signIns, 0);
    expect(find.text('Digite um e-mail válido.'), findsOneWidget);
    expect(find.text('Digite sua senha.'), findsOneWidget);
    expect(
      tester.widget<Text>(find.text('Digite um e-mail válido.')).style!.color,
      kError,
    );
    cloud.showBusy(true);
    await tester.pump();
    expect(
      tester
          .widget<CircularProgressIndicator>(
            find.byType(CircularProgressIndicator),
          )
          .color,
      kBrandPurple,
    );
    for (final field in tester.widgetList<TextFormField>(
      find.byType(TextFormField),
    )) {
      expect(field.enabled, isFalse);
    }
    cloud.showBusy(false);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byType(TextFormField).at(0));
    await tester.enterText(
      find.byType(TextFormField).at(0),
      'learner@example.test',
    );
    await tester.ensureVisible(find.byType(TextFormField).at(1));
    await tester.enterText(find.byType(TextFormField).at(1), 'test-only-input');
    await _tapText(tester, 'Entrar');
    expect(cloud.signIns, 1);
    expect(cloud.email, 'learner@example.test');
    expect(find.text('Salvar backup'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('restyled backup dialog still requires explicit confirmation', (
    tester,
  ) async {
    _viewport(tester, const Size(390, 844));
    final controller = await _controller(tester);
    final cloud = _CloudPreview(signedIn: true);
    addTearDown(cloud.dispose);
    await tester.pumpWidget(_profile(controller, cloud));
    await _tapText(tester, 'Salvar backup');
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(cloud.backups, 0);
    await _tapText(tester, 'Cancelar');
    expect(cloud.backups, 0);
    await _tapText(tester, 'Salvar backup');
    await _tapText(tester, 'Confirmar');
    expect(cloud.backups, 1);
    expect(cloud.savedProgress, controller.exportProgress());
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
