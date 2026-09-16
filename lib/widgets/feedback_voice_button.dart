import 'package:flutter/material.dart';

import '../models/feedback_catalog.dart';
import '../state/learning_controller.dart';

class FeedbackVoiceButton extends StatelessWidget {
  const FeedbackVoiceButton({
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
              Text('Voz do feedback',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              const Text(
                'Escolha a voz das reações a acertos e erros. '
                'A preferência vale para este curso e pode mudar a qualquer hora.',
              ),
              const SizedBox(height: 12),
              ListTile(
                leading: const Icon(Icons.volume_off_rounded),
                title: const Text('Sem áudio'),
                subtitle: const Text('Somente a correção escrita.'),
                selected: controller.feedbackVoiceId == FeedbackCatalog.off,
                onTap: () => Navigator.pop(context, FeedbackCatalog.off),
              ),
              for (final voice in controller.feedbackCatalog.voices)
                ListTile(
                  leading: Icon(controller.feedbackVoiceId == voice.id
                      ? Icons.check_circle_rounded
                      : Icons.record_voice_over_rounded),
                  title: Text(voice.name),
                  subtitle: Text('${voice.description}\n'
                      'Acerto: ${voice.clips.firstWhere((clip) => clip.category == FeedbackCategory.correct).text}\n'
                      'Erro: ${voice.clips.firstWhere((clip) => clip.category == FeedbackCategory.incorrect).text}'),
                  isThreeLine: true,
                  selected: controller.feedbackVoiceId == voice.id,
                  onTap: () => Navigator.pop(context, voice.id),
                ),
              if (controller.feedbackCatalog.voices.isEmpty)
                const Text('As vozes de áudio não estão disponíveis nesta versão.'),
              const SizedBox(height: 12),
              const Text(
                'As frases também aparecem por escrito. Se o áudio não estiver '
                'disponível, a aula continua normalmente.',
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null && context.mounted) {
      await controller.setFeedbackVoice(selected);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: controller,
        builder: (context, _) => IconButton(
          tooltip:
              'Voz do feedback: ${controller.feedbackVoice?.name ?? 'Sem áudio'}',
          icon: Icon(controller.feedbackVoice == null
              ? Icons.volume_off_rounded
              : Icons.record_voice_over_rounded),
          onPressed: () => _choose(context),
        ),
      );
}
