import 'dart:async';

import 'package:flutter/material.dart';

import '../models/course.dart';
import '../services/cloud_service.dart';
import '../state/learning_controller.dart';
import '../theme.dart';
import '../widgets/course_picker_button.dart';
import '../widgets/feedback_theme_button.dart';
import 'lesson_screen.dart';
import 'profile_screen.dart';
import 'sources_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.controller, required this.cloud});

  final LearningController controller;
  final CloudService cloud;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  int _tab = 0;
  Timer? _refresh;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refresh = Timer.periodic(const Duration(minutes: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) setState(() {});
  }

  @override
  void dispose() {
    _refresh?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _openLesson(Lesson lesson) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LessonScreen(
          controller: widget.controller,
          exercises: lesson.exercises,
          lesson: lesson,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.controller,
      builder: (context, _) {
        final controller = widget.controller;
        return Scaffold(
          appBar: AppBar(
            title: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.spa_rounded, color: kBrandPurpleLight),
                SizedBox(width: 8),
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text('fluent', style: kBrandHeadlineStyle),
                  ),
                ),
              ],
            ),
            actions: [
              FeedbackThemeButton(controller: controller),
              Padding(
                padding: const EdgeInsets.only(right: 20),
                child: Chip(
                  avatar: const Icon(
                    Icons.local_fire_department_rounded,
                    color: kBrandCoral,
                    size: kIconSize,
                  ),
                  label: Text('${controller.progress.streak} dias'),
                  backgroundColor: kCoralSurface,
                  side: const BorderSide(
                    color: kCoralBorder,
                    width: kBorderWidth,
                  ),
                ),
              ),
            ],
          ),
          body: SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 680),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    if (controller.storageError != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: SurfaceCard(
                          compact: true,
                          child: Text(
                            controller.storageError!,
                            style: const TextStyle(color: kError),
                          ),
                        ),
                      ),
                    if (_tab == 0) ..._learn(context, controller),
                    if (_tab == 1) ..._review(context, controller),
                    if (_tab == 2)
                      ProfileScreen(
                        controller: controller,
                        cloud: widget.cloud,
                      ),
                  ],
                ),
              ),
            ),
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _tab,
            onDestinationSelected: (value) => setState(() => _tab = value),
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.route_outlined),
                selectedIcon: Icon(Icons.route),
                label: 'Aprender',
              ),
              NavigationDestination(
                icon: Icon(Icons.style_outlined),
                selectedIcon: Icon(Icons.style),
                label: 'Revisar',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: 'Meu espaço',
              ),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _learn(BuildContext context, LearningController controller) {
    final progress = controller.progress;
    final next = controller.nextLesson;
    final ratio = (progress.dailyXp / progress.dailyGoal)
        .clamp(0.0, 1.0)
        .toDouble();
    return [
      CoursePickerButton(controller: controller),
      const SizedBox(height: 20),
      Semantics(
        container: true,
        header: true,
        child: Text(
          'Um pouco hoje.\nUm mundo amanhã.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
      ),
      const SizedBox(height: 16),
      SurfaceCard(
        key: const ValueKey('next-lesson-card'),
        emphasized: true,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        next == null
                            ? 'Trilha concluída'
                            : 'Próxima lição · ${next.exercises.length} exercícios',
                        style: kSelectedChipTextStyle,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        next == null
                            ? 'Você concluiu esta trilha de prática!'
                            : next.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
                if (next != null) ...[
                  const SizedBox(width: 12),
                  IconButton(
                    tooltip: 'Detalhes da próxima lição',
                    icon: const Icon(Icons.info_outline_rounded),
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (context) => AlertDialog(
                        title: Text(next.title),
                        content: SingleChildScrollView(
                          child: SelectableText(next.description),
                        ),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(context),
                            child: const Text('Fechar'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
            if (next == null) ...[
              const SizedBox(height: 8),
              const Text(
                'Continue revisando para manter suas palavras por perto.',
                style: kSecondaryTextStyle,
              ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: PrimaryButton.icon(
                onPressed: next == null
                    ? () => setState(() => _tab = 1)
                    : () => _openLesson(next),
                icon: const Icon(Icons.arrow_forward_rounded),
                label: Text(next == null ? 'Ir para revisão' : 'Começar lição'),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      SurfaceCard(
        compact: true,
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const BrandIconBox(Icons.wb_sunny_rounded),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      Text(
                        progress.dailyXp >= progress.dailyGoal
                            ? 'Meta alcançada!'
                            : 'Meta diária',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      Text(
                        '${progress.dailyXp}/${progress.dailyGoal} XP',
                        style: kSelectedChipTextStyle,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: ratio,
                    minHeight: 8,
                    borderRadius: kPillRadius,
                    color: kBrandPurpleLight,
                    backgroundColor: kSurfacePurpleRaised,
                    semanticsLabel:
                        'Meta diária: ${progress.dailyXp} de ${progress.dailyGoal} XP',
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 12,
        runSpacing: 4,
        children: [
          Semantics(
            container: true,
            header: true,
            child: Text(
              'Sua trilha',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          TextButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const SourcesScreen()),
            ),
            icon: const Icon(Icons.menu_book_outlined),
            label: const Text('Fontes e licenças'),
          ),
        ],
      ),
      for (final (index, unit) in controller.course.units.indexed) ...[
        const SizedBox(height: 16),
        Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: const BoxDecoration(
                color: kSurfacePurple,
                borderRadius: kIconRadius,
              ),
              alignment: Alignment.center,
              child: Text(
                '${index + 1}',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  color: kBrandPurpleLight,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    unit.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(unit.description, style: kSecondaryTextStyle),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        for (final lesson in unit.lessons)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _LessonTile(
              lesson: lesson,
              completed: controller.isCompleted(lesson),
              unlocked: controller.isUnlocked(lesson),
              onTap: () => _openLesson(lesson),
            ),
          ),
      ],
    ];
  }

  List<Widget> _review(BuildContext context, LearningController controller) {
    final due = controller.dueExercises;
    return [
      Text(
        'Relembrar é aprender.',
        style: Theme.of(context).textTheme.headlineLarge,
      ),
      const SizedBox(height: 8),
      const Text(
        'As palavras voltam na hora certa para ficar na memória.',
        style: kSecondaryTextStyle,
      ),
      const SizedBox(height: 24),
      SurfaceCard(
        emphasized: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const BrandIconBox(Icons.auto_awesome_rounded),
            const SizedBox(height: 16),
            Text(
              due.isEmpty
                  ? 'Tudo em dia por aqui!'
                  : '${due.length} exercícios para rever',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              due.isEmpty
                  ? 'Faça uma lição ou volte depois. Suas revisões aparecerão aqui automaticamente.'
                  : 'Uma sessão curta, feita com o que você já estudou.',
              style: kSecondaryTextStyle,
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: PrimaryButton.icon(
                onPressed: due.isEmpty
                    ? null
                    : () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => LessonScreen(
                              controller: controller,
                              exercises: due.take(10).toList(),
                            ),
                          ),
                        );
                      },
                icon: const Icon(Icons.replay_rounded),
                label: const Text('Revisar agora'),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      const SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Como funciona?',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
            SizedBox(height: 12),
            Text(
              '1. Aprenda palavras e frases nas lições.\n'
              '2. Reveja seus erros mais cedo, sem penalidades.\n'
              '3. Acerte nas revisões para aumentar o intervalo.',
              style: kSecondaryTextStyle,
            ),
          ],
        ),
      ),
    ];
  }
}

class _LessonTile extends StatelessWidget {
  const _LessonTile({
    required this.lesson,
    required this.completed,
    required this.unlocked,
    required this.onTap,
  });

  final Lesson lesson;
  final bool completed;
  final bool unlocked;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: completed ? kSurfacePurpleRaised : kSurfacePurple,
      shape: RoundedRectangleBorder(
        borderRadius: kCardRadius,
        side: BorderSide(
          color: unlocked ? kSurfaceBorder : kFieldBorder,
          width: kBorderWidth,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        enabled: unlocked,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: BrandIconBox(
          completed
              ? Icons.check_rounded
              : unlocked
              ? Icons.play_arrow_rounded
              : Icons.lock_outline_rounded,
          color: completed
              ? kBrandPurpleLight
              : unlocked
              ? kBrandPurple
              : kTextHint,
        ),
        title: Text(
          lesson.title,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: unlocked ? kTextPrimary : kTextHint,
          ),
        ),
        subtitle: Text(
          completed
              ? 'Concluída · praticar novamente'
              : unlocked
              ? '${lesson.exercises.length} exercícios · +20 XP + bônus'
              : 'Conclua a lição anterior',
          style: TextStyle(
            color: unlocked ? kTextSecondary : kTextHint,
            fontSize: 14,
          ),
        ),
        trailing: unlocked
            ? const Icon(Icons.chevron_right_rounded, color: kBrandPurpleLight)
            : null,
        onTap: unlocked ? onTap : null,
      ),
    );
  }
}
