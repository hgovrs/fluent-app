import 'package:flutter/material.dart';

import '../models/feedback_catalog.dart';
import '../state/learning_controller.dart';
import '../theme.dart';
import 'selection_tile.dart';

class FeedbackThemeButton extends StatelessWidget {
  const FeedbackThemeButton({
    super.key,
    required this.controller,
    this.onOpening,
  });

  final LearningController controller;
  final VoidCallback? onOpening;

  Future<void> _choose(BuildContext context) async {
    onOpening?.call();
    final selected = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * 0.75,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Feedback de áudio',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              const Text(
                'Escolha o clima das reações a acertos e erros. '
                'A preferência vale para este curso e pode mudar a qualquer hora.',
                style: kSecondaryTextStyle,
              ),
              const SizedBox(height: 12),
              SelectionTile(
                icon: Icons.volume_off_rounded,
                title: 'Sem áudio',
                subtitle: 'Somente a correção escrita.',
                selected: controller.feedbackThemeId == FeedbackCatalog.off,
                onTap: () => Navigator.pop(context, FeedbackCatalog.off),
              ),
              for (final theme in controller.feedbackCatalog.themes)
                SelectionTile(
                  icon: controller.feedbackThemeId == theme.id
                      ? Icons.check_circle_rounded
                      : Icons.volume_up_rounded,
                  title: theme.name,
                  subtitle:
                      '${theme.description}\n'
                      'Acerto: ${theme.clips.firstWhere((clip) => clip.category == FeedbackCategory.correct).text}\n'
                      'Erro: ${theme.clips.firstWhere((clip) => clip.category == FeedbackCategory.incorrect).text}',
                  selected: controller.feedbackThemeId == theme.id,
                  onTap: () => Navigator.pop(context, theme.id),
                ),
              if (controller.feedbackCatalog.themes.isEmpty)
                const Text(
                  'Os temas de áudio não estão disponíveis nesta versão.',
                  style: TextStyle(color: kTextHint),
                ),
              const SizedBox(height: 12),
              const Text(
                'As frases também aparecem por escrito. Se o áudio não estiver '
                'disponível, a aula continua normalmente.',
                style: kSecondaryTextStyle,
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null && context.mounted) {
      await controller.setFeedbackTheme(selected);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => IconButton(
      tooltip:
          'Feedback de áudio: ${controller.feedbackTheme?.name ?? 'Sem áudio'}',
      icon: Icon(
        controller.feedbackTheme == null
            ? Icons.volume_off_rounded
            : Icons.volume_up_rounded,
        color: controller.feedbackTheme == null
            ? kBrandPurple
            : kBrandPurpleLight,
      ),
      onPressed: () => _choose(context),
    ),
  );
}
