import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:fluent_app/models/course.dart';
import 'package:fluent_app/models/feedback_catalog.dart';
import 'package:fluent_app/models/learning_progress.dart';
import 'package:fluent_app/screens/lesson_screen.dart';
import 'package:fluent_app/services/feedback_audio_player.dart';
import 'package:fluent_app/services/progress_store.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:fluent_app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/pump_fluent_app.dart';

Map<String, dynamic> _catalogJson() =>
    jsonDecode(File('assets/audio_feedback/catalog.json').readAsStringSync())
        as Map<String, dynamic>;

FeedbackCatalog _catalog() => FeedbackCatalog.fromJson(_catalogJson());

Course _course(String id) => Course(
  id: id,
  title: id,
  sourceLanguage: 'pt-BR',
  targetLanguage: id,
  level: 'A1',
  units: [
    CourseUnit(
      id: 'unit',
      title: 'Unidade',
      description: 'Prática',
      lessons: [
        Lesson(
          id: 'lesson',
          title: 'Lição',
          description: 'Prática',
          exercises: [
            Exercise(
              id: 'one',
              type: ExerciseType.choice,
              prompt: 'Olá',
              answer: 'Hello',
              options: ['Hello', 'Goodbye'],
              explanation: 'Hello é uma saudação.',
            ),
            Exercise(
              id: 'two',
              type: ExerciseType.typed,
              prompt: 'Obrigado',
              answer: 'Thank you',
              explanation: 'Thank you expressa gratidão.',
            ),
          ],
        ),
      ],
    ),
  ],
);

class _Output implements FeedbackAudioOutput {
  final loaded = <String>[];
  final finished = Completer<void>();
  Completer<void>? loading;
  bool fail = false;
  bool disposed = false;
  int plays = 0;

  @override
  Future<void> load(String assetPath) async {
    loaded.add(assetPath);
    if (fail) throw StateError('Missing audio');
    if (loading != null) await loading!.future;
  }

  @override
  Future<void> play() async {
    plays++;
    await finished.future;
  }

  @override
  Future<void> dispose() async {
    disposed = true;
    if (!finished.isCompleted) finished.complete();
  }
}

Future<void> _flush() => Future<void>.delayed(Duration.zero);

