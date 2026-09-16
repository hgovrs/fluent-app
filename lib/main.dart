import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'data/course_catalog.dart';
import 'data/feedback_catalog_loader.dart';
import 'models/feedback_catalog.dart';
import 'screens/home_screen.dart';
import 'services/cloud_service.dart';
import 'services/progress_store.dart';
import 'state/learning_controller.dart';
import 'widgets/fluent_logo.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FluentApp());
}

class FluentApp extends StatefulWidget {
  const FluentApp({super.key});

  @override
  State<FluentApp> createState() => _FluentAppState();
}

class _FluentAppState extends State<FluentApp> {
  late Future<(LearningController, CloudService)> _startup;

  @override
  void initState() {
    super.initState();
    _startup = _load();
  }

  Future<(LearningController, CloudService)> _load() async {
    final courses = await CourseCatalog.load();
    FeedbackCatalog feedbackCatalog;
    try {
      feedbackCatalog = await FeedbackCatalogLoader.load();
    } catch (_) {
      feedbackCatalog = FeedbackCatalog([]);
    }
    final controller = LearningController(
      courses: courses,
      store: ProgressStore(),
      feedbackCatalog: feedbackCatalog,
    );
    await controller.load();
    final cloud = await CloudService.initialize();
    return (controller, cloud);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Fluent',
      debugShowCheckedModeBanner: false,
      theme: fluentTheme,
      locale: const Locale('pt', 'BR'),
      supportedLocales: const [Locale('pt', 'BR')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: FutureBuilder<(LearningController, CloudService)>(
        future: _startup,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Scaffold(
              body: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const FluentLogo(size: 72),
                      const SizedBox(height: 16),
                      const Icon(Icons.cloud_off_rounded, size: 40),
                      const SizedBox(height: 16),
                      const Text('Não conseguimos abrir seu curso. Tente novamente.'),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: () => setState(() => _startup = _load()),
                        child: const Text('Tentar novamente'),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Scaffold(
              body: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FluentLogo(size: 96),
                    SizedBox(height: 20),
                    Text(
                      'fluent',
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -1,
                        color: ink,
                      ),
                    ),
                    SizedBox(height: 24),
                    CircularProgressIndicator(),
                  ],
                ),
              ),
            );
          }
          return HomeScreen(controller: snapshot.data!.$1, cloud: snapshot.data!.$2);
        },
      ),
    );
  }
}
