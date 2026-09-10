import 'package:flutter/material.dart';

const ink = Color(0xFF20352E);
const green = Color(0xFF287A56);
const mint = Color(0xFFE6F3E9);
const paper = Color(0xFFF8F9F4);
const amber = Color(0xFFF2BA54);

final fluentTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: paper,
  colorScheme: ColorScheme.fromSeed(seedColor: green, surface: paper),
  appBarTheme: const AppBarTheme(
    backgroundColor: paper,
    foregroundColor: ink,
    centerTitle: false,
    scrolledUnderElevation: 0,
  ),
  textTheme: const TextTheme(
    headlineLarge: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, color: ink),
    headlineMedium: TextStyle(fontSize: 27, fontWeight: FontWeight.w800, color: ink),
    titleLarge: TextStyle(fontSize: 21, fontWeight: FontWeight.w700, color: ink),
    titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: ink),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: ink),
    bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: ink),
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      minimumSize: const Size(48, 54),
      backgroundColor: green,
      foregroundColor: Colors.white,
      textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      minimumSize: const Size(48, 48),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
  ),
  navigationBarTheme: const NavigationBarThemeData(
    backgroundColor: Colors.white,
    indicatorColor: mint,
  ),
);

class SurfaceCard extends StatelessWidget {
  const SurfaceCard({
    super.key,
    required this.child,
    this.color = Colors.white,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;
  final Color color;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: ink.withValues(alpha: 0.08)),
    ),
    child: child,
  );
}
