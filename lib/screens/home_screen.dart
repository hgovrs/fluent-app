import 'dart:async';

import 'package:flutter/material.dart';

import '../models/course.dart';
import '../services/cloud_service.dart';
import '../state/learning_controller.dart';
import '../theme.dart';
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
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => LessonScreen(
        controller: widget.controller,
        exercises: lesson.exercises,
        lesson: lesson,
      ),
    ));
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
                Icon(Icons.spa_rounded, color: green),
                SizedBox(width: 8),
                Text('fluent', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: -1)),
              ],
            ),
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 20),
                child: Chip(
                  avatar: const Icon(Icons.local_fire_department_rounded, color: Color(0xFFBB631C)),
                  label: Text('${controller.progress.streak} dias'),
                  backgroundColor: const Color(0xFFFFEED4),
                  side: BorderSide.none,
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
                          color: const Color(0xFFFFEED4),
                          child: Text(controller.storageError!),
                        ),
                      ),
                    if (_tab == 0) ..._learn(context, controller),
                    if (_tab == 1) ..._review(context, controller),
                    if (_tab == 2)
                      ProfileScreen(controller: controller, cloud: widget.cloud),
                  ],
                ),
              ),
            ),
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _tab,
            onDestinationSelected: (value) => setState(() => _tab = value),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.route_outlined), selectedIcon: Icon(Icons.route), label: 'Aprender'),
              NavigationDestination(icon: Icon(Icons.style_outlined), selectedIcon: Icon(Icons.style), label: 'Revisar'),
              NavigationDestination(icon: Icon(Icons.person_outline_rounded), selectedIcon: Icon(Icons.person_rounded), label: 'Meu espaço'),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _learn(BuildContext context, LearningController controller) {
    final progress = controller.progress;
    final next = controller.nextLesson;
    final ratio = (progress.dailyXp / progress.dailyGoal).clamp(0.0, 1.0).toDouble();
    return [
      Text('Um pouco hoje.\nUm mundo amanhã.', style: Theme.of(context).textTheme.headlineLarge),
      const SizedBox(height: 8),
      const Text('Seu próximo passo começa com poucos minutos.'),
      if (controller.courses.length > 1) ...[
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: controller.course.id,
          key: ValueKey(controller.course.id),
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Escolha sua trilha'),
          items: [
            for (final course in controller.courses)
              DropdownMenuItem(
                value: course.id,
                child: Text(course.title, overflow: TextOverflow.ellipsis),
              ),
          ],
          onChanged: (id) {
            if (id != null) controller.selectCourse(id);
          },
        ),
      ],
      if (controller.course.coverage.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text(controller.course.coverage),
      ],
      TextButton.icon(
        onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => const SourcesScreen(),
        )),
        icon: const Icon(Icons.menu_book_outlined),
        label: const Text('Fontes e licenças'),
      ),
      const SizedBox(height: 24),
      SurfaceCard(
        color: mint,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.public_rounded, color: green, size: 32),
              const SizedBox(width: 12),
              Expanded(child: Text(controller.course.title, style: Theme.of(context).textTheme.titleLarge)),
            ]),
            const SizedBox(height: 8),
            Text(controller.course.level),
            const SizedBox(height: 14),
            Text(next == null ? 'Você concluiu esta trilha de prática!' : next.title,
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            Text(next == null
                ? 'Continue revisando para manter suas palavras por perto.'
                : next.description),
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: next == null ? () => setState(() => _tab = 1) : () => _openLesson(next),
                icon: const Icon(Icons.arrow_forward_rounded),
                label: Text(next == null ? 'Ir para revisão' : 'Começar lição'),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 16),
      SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.wb_sunny_rounded, color: Color(0xFFAD7619)),
              const SizedBox(width: 10),
              Expanded(child: Text(progress.dailyXp >= progress.dailyGoal ? 'Meta do dia alcançada!' : 'Sua meta de hoje',
                  style: Theme.of(context).textTheme.titleMedium)),
              Text('${progress.dailyXp}/${progress.dailyGoal} XP'),
            ]),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: ratio,
              minHeight: 8,
              borderRadius: BorderRadius.circular(8),
              backgroundColor: mint,
              semanticsLabel: 'Meta diária',
              semanticsValue: '${progress.dailyXp} de ${progress.dailyGoal} XP',
            ),
            const SizedBox(height: 8),
            const Text('Sem pressa, sem perder vidas. Cada tentativa ensina.'),
          ],
        ),
      ),
      const SizedBox(height: 28),
      Text('Sua trilha', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 4),
      const Text('Um novo idioma, uma conquista de cada vez.'),
      for (final (index, unit) in controller.course.units.indexed) ...[
        const SizedBox(height: 24),
        Row(children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(color: mint, borderRadius: BorderRadius.circular(12)),
            alignment: Alignment.center,
            child: Text('${index + 1}', style: const TextStyle(fontWeight: FontWeight.w800, color: green)),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(unit.title, style: Theme.of(context).textTheme.titleMedium),
            Text(unit.description),
          ])),
        ]),
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
      Text('Relembrar é aprender.', style: Theme.of(context).textTheme.headlineLarge),
      const SizedBox(height: 8),
      const Text('As palavras voltam na hora certa para ficar na memória.'),
      const SizedBox(height: 24),
      SurfaceCard(
        color: mint,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.auto_awesome_rounded, color: green, size: 48),
            const SizedBox(height: 16),
            Text(due.isEmpty ? 'Tudo em dia por aqui!' : '${due.length} exercícios para rever',
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 8),
            Text(due.isEmpty
                ? 'Faça uma lição ou volte depois. Suas revisões aparecerão aqui automaticamente.'
                : 'Uma sessão curta, feita com o que você já estudou.'),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: due.isEmpty ? null : () {
                  Navigator.of(context).push(MaterialPageRoute<void>(
                    builder: (_) => LessonScreen(
                      controller: controller,
                      exercises: due.take(10).toList(),
                    ),
                  ));
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
            Text('Como funciona?', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
            SizedBox(height: 12),
            Text('1. Aprenda palavras e frases nas lições.\n'
                '2. Reveja seus erros mais cedo, sem penalidades.\n'
                '3. Acerte nas revisões para aumentar o intervalo.'),
          ],
        ),
      ),
    ];
  }
}

class _LessonTile extends StatelessWidget {
  const _LessonTile({required this.lesson, required this.completed, required this.unlocked, required this.onTap});

  final Lesson lesson;
  final bool completed;
  final bool unlocked;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: completed ? mint : Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: unlocked ? green.withValues(alpha: 0.18) : Colors.black12),
      ),
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        enabled: unlocked,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: unlocked ? green : const Color(0xFFE8EBE5),
          child: Icon(completed ? Icons.check_rounded : unlocked ? Icons.play_arrow_rounded : Icons.lock_outline_rounded,
              color: unlocked ? Colors.white : Colors.grey),
        ),
        title: Text(lesson.title, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(completed ? 'Concluída · praticar novamente' : unlocked ? '${lesson.exercises.length} exercícios · +20 XP + bônus' : 'Conclua a lição anterior'),
        trailing: unlocked ? const Icon(Icons.chevron_right_rounded) : null,
        onTap: unlocked ? onTap : null,
      ),
    );
  }
}
