import 'dart:async';
import 'dart:convert';
import 'dart:io';

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

Size _pngSize(String path) {
  final bytes = _file(path).readAsBytesSync();
  expect(bytes.take(8), [137, 80, 78, 71, 13, 10, 26, 10], reason: path);
  final header = ByteData.sublistView(bytes);
  return Size(header.getUint32(16).toDouble(), header.getUint32(20).toDouble());
}

Future<void> _loadLogo(WidgetTester tester) async {
  await tester.runAsync(
    () => precacheImage(
      const AssetImage(FluentLogo.assetPath),
      tester.element(find.byType(FluentLogo).first),
    ),
  );
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(loadBrandFonts);

  testWidgets('uses the supplied image without tint, cropping or distortion', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: fluentTheme,
        home: const Scaffold(body: Center(child: FluentLogo(size: 120))),
      ),
    );
    await _loadLogo(tester);
    final image = tester.widget<Image>(find.byType(Image));
    expect((image.image as AssetImage).assetName, 'logo.png');
    expect(image.fit, BoxFit.contain);
    expect(image.color, isNull);
    expect(image.colorBlendMode, isNull);
    expect(image.width, 120);
    expect(image.height, 120);
    expect(
      find.descendant(
        of: find.byType(FluentLogo),
        matching: find.byType(CustomPaint),
      ),
      findsNothing,
    );
    final semantics = tester.widget<Semantics>(
      find
          .descendant(
            of: find.byType(FluentLogo),
            matching: find.byType(Semantics),
          )
          .first,
    );
    expect(semantics.properties.image, isTrue);
    expect(semantics.properties.label, 'Fluent');
    expect(semantics.container, isTrue);
    final original = _pngSize('logo.png');
    final fitted = applyBoxFit(image.fit!, original, const Size(120, 120));
    expect(fitted.source, original);
    expect(
      fitted.destination.aspectRatio,
      closeTo(original.aspectRatio, 0.0001),
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('wordmark retains Genhead and fits with enlarged text', (
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
    await _loadLogo(tester);
    final text = tester.widget<Text>(find.text('fluent'));
    expect(text.style!.fontFamily, kFontBrand);
    expect(text.style!.fontWeight, FontWeight.w700);
    expect(text.style!.color, kTextPrimary);
    expect(
      tester.getSize(find.byType(FluentWordmark)).width,
      lessThanOrEqualTo(110),
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  test(
    'original logo is bundled and the full-size platform copies are identical',
    () async {
      final source = _file('logo.png').readAsBytesSync();
      final bundled = await rootBundle.load(FluentLogo.assetPath);
      expect(
        bundled.buffer.asUint8List(
          bundled.offsetInBytes,
          bundled.lengthInBytes,
        ),
        source,
      );
      expect(_file('web/logo.png').readAsBytesSync(), source);
      expect(
        _file(
          'android/app/src/main/res/drawable-nodpi/brand_logo.png',
        ).readAsBytesSync(),
        source,
      );
      expect(_file('web/favicon.svg').existsSync(), isFalse);
      expect(
        _file('android/app/src/main/res/drawable/ic_launcher.xml').existsSync(),
        isFalse,
      );
      final manifest =
          jsonDecode(_file('assets/branding/manifest.json').readAsStringSync())
              as Map<String, dynamic>;
      expect(manifest['source'], FluentLogo.assetPath);
      expect(manifest['preserveEntireImage'], isTrue);
      expect(
        Size(manifest['width'].toDouble(), manifest['height'].toDouble()),
        _pngSize('logo.png'),
      );
    },
  );

  test('all launcher densities and web icon sizes reference the new artwork', () {
    for (final (density, scale) in [
      ('mdpi', 1.0),
      ('hdpi', 1.5),
      ('xhdpi', 2.0),
      ('xxhdpi', 3.0),
      ('xxxhdpi', 4.0),
    ]) {
      expect(
        _pngSize('android/app/src/main/res/mipmap-$density/ic_launcher.png'),
        Size.square(48 * scale),
      );
      expect(
        _pngSize(
          'android/app/src/main/res/drawable-$density/ic_launcher_foreground.png',
        ),
        Size.square(108 * scale),
      );
    }
    final android = _file(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    expect(android, contains('android:icon="@mipmap/ic_launcher"'));
    expect(android, contains('android:roundIcon="@mipmap/ic_launcher"'));
    final adaptive = _file(
      'android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml',
    ).readAsStringSync();
    expect(adaptive, contains('@color/background_dark'));
    expect(adaptive, contains('@drawable/ic_launcher_foreground'));
    expect(
      _file(
        'android/app/src/main/res/values-v31/styles.xml',
      ).readAsStringSync(),
      contains(
        'name="android:windowSplashScreenAnimatedIcon">@mipmap/ic_launcher',
      ),
    );
    final splash = _file(
      'android/app/src/main/res/drawable/launch_background.xml',
    ).readAsStringSync();
    expect(splash, contains('@drawable/brand_logo'));
    expect(splash, contains('android:width="180dp" android:height="120dp"'));
    expect(_pngSize('web/favicon.png'), const Size.square(32));
    expect(_pngSize('web/icons/apple-touch-icon.png'), const Size.square(180));
    final web =
        jsonDecode(_file('web/manifest.json').readAsStringSync())
            as Map<String, dynamic>;
    final icons = (web['icons'] as List).cast<Map<String, dynamic>>();
    expect(icons, hasLength(4));
    for (final item in icons) {
      final size = double.parse((item['sizes'] as String).split('x').first);
      expect(_pngSize('web/${item['src']}'), Size.square(size));
      expect(item['type'], 'image/png');
    }
    expect(icons.map((icon) => icon['purpose']).toSet(), {'any', 'maskable'});
    final html = _file('web/index.html').readAsStringSync();
    expect(html, contains('href="favicon.png"'));
    expect(html, contains('href="icons/apple-touch-icon.png"'));
    expect(html, contains('class="loading-logo" src="logo.png" alt="Fluent"'));
    expect(
      _file('web/theme.css').readAsStringSync(),
      contains('object-fit: contain'),
    );
  });

  testWidgets('home and profile use the supplied logo', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await pumpFluentApp(tester);
    await _loadLogo(tester);
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

  testWidgets(
    'loading and startup error show the supplied logo and allow retry',
    (tester) async {
      const catalog = 'assets/courses/catalog.json';
      final assets = <String, ByteData>{
        for (final path in [FluentLogo.assetPath, 'AssetManifest.bin'])
          path: (await tester.runAsync(() => rootBundle.load(path)))!,
      };
      final pending = Completer<ByteData?>();
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      rootBundle.evict(catalog);
      messenger.setMockMessageHandler('flutter/assets', (message) async {
        final path = utf8.decode(
          message!.buffer.asUint8List(
            message.offsetInBytes,
            message.lengthInBytes,
          ),
        );
        if (path == catalog) return pending.future;
        if (!assets.containsKey(path)) {
          throw StateError('Unexpected asset request: $path');
        }
        return assets[path];
      });
      try {
        await tester.pumpWidget(const FluentApp());
        await _loadLogo(tester);
        expect(tester.widget<FluentLogo>(find.byType(FluentLogo)).size, 160);
        expect(find.byType(CircularProgressIndicator), findsOneWidget);
        pending.complete(null);
        await tester.pumpAndSettle();
        expect(tester.widget<FluentLogo>(find.byType(FluentLogo)).size, 120);
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
    },
  );
}
