import 'package:flutter/material.dart';

import '../models/course.dart';
import '../state/learning_controller.dart';
import '../theme.dart';
import 'selection_tile.dart';

class CoursePickerButton extends StatelessWidget {
  const CoursePickerButton({super.key, required this.controller});

  final LearningController controller;

  Future<void> _showDetails(BuildContext context, Course course) =>
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(course.title),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  course.level,
                  style: const TextStyle(color: kBrandPurpleLight),
                ),
                const SizedBox(height: 12),
                Text(_lessonCount(course)),
                if (course.coverage.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  SelectableText(course.coverage),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Fechar'),
            ),
          ],
        ),
      );

  Future<void> _choose(BuildContext context) async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * 0.8,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Semantics(
                        container: true,
                        header: true,
                        child: Text(
                          'Escolha sua trilha',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Fechar seleção de trilha',
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  children: [
                    for (final course in controller.courses)
                      SelectionTile(
                        key: ValueKey('course-option-${course.id}'),
                        icon: controller.course.id == course.id
                            ? Icons.check_circle_rounded
                            : Icons.public_rounded,
                        title: course.title,
                        subtitle: _lessonCount(course),
                        selected: controller.course.id == course.id,
                        onTap: () => Navigator.pop(context, course.id),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
                child: TextButton.icon(
                  onPressed: () => _showDetails(context, controller.course),
                  icon: const Icon(Icons.info_outline_rounded),
                  label: const Text('Sobre a trilha atual'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null && context.mounted) {
      await controller.selectCourse(selected);
    }
  }

  static String _lessonCount(Course course) {
    final count = course.lessons.length;
    return '$count ${count == 1 ? 'lição' : 'lições'}';
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) {
      final course = controller.course;
      final canSwitch = controller.courses.length > 1;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          OutlinedButton(
            key: const ValueKey('course-picker'),
            onPressed: () =>
                canSwitch ? _choose(context) : _showDetails(context, course),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.all(16),
              alignment: Alignment.centerLeft,
            ),
            child: Row(
              children: [
                const BrandIconBox(Icons.public_rounded),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        course.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        canSwitch ? 'Trocar trilha' : 'Sobre esta trilha',
                        style: kSelectedChipTextStyle,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Icon(
                  canSwitch
                      ? Icons.unfold_more_rounded
                      : Icons.info_outline_rounded,
                ),
              ],
            ),
          ),
          if (course.coverage.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'Prática parcial, sem certificação.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      );
    },
  );
}
