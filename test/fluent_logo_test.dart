import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:fluent_app/main.dart';
import 'package:fluent_app/screens/profile_screen.dart';
import 'package:fluent_app/theme.dart';
import 'package:fluent_app/widgets/fluent_logo.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/load_brand_fonts.dart';
import 'support/pump_fluent_app.dart';

File _file(String path) => File.fromUri(Directory.current.uri.resolve(path));

String _attribute(String element, String name) => RegExp(
  '(?:^|\\s)${RegExp.escape(name)}="([^"]*)"',
).firstMatch(element)!.group(1)!;

List<String> _paths(String source) => RegExp(
  r'<path\b[^>]*>',
).allMatches(source).map((m) => m.group(0)!).toList();

List<Object> _pathTokens(String path) =>
    RegExp(r'[A-Za-z]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)').allMatches(path).map((
      match,
    ) {
      final token = match.group(0)!;
      return double.tryParse(token) ?? token;
    }).toList();

Future<ByteData> _rasterize(CustomPainter painter) async {
  final recorder = ui.PictureRecorder();
  painter.paint(Canvas(recorder), const Size(108, 108));
  final picture = recorder.endRecording();
  try {
    final image = await picture.toImage(108, 108);
    try {
      return (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
    } finally {
      image.dispose();
    }
  } finally {
    picture.dispose();
  }
}

List<int> _pixel(ByteData data, int x, int y) =>
    List.generate(4, (channel) => data.getUint8((y * 108 + x) * 4 + channel));

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(loadBrandFonts);

  for (final withBackground in [true, false]) {
    testWidgets('logo paints the approved colors, background=$withBackground', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: fluentTheme,
          home: Scaffold(
            body: Center(
              child: FluentLogo(size: 108, withBackground: withBackground),
            ),
          ),
        ),
      );
      final logo = find.byType(FluentLogo);
      final decoration =
          tester
                  .widget<DecoratedBox>(
                    find
                        .descendant(
                          of: logo,
                          matching: find.byType(DecoratedBox),
                        )
                        .first,
                  )
                  .decoration
              as BoxDecoration;
      expect(decoration.borderRadius, BorderRadius.circular(26));
      expect(decoration.boxShadow, withBackground ? [kPrimaryShadow] : null);
      final semantics = tester.widget<Semantics>(
        find.descendant(of: logo, matching: find.byType(Semantics)).first,
      );
      expect(semantics.properties.label, 'Fluent');
      expect(semantics.properties.image, isTrue);
      expect(semantics.container, isTrue);
      final painter = tester
          .widget<CustomPaint>(
            find.descendant(of: logo, matching: find.byType(CustomPaint)).first,
          )
          .painter!;
      await tester.runAsync(() async {
        final data = await _rasterize(painter);
        expect(
          _pixel(data, 24, 40),
          withBackground ? [255, 255, 255, 255] : [96, 100, 166, 255],
        );
        expect(
          _pixel(data, 44, 33),
          withBackground ? [96, 100, 166, 255] : [255, 255, 255, 255],
        );
        expect(_pixel(data, 76, 56), [242, 113, 102, 255]);
        expect(_pixel(data, 0, 0)[3], 0);
        if (withBackground) {
          expect(_pixel(data, 8, 40), _pixel(data, 8, 80));
          expect(_pixel(data, 8, 80)[0], lessThan(_pixel(data, 100, 80)[0]));
        } else {
          expect(_pixel(data, 8, 80)[3], 0);
        }
      });
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('wordmark retains branding without overflowing at large text', (
    tester,
  ) async {
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      MaterialApp(
        theme: fluentTheme,
        home: const Scaffold(
          body: Center(child: SizedBox(width: 110, child: FluentWordmark())),
        ),
      ),
    );
    final text = tester.widget<Text>(find.text('fluent'));
    expect(text.style!.fontFamily, kFontBrand);
    expect(text.style!.fontWeight, FontWeight.w700);
    expect(text.style!.color, kTextPrimary);
    expect(find.byType(ExcludeSemantics), findsWidgets);
    expect(
      tester.getSize(find.byType(FluentWordmark)).width,
      lessThanOrEqualTo(110),
    );
    expect(tester.takeException(), isNull);
  });

  test(
    'SVG and Android keep the same bubble, letter and horizontal gradient',
    () {
      final svg = _file('web/favicon.svg').readAsStringSync();
      final android = _file(
        'android/app/src/main/res/drawable/ic_launcher.xml',
      ).readAsStringSync();
      final svgPaths = _paths(svg);
      final androidPaths = _paths(android);
      for (final (id, color) in [
        ('bubble', 'text_primary'),
        ('letter', 'brand_purple'),
      ]) {
        final svgPath = svgPaths.singleWhere(
          (path) => _attribute(path, 'id') == id,
        );
        final androidPath = androidPaths.singleWhere(
          (path) => path.contains('android:fillColor="@color/$color"'),
        );
        expect(
          _pathTokens(_attribute(svgPath, 'd')),
          _pathTokens(_attribute(androidPath, 'android:pathData')),
        );
      }
      expect(svg, contains('viewBox="0 0 108 108"'));
      expect(svg, contains('width="108" height="108" rx="26"'));
      expect(svg, contains('x1="0" y1="0.5" x2="1" y2="0.5"'));
      expect(svg, contains('cx="76" cy="56" r="7" fill="#F27166"'));
      expect(android, contains('android:startX="0" android:startY="54"'));
      expect(android, contains('android:endX="108" android:endY="54"'));
      expect(android, contains('android:startColor="@color/brand_purple"'));
      expect(android, contains('android:endColor="@color/brand_purple_light"'));
      expect(android, contains('M76,49a7,7 0 1 1 0,14a7,7 0 1 1 0,-14z'));
      expect(
        RegExp(
          r'#[0-9A-Fa-f]{6}',
        ).allMatches(svg).map((m) => m.group(0)).toSet(),
        {'#6064A6', '#9195D9', '#FFFFFF', '#F27166'},
      );
      final colors = _file(
        'android/app/src/main/res/values/colors.xml',
      ).readAsStringSync();
      expect(colors, contains('name="brand_purple_light">#9195D9</color>'));
      expect(colors, contains('name="brand_coral">#F27166</color>'));
      expect(
        _file('web/index.html').readAsStringSync(),
        contains('class="loading-logo" src="favicon.svg" alt="Fluent"'),
      );
      expect(
        _file('web/theme.css').readAsStringSync(),
        contains('box-shadow: 0 6px 16px var(--purple-glow)'),
      );
      expect(
        _file(
          'android/app/src/main/res/drawable/launch_background.xml',
        ).readAsStringSync(),
        contains(
          'android:drawable="@drawable/ic_launcher" android:gravity="center"',
        ),
      );
    },
  );

  testWidgets('home and profile share the new mark', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await pumpFluentApp(tester);
    expect(find.byType(FluentWordmark), findsOneWidget);
    await tester.tap(find.text('Meu espaço'));
    await tester.pumpAndSettle();
    expect(
      find.descendant(
        of: find.byType(ProfileScreen),
        matching: find.byType(FluentLogo),
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('loading and startup error retain the logo and retry action', (
    tester,
  ) async {
    const catalog = 'assets/courses/catalog.json';
    final pending = Completer<ByteData?>();
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    rootBundle.evict(catalog);
    messenger.setMockMessageHandler('flutter/assets', (message) {
      final asset = utf8.decode(
        message!.buffer.asUint8List(
          message.offsetInBytes,
          message.lengthInBytes,
        ),
      );
      if (asset != catalog) {
        throw StateError('Unexpected asset request: $asset');
      }
      return pending.future;
    });
    try {
      await tester.pumpWidget(const FluentApp());
      expect(tester.widget<FluentLogo>(find.byType(FluentLogo)).size, 96);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(
        tester.widget<Text>(find.text('fluent')).style!.fontFamily,
        kFontBrand,
      );
      pending.complete(null);
      await tester.pumpAndSettle();
      expect(tester.widget<FluentLogo>(find.byType(FluentLogo)).size, 72);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(
        find.widgetWithText(PrimaryButton, 'Tentar novamente'),
        findsOneWidget,
      );
      expect(
        find.text('Não conseguimos abrir seu curso. Tente novamente.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    } finally {
      if (!pending.isCompleted) pending.complete(null);
      await tester.pumpWidget(const SizedBox());
      messenger.setMockMessageHandler('flutter/assets', null);
      rootBundle.evict(catalog);
    }
  });
}