Future<LearningController> _pumpFeedbackLesson(
  WidgetTester tester,
  List<_Output> outputs, {
  bool review = false,
  String? savedThemeId,
  bool failAudio = false,
}) async {
  final saved = savedThemeId == null
      ? null
      : jsonEncode({
          'schemaVersion': 1,
          'selectedCourseId': 'en',
          'courses': {
            'en': LearningProgress(feedbackThemeId: savedThemeId).toJson(),
          },
        });
  final controller = LearningController(
    courses: [_course('en')],
    feedbackCatalog: _catalog(),
    store: ProgressStore(read: () async => saved, write: (_) async => true),
  );
  addTearDown(controller.dispose);
  await controller.load();
  final lesson = controller.course.lessons.first;
  await tester.pumpWidget(
    MaterialApp(
      theme: fluentTheme,
      home: LessonScreen(
        controller: controller,
        lesson: review ? null : lesson,
        exercises: lesson.exercises,
        createFeedbackPlayer: () => FeedbackAudioPlayer(
          createOutput: () {
            final output = _Output()..fail = failAudio;
            outputs.add(output);
            return output;
          },
        ),
      ),
    ),
  );
  return controller;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('catálogo de feedback', () {
    test('todos os temas têm acertos, erros e caminhos locais únicos', () {
      final catalog = _catalog();
      expect(
        catalog.themes.map((theme) => theme.id),
        containsAll(['zoacao', 'torcida', 'tranquilo']),
      );
      expect(
        catalog.theme(LearningProgress.defaultFeedbackThemeId)?.name,
        'Zoação leve',
      );
      final paths = <String>{};
      for (final theme in catalog.themes) {
        for (final category in FeedbackCategory.values) {
          expect(
            theme.clips.where((clip) => clip.category == category),
            isNotEmpty,
          );
        }
        for (final clip in theme.clips) {
          expect(paths.add(clip.assetPath), isTrue);
          expect(clip.assetPath, startsWith('assets/audio_feedback/'));
          expect(clip.assetPath, endsWith('.mp3'));
        }
      }
    });

    test('rejeita caminhos, IDs duplicados e categorias incompletas', () {
      for (final id in ['../escape', 'off', 'bad/id', '']) {
        final json = _catalogJson();
        json['themes'][0]['id'] = id;
        expect(() => FeedbackCatalog.fromJson(json), throwsFormatException);
      }
      final duplicate = _catalogJson();
      duplicate['themes'][1]['id'] = duplicate['themes'][0]['id'];
      expect(() => FeedbackCatalog.fromJson(duplicate), throwsFormatException);
      final noErrors = _catalogJson();
      (noErrors['themes'][0]['clips'] as List).removeWhere(
        (dynamic clip) => clip['category'] == 'incorrect',
      );
      expect(() => FeedbackCatalog.fromJson(noErrors), throwsFormatException);
      final badCategory = _catalogJson();
      badCategory['themes'][0]['clips'][0]['category'] = 'unknown';
      expect(
        () => FeedbackCatalog.fromJson(badCategory),
        throwsFormatException,
      );
    });

    test(
      'novos temas entram pelo catálogo, sem enum de temas na interface',
      () {
        final json = _catalogJson();
        final extra = jsonDecode(jsonEncode(json['themes'][0]));
        extra['id'] = 'novo_tema';
        extra['name'] = 'Novo tema';
        (json['themes'] as List).add(extra);
        expect(
          FeedbackCatalog.fromJson(json).theme('novo_tema')!.name,
          'Novo tema',
        );
      },
    );

    test('sorteia somente a categoria pedida, sem repetição imediata', () {
      final picker = FeedbackPicker(random: Random(12));
      for (final theme in _catalog().themes) {
        for (final category in FeedbackCategory.values) {
          String? previous;
          for (var i = 0; i < 20; i++) {
            final clip = picker.pick(theme, category);
            expect(clip.category, category);
            expect(clip.id, isNot(previous));
            previous = clip.id;
          }
        }
      }
    });
  });

  group('preferência por curso', () {
    test('progresso novo ou sem preferência inicia com Zoação leve', () {
      expect(LearningProgress().feedbackThemeId, 'zoacao');
      final json = LearningProgress().toJson()..remove('feedbackThemeId');
      final progress = LearningProgress.fromJson(json);
      expect(progress.feedbackThemeId, 'zoacao');
    });

    test('mantém temas e silêncio salvos e rejeita preferência inválida', () {
      for (final themeId in ['off', 'zoacao', 'torcida', 'tranquilo']) {
        final progress = LearningProgress(feedbackThemeId: themeId);
        expect(
          LearningProgress.fromJson(progress.toJson()).feedbackThemeId,
          themeId,
        );
      }
      final json = LearningProgress().toJson();
      json['feedbackThemeId'] = 42;
      expect(() => LearningProgress.fromJson(json), throwsFormatException);
    });

    test('persiste, isola cursos e não ativa tema via backup remoto', () async {
      String? saved;
      final store = ProgressStore(
        read: () async => saved,
        write: (value) async {
          saved = value;
          return true;
        },
      );
      LearningController create() => LearningController(
        courses: [_course('en'), _course('es')],
        store: store,
        feedbackCatalog: _catalog(),
      );
      final controller = create();
      addTearDown(controller.dispose);
      await controller.load();
      expect(controller.feedbackThemeId, 'zoacao');
      await controller.setFeedbackTheme('torcida');
      await controller.selectCourse('es');
      expect(controller.feedbackThemeId, 'zoacao');
      await controller.selectCourse('en');
      expect(controller.feedbackThemeId, 'torcida');
      final restored = create();
      addTearDown(restored.dispose);
      await restored.load();
      expect(restored.feedbackThemeId, 'torcida');
      await restored.setFeedbackTheme('off');
      await restored.mergeRemote(controller.exportProgress());
      expect(restored.feedbackThemeId, 'off');
      await expectLater(
        controller.setFeedbackTheme('unknown'),
        throwsArgumentError,
      );
    });

    test('tema removido não bloqueia curso nem ativa outro áudio', () async {
      final progress = LearningProgress(feedbackThemeId: 'tema_removido');
      final controller = LearningController(
        courses: [_course('en')],
        feedbackCatalog: _catalog(),
        store: ProgressStore(
          read: () async => jsonEncode({
            'schemaVersion': 1,
            'selectedCourseId': 'en',
            'courses': {'en': progress.toJson()},
          }),
          write: (_) async => true,
        ),
      );
      addTearDown(controller.dispose);
      await controller.load();
      expect(controller.storageError, isNull);
      expect(controller.feedbackThemeId, 'off');
      expect(controller.nextLesson, isNotNull);
    });
  });

  group('reprodução opcional', () {
    final clip = _catalog().themes.first.clips.first;

    test('falha de áudio não lança erro para a aula', () async {
      final output = _Output()..fail = true;
      final player = FeedbackAudioPlayer(createOutput: () => output);
      addTearDown(player.dispose);
      await player.play(clip);
      expect(player.status, FeedbackAudioStatus.unavailable);
      expect(output.disposed, isTrue);
    });

    test('parar durante carregamento impede reprodução atrasada', () async {
      final output = _Output()..loading = Completer<void>();
      final player = FeedbackAudioPlayer(createOutput: () => output);
      addTearDown(player.dispose);
      final playing = player.play(clip);
      await _flush();
      await player.stop();
      output.loading!.complete();
      await playing;
      expect(output.plays, 0);
      expect(output.disposed, isTrue);
      expect(player.status, FeedbackAudioStatus.idle);
    });

    test(
      'nova reação substitui áudio anterior e dispose encerra reprodução',
      () async {
        final outputs = <_Output>[];
        final player = FeedbackAudioPlayer(
          createOutput: () {
            final output = _Output();
            outputs.add(output);
            return output;
          },
        );
        final first = player.play(clip);
        await _flush();
        expect(player.status, FeedbackAudioStatus.playing);
        final second = player.play(clip);
        await _flush();
        expect(outputs.first.disposed, isTrue);
        expect(outputs.last.plays, 1);
        player.dispose();
        await Future.wait([first, second]);
        expect(outputs.last.disposed, isTrue);
      },
    );
  });

  testWidgets('escolhe tema antes da lição pela tela inicial', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await pumpFluentApp(tester);
    await tester.tap(find.byTooltip('Feedback de áudio: Zoação leve'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Tranquilo'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.text('Tranquilo'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Feedback de áudio: Tranquilo'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  for (final review in [false, true]) {
    for (final correct in [false, true]) {
      testWidgets(
        '${review ? 'revisão' : 'lição'} toca ${correct ? 'acerto' : 'erro'} automaticamente sem replay',
        (tester) async {
          final outputs = <_Output>[];
          final controller = await _pumpFeedbackLesson(
            tester,
            outputs,
            review: review,
          );
          expect(controller.feedbackThemeId, 'zoacao');
          await tester.tap(find.text(correct ? 'Hello' : 'Goodbye'));
          await tester.pump();
          expect(outputs, isEmpty);
          await tester.tap(find.text('Verificar'));
          await tester.pump();
          expect(outputs.single.plays, 1);
          expect(
            outputs.single.loaded.single,
            contains(correct ? 'zoacao_acerto_' : 'zoacao_erro_'),
          );
          await tester.pumpAndSettle();
          await tester.scrollUntilVisible(
            find.text('Parar áudio'),
            200,
            scrollable: find.byType(Scrollable).first,
          );
          expect(find.text('Ouvir reação'), findsNothing);
          outputs.single.finished.complete();
          await tester.pumpAndSettle();
          expect(outputs.single.disposed, isTrue);
          expect(find.text('Parar áudio'), findsNothing);
          expect(find.text('Ouvir reação'), findsNothing);
          await tester.pump();
          expect(outputs, hasLength(1));
          await tester.pumpWidget(const SizedBox());
        },
      );
    }
  }

  testWidgets('parar a reação não oferece reprodução manual', (tester) async {
    final outputs = <_Output>[];
    await _pumpFeedbackLesson(tester, outputs);
    await tester.tap(find.text('Hello'));
    await tester.pump();
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(outputs.single.plays, 1);
    await tester.scrollUntilVisible(
      find.text('Parar áudio'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Parar áudio'));
    await tester.pumpAndSettle();
    expect(outputs.single.disposed, isTrue);
    expect(find.text('Parar áudio'), findsNothing);
    expect(find.text('Ouvir reação'), findsNothing);
    expect(outputs, hasLength(1));
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'falha do áudio não exige reprodução manual nem bloqueia correção',
    (tester) async {
      final outputs = <_Output>[];
      await _pumpFeedbackLesson(tester, outputs, failAudio: true);
      await tester.tap(find.text('Hello'));
      await tester.pump();
      await tester.tap(find.text('Verificar'));
      await tester.pumpAndSettle();
      expect(outputs.single.plays, 0);
      expect(outputs.single.disposed, isTrue);
      expect(find.text('Muito bem!'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text(
          'Áudio indisponível. Você pode continuar pela correção escrita.',
        ),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Parar áudio'), findsNothing);
      expect(find.text('Ouvir reação'), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets('respeita Sem áudio salvo sem ativar a reação padrão', (
    tester,
  ) async {
    final outputs = <_Output>[];
    final controller = await _pumpFeedbackLesson(
      tester,
      outputs,
      savedThemeId: 'off',
    );
    expect(controller.feedbackThemeId, 'off');
    await tester.tap(find.text('Hello'));
    await tester.pump();
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(find.text('Muito bem!'), findsOneWidget);
    expect(outputs, isEmpty);
    expect(find.text('Parar áudio'), findsNothing);
    expect(find.text('Ouvir reação'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('reage à correção, para ao avançar e silencia durante a lição', (
    tester,
  ) async {
    final outputs = <_Output>[];
    final controller = LearningController(
      courses: [_course('en')],
      feedbackCatalog: _catalog(),
      store: ProgressStore(read: () async => null, write: (_) async => true),
    );
    addTearDown(controller.dispose);
    await controller.setFeedbackTheme('zoacao');
    final lesson = controller.course.lessons.first;
    await tester.pumpWidget(
      MaterialApp(
        theme: fluentTheme,
        home: LessonScreen(
          controller: controller,
          lesson: lesson,
          exercises: lesson.exercises,
          createFeedbackPlayer: () => FeedbackAudioPlayer(
            createOutput: () {
              final output = _Output();
              outputs.add(output);
              return output;
            },
          ),
        ),
      ),
    );
    await tester.tap(find.text('Goodbye'));
    await tester.pump();
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(outputs.single.plays, 1);
    expect(outputs.single.loaded.single, contains('zoacao_erro_'));
    expect(find.text('Resposta: Hello'), findsOneWidget);
    expect(find.text('Hello é uma saudação.'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Continuar'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();
    expect(outputs.single.disposed, isTrue);
    await tester.tap(find.byTooltip('Feedback de áudio: Zoação leve'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sem áudio'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Thank you');
    await tester.pump();
    await tester.ensureVisible(find.text('Verificar'));
    await tester.tap(find.text('Verificar'));
    await tester.pumpAndSettle();
    expect(find.text('Muito bem!'), findsOneWidget);
    expect(outputs, hasLength(1));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
