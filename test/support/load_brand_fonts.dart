import 'package:fluent_app/theme.dart';
import 'package:flutter/services.dart';

Future<void> loadBrandFonts() async {
  for (final entry in {
    kFontBody: [
      'assets/fonts/santech-regular.otf',
      'assets/fonts/santech-semibold.otf',
    ],
    kFontBrand: [
      'assets/fonts/genhead.otf',
      'assets/fonts/genhead-semibild.otf',
    ],
  }.entries) {
    final loader = FontLoader(entry.key);
    for (final asset in entry.value) {
      loader.addFont(rootBundle.load(asset));
    }
    await loader.load();
  }
}
