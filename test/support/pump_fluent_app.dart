import 'package:fluent_app/main.dart';
import 'package:fluent_app/services/cloud_service.dart';
import 'package:fluent_app/state/learning_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> pumpAssetRoute<T>(
  WidgetTester tester,
  Future<void> Function() show,
) async {
  // AssetBundle decoding and IO must finish outside the widget fake clock.
  await tester.runAsync(() async {
    await show();
    await tester.pump();
    final future = tester
        .widget<FutureBuilder<T>>(
          find.byType(FutureBuilder<T>, skipOffstage: false),
        )
        .future!;
    await future.timeout(const Duration(seconds: 20));
  });
  expect(tester.takeException(), isNull);
  await tester.pumpAndSettle();
}

Future<void> pumpFluentApp(WidgetTester tester) =>
    pumpAssetRoute<(LearningController, CloudService)>(
      tester,
      () => tester.pumpWidget(const FluentApp()),
    );
