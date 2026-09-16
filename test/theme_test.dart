import 'dart:convert';
import 'dart:io';

import 'package:fluent_app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

File _file(String path) => File.fromUri(Directory.current.uri.resolve(path));

String _hex(Color color) =>
    '#${color.toARGB32().toRadixString(16).substring(2).toUpperCase()}';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('the palette and translucent recipes match the design system', () {
    expect(kBackgroundDark.toARGB32(), 0xFF0D0D0D);
    expect(kBrandPurple.toARGB32(), 0xFF6064A6);
    expect(kBrandPurpleLight.toARGB32(), 0xFF9195D9);
    expect(kBrandPurpleDeep.toARGB32(), 0xFF363A8D);
    expect(kBrandCoral.toARGB32(), 0xFFF27166);
    expect(kBrandCoralLight.toARGB32(), 0xFFF28E85);
    expect(kTextPrimary, Colors.white);
    expect(kError, Colors.red.shade300);
    expect(kTextSecondary, kTextPrimary.withValues(alpha: 0.70));
    expect(kTextHint, kTextPrimary.withValues(alpha: 0.60));
    expect(kTextPlaceholder, kTextPrimary.withValues(alpha: 0.20));
    expect(kTextChip, kTextPrimary.withValues(alpha: 0.90));
    expect(kSurfacePurple, kBrandPurple.withValues(alpha: 0.15));
    expect(kSurfacePurpleRaised, kBrandPurple.withValues(alpha: 0.18));
    expect(kSurfaceBorder, kBrandPurpleLight.withValues(alpha: 0.35));
    expect(kFieldBorder, kBrandPurple.withValues(alpha: 0.30));
    expect(kIconMuted, kBrandPurpleLight.withValues(alpha: 0.60));
    expect(kPurpleGlow, kBrandPurple.withValues(alpha: 0.30));
    expect(kCoralSurface, kBrandCoral.withValues(alpha: 0.15));
    expect(kCoralBorder, kBrandCoralLight.withValues(alpha: 0.35));
    expect(kImageVeil, kBackgroundDark.withValues(alpha: 0.70));
    expect(
      kOverlaySurface,
      Color.alphaBlend(kSurfacePurpleRaised, kBackgroundDark),
    );
    expect(kImageOverlayGradient.colors, [kTransparent, kBackgroundDark]);
    expect(kPrimaryGradient.colors, [kBrandPurple, kBrandPurpleLight]);
    expect(kPrimaryGradient.begin, Alignment.centerLeft);
    expect(kPrimaryGradient.end, Alignment.centerRight);
    expect(kPrimaryShadow.color, kPurpleGlow);
    expect(kPrimaryShadow.blurRadius, 16);
    expect(kPrimaryShadow.offset, const Offset(0, 6));
  });

  test('dark theme covers text, controls, overlays and system bars', () {
    expect(fluentTheme.brightness, Brightness.dark);
    expect(fluentTheme.scaffoldBackgroundColor, kBackgroundDark);
    expect(fluentTheme.canvasColor, kBackgroundDark);
    expect(fluentTheme.colorScheme.surface, kBackgroundDark);
    expect(fluentTheme.colorScheme.surfaceTint, kTransparent);
    expect(fluentTheme.shadowColor, kPurpleGlow);
    expect(fluentTheme.applyElevationOverlayColor, isFalse);
    for (final style in [
      fluentTheme.textTheme.headlineLarge,
      fluentTheme.textTheme.headlineMedium,
      fluentTheme.textTheme.headlineSmall,
      fluentTheme.textTheme.titleLarge,
      fluentTheme.textTheme.bodyLarge,
      fluentTheme.textTheme.bodyMedium,
      fluentTheme.textTheme.labelSmall,
    ]) {
      expect(style!.fontFamily, kFontBody);
    }
    expect(kBrandHeadlineStyle.fontFamily, kFontBrand);
    expect(kBrandHeadlineStyle.fontWeight, FontWeight.w700);
    expect(fluentTheme.textTheme.headlineLarge!.fontSize, 24);
    expect(fluentTheme.textTheme.bodyLarge!.fontSize, 16);
    expect(fluentTheme.textTheme.bodyMedium!.fontSize, 14);
    expect(kChipTextStyle.fontSize, 11);
    expect(kChipTextStyle.fontWeight, FontWeight.w600);
    expect(kButtonTextStyle.fontSize, 16);
    expect(kButtonTextStyle.fontWeight, FontWeight.w700);

    final field = fluentTheme.inputDecorationTheme;
    expect(field.hintStyle!.color, kTextPlaceholder);
    expect(field.labelStyle!.color, kTextHint);
    expect(field.errorStyle!.color, kError);
    expect(field.enabledBorder!.borderSide.color, kFieldBorder);
    expect(field.focusedBorder!.borderSide.color, kBrandPurple);
    expect((field.border! as OutlineInputBorder).borderRadius, kSmallRadius);
    expect(fluentTheme.textSelectionTheme.cursorColor, kBrandPurple);
    expect(fluentTheme.chipTheme.padding, kChipPadding);
    expect(fluentTheme.chipTheme.labelPadding, EdgeInsets.zero);
    expect(
      (fluentTheme.chipTheme.shape! as RoundedRectangleBorder).borderRadius,
      kPillRadius,
    );
    expect(fluentTheme.dialogTheme.backgroundColor, kOverlaySurface);
    expect(fluentTheme.dialogTheme.barrierColor, kImageVeil);
    expect(fluentTheme.bottomSheetTheme.modalBackgroundColor, kOverlaySurface);
    expect(fluentTheme.bottomSheetTheme.modalBarrierColor, kImageVeil);
    expect(fluentTheme.snackBarTheme.backgroundColor, kOverlaySurface);
    expect(fluentTheme.progressIndicatorTheme.color, kBrandPurple);
    expect(
      fluentTheme.appBarTheme.systemOverlayStyle!.statusBarColor,
      kBackgroundDark,
    );
    expect(
      fluentTheme.appBarTheme.systemOverlayStyle!.systemNavigationBarColor,
      kBackgroundDark,
    );

    final navigation = fluentTheme.navigationBarTheme;
    expect(navigation.backgroundColor, kBackgroundDark);
    expect(navigation.iconTheme!.resolve({})!.color, kBrandPurple);
    expect(
      navigation.iconTheme!.resolve({WidgetState.selected})!.color,
      kBrandPurpleLight,
    );
    expect(navigation.labelTextStyle!.resolve({})!.color, kTextHint);
    expect(
      navigation.labelTextStyle!.resolve({WidgetState.selected})!.color,
      kBrandPurpleLight,
    );
  });

  test(
    'font assets are packaged with explicit weights and italic styles',
    () async {
      final manifest =
          (jsonDecode(await rootBundle.loadString('FontManifest.json'))
                  as List<Object?>)
              .cast<Map<String, Object?>>();
      final tech = manifest.singleWhere((font) => font['family'] == kFontBody);
      final genhead = manifest.singleWhere(
        (font) => font['family'] == kFontBrand,
      );
      expect(tech['fonts'], [
        {'asset': 'assets/fonts/santech-thin.otf', 'weight': 100},
        {
          'asset': 'assets/fonts/santech-thinitalic.otf',
          'weight': 100,
          'style': 'italic',
        },
        {'asset': 'assets/fonts/santech-regular.otf', 'weight': 400},
        {
          'asset': 'assets/fonts/santech-italic.otf',
          'weight': 400,
          'style': 'italic',
        },
        {'asset': 'assets/fonts/santech-semibold.otf', 'weight': 600},
        {
          'asset': 'assets/fonts/santech-semibolditalic.otf',
          'weight': 600,
          'style': 'italic',
        },
      ]);
      expect(genhead['fonts'], [
        {'asset': 'assets/fonts/genhead.otf', 'weight': 400},
        {'asset': 'assets/fonts/genhead-semibild.otf', 'weight': 700},
      ]);
      final assets = [
        for (final family in [tech, genhead])
          for (final font
              in (family['fonts']! as List<Object?>)
                  .cast<Map<String, Object?>>())
            font['asset']! as String,
        'assets/fonts/genhead-bold.otf',
      ];
      for (final asset in assets) {
        final data = await rootBundle.load(asset);
        expect(data.lengthInBytes, greaterThan(0), reason: asset);
        expect(
          data.getUint32(0),
          0x4F54544F,
          reason: '$asset must be OpenType',
        );
      }
    },
  );

  test('screens use central tokens instead of literal or generated colors', () {
    final lib = Directory.fromUri(Directory.current.uri.resolve('lib/'));
    for (final file in lib.listSync(recursive: true).whereType<File>()) {
      if (!file.path.endsWith('.dart') ||
          file.uri.pathSegments.last == 'theme.dart') {
        continue;
      }
      final source = file.readAsStringSync();
      expect(
        source,
        isNot(matches(RegExp(r'\b(?:Color\s*\(|Colors\.)'))),
        reason: file.path,
      );
      expect(
        source,
        isNot(contains('ColorScheme.fromSeed')),
        reason: file.path,
      );
      expect(source, isNot(contains('BlendMode.')), reason: file.path);
      expect(source, isNot(contains('kBrandPurpleDeep')), reason: file.path);
      expect(source, isNot(contains('FilledButton')), reason: file.path);
    }
  });

  test('web and Android bootstrap resources mirror the same palette', () {
    final background = _hex(kBackgroundDark);
    final purple = _hex(kBrandPurple);
    final white = _hex(kTextPrimary);
    final manifest =
        jsonDecode(_file('web/manifest.json').readAsStringSync())
            as Map<String, Object?>;
    expect(manifest['background_color'], background);
    expect(manifest['theme_color'], background);
    final html = _file('web/index.html').readAsStringSync();
    expect(html, contains('name="theme-color" content="$background"'));
    expect(html, contains('href="theme.css"'));
    final css = _file('web/theme.css').readAsStringSync();
    expect(css, contains('--background-dark: $background'));
    expect(css, contains('--brand-purple: $purple'));
    expect(css, contains('--text-primary: $white'));
    expect(css, contains('assets/assets/fonts/santech-regular.otf'));
    expect(css, isNot(contains('system-ui')));
    expect(css, isNot(contains('mix-blend-mode')));
    final colors = _file(
      'android/app/src/main/res/values/colors.xml',
    ).readAsStringSync();
    expect(colors, contains('name="background_dark">$background</color>'));
    expect(colors, contains('name="brand_purple">$purple</color>'));
    expect(colors, contains('name="text_primary">$white</color>'));
    final styles = _file(
      'android/app/src/main/res/values/styles.xml',
    ).readAsStringSync();
    expect(styles, isNot(contains('Theme.Light')));
    expect(styles, contains('name="android:windowLightStatusBar">false'));
    expect(styles, contains('name="android:windowLightNavigationBar">false'));
    final splash = _file(
      'android/app/src/main/res/values-v31/styles.xml',
    ).readAsStringSync();
    expect(
      splash,
      contains(
        'name="android:windowSplashScreenBackground">@color/background_dark',
      ),
    );
    expect(
      _file(
        'android/app/src/main/res/drawable/launch_background.xml',
      ).readAsStringSync(),
      contains('@color/background_dark'),
    );
  });

  testWidgets('primary CTA keeps transparent material and disabled behavior', (
    tester,
  ) async {
    var taps = 0;
    Widget host({required bool enabled}) => MaterialApp(
      theme: fluentTheme,
      home: Scaffold(
        body: Center(
          child: PrimaryButton(
            onPressed: enabled ? () => taps++ : null,
            child: const Text('Continuar'),
          ),
        ),
      ),
    );
    BoxDecoration decoration() =>
        tester
                .widget<DecoratedBox>(
                  find
                      .descendant(
                        of: find.byType(PrimaryButton),
                        matching: find.byType(DecoratedBox),
                      )
                      .first,
                )
                .decoration
            as BoxDecoration;

    await tester.pumpWidget(host(enabled: true));
    expect(decoration().gradient, kPrimaryGradient);
    expect(decoration().borderRadius, kCardRadius);
    expect(decoration().boxShadow, [kPrimaryShadow]);
    final style = fluentTheme.elevatedButtonTheme.style!;
    for (final states in <Set<WidgetState>>[
      {},
      {WidgetState.pressed},
      {WidgetState.focused},
      {WidgetState.disabled},
    ]) {
      expect(style.backgroundColor!.resolve(states), kTransparent);
      expect(style.shadowColor!.resolve(states), kTransparent);
      expect(style.surfaceTintColor!.resolve(states), kTransparent);
      expect(style.elevation!.resolve(states), 0);
    }
    await tester.tap(find.text('Continuar'));
    expect(taps, 1);
    await tester.pumpWidget(host(enabled: false));
    await tester.pumpAndSettle();
    expect(decoration().gradient, isNull);
    expect(decoration().boxShadow, isNull);
    expect(decoration().color, kSurfacePurpleRaised);
    expect(
      tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed,
      isNull,
    );
    await tester.tap(find.text('Continuar'));
    expect(taps, 1);
  });

  testWidgets('surfaces, icon boxes and loading use the specified geometry', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: fluentTheme,
        home: const Scaffold(
          body: Column(
            children: [
              SurfaceCard(child: Text('Surface')),
              SurfaceCard(
                compact: true,
                emphasized: true,
                child: Text('Small'),
              ),
              BrandIconBox(Icons.star_outline_rounded),
              SizedBox(height: 64, child: AppLoading()),
            ],
          ),
        ),
      ),
    );
    final cards = find.byType(SurfaceCard);
    BoxDecoration card(int index) =>
        tester
                .widget<Container>(
                  find
                      .descendant(
                        of: cards.at(index),
                        matching: find.byType(Container),
                      )
                      .first,
                )
                .decoration!
            as BoxDecoration;
    expect(card(0).color, kSurfacePurple);
    expect(card(0).borderRadius, kCardRadius);
    expect(card(0).border, Border.all(color: kSurfaceBorder, width: 0.8));
    expect(card(1).color, kSurfacePurpleRaised);
    expect(card(1).borderRadius, kSmallRadius);
    final iconBox = tester.widget<Container>(
      find.descendant(
        of: find.byType(BrandIconBox),
        matching: find.byType(Container),
      ),
    );
    expect(iconBox.padding, const EdgeInsets.all(8));
    expect((iconBox.decoration! as BoxDecoration).borderRadius, kIconRadius);
    final icon = tester.widget<Icon>(find.byIcon(Icons.star_outline_rounded));
    expect(icon.size, 20);
    expect(icon.color, kIconMuted);
    final spinner = tester.widget<CircularProgressIndicator>(
      find.byType(CircularProgressIndicator),
    );
    expect(spinner.color, kBrandPurple);
    expect(
      tester
          .widget<ColoredBox>(
            find.descendant(
              of: find.byType(AppLoading),
              matching: find.byType(ColoredBox),
            ),
          )
          .color,
      kBackgroundDark,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
