import 'dart:async';

import 'package:flutter/material.dart';

import '../models/course.dart';
import '../models/feedback_catalog.dart';
import '../services/feedback_audio_player.dart';
import '../state/learning_controller.dart';
import '../theme.dart';
import '../widgets/feedback_voice_button.dart';
import 'sources_screen.dart';

class LessonScreen extends StatefulWidget {
  const LessonScreen({
    super.key,
    required this.controller,
    required this.exercises,
    this.lesson,
    this.createFeedbackPlayer,
  });

  final LearningController controller;
  final List<Exercise> exercises;
  final Lesson? lesson;
  final FeedbackAudioPlayer Function()? createFeedbackPlayer;

  @override
  State<LessonScreen> createState() => _LessonScreenState();
}

class _LessonScreenState extends State<LessonScreen>
    with WidgetsBindingObserver {
  final _text = TextEditingController();
  final Map<String, bool> _results = {};
  final List<int> _words = [];
  int _index = 0;
  String? _choice;
  bool? _correct;
  bool _finished = false;
  bool _saving = false;
  bool _allowPop = false;
  int _earnedXp = 0;
  late final FeedbackAudioPlayer _audio;
  final _feedbackPicker = FeedbackPicker();
  FeedbackClip? _feedback;
  late String _voiceId;

  @override
  void initState() {
    super.initState();
    _audio = widget.createFeedbackPlayer?.call() ?? FeedbackAudioPlayer();
    _voiceId = widget.controller.feedbackVoiceId;
    widget.controller.addListener(_voiceChanged);
    WidgetsBinding.instance.addObserver(this);
  }

  void _voiceChanged() {
    final voiceId = widget.controller.feedbackVoiceId;
    if (_voiceId == voiceId) return;
    _voiceId = voiceId;
    unawaited(_audio.stop());
    setState(() => _feedback = null);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) unawaited(_audio.stop());
  }

  Exercise get _exercise => widget.exercises[_index];

  String get _answer => switch (_exercise.type) {
    ExerciseType.choice => _choice ?? '',
    ExerciseType.typed => _text.text,
    ExerciseType.wordOrder => _words.map((i) => _exercise.options[i]).join(' '),
  };

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.controller.removeListener(_voiceChanged);
    _audio.dispose();
    _text.dispose();
    super.dispose();
  }

  Future<void> _exit() async {
    if (_saving) return;
    unawaited(_audio.stop());
    if (_finished) {
      Navigator.of(context).pop();
      return;
    }
    final exit = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sair desta prática?'),
        content: const Text(
          'O progresso desta sessão ainda não será salvo. Você pode começar de novo quando quiser.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Continuar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sair'),
          ),
        ],
      ),
    );
    if (exit == true && mounted) {
      setState(() => _allowPop = true);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) Navigator.of(context).pop();
      });
    }
  }

  void _check() {
    if (_correct != null || _saving || _answer.trim().isEmpty) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _correct = _exercise.accepts(_answer);
      _results[_exercise.id] = _correct!;
      final voice = widget.controller.feedbackVoice;
      _feedback = voice == null
          ? null
          : _feedbackPicker.pick(
              voice,
              _correct! ? FeedbackCategory.correct : FeedbackCategory.incorrect,
            );
    });
    if (_feedback != null) unawaited(_audio.play(_feedback!));
  }

  Future<void> _continue() async {
    unawaited(_audio.stop());
    _feedback = null;
    if (_index < widget.exercises.length - 1) {
      setState(() {
        _index++;
        _choice = null;
        _correct = null;
        _words.clear();
        _text.clear();
      });
      return;
    }
    setState(() => _saving = true);
    final before = widget.controller.progress.totalXp;
    try {
      if (widget.lesson != null) {
        await widget.controller.completeLesson(widget.lesson!, _results);
      } else {
        await widget.controller.completeReview(_results);
      }
      if (!mounted) return;
      setState(() {
        _earnedXp = widget.controller.progress.totalXp - before;
        _finished = true;
        _saving = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não foi possível salvar. Tente novamente.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _finished || _allowPop,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) _exit();
      },
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          leading: IconButton(
            tooltip: 'Sair da prática',
            onPressed: _saving ? null : _exit,
            icon: const Icon(Icons.close_rounded),
          ),
          title: Text(widget.lesson?.title ?? 'Revisão do dia'),
          actions: [
            if (widget.lesson?.studyNotes.isNotEmpty ?? false)
              IconButton(
                tooltip: 'Material de estudo',
                icon: const Icon(Icons.menu_book_outlined),
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Antes de praticar'),
                    content: SingleChildScrollView(
                      child: SelectableText(widget.lesson!.studyNotes),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Voltar à prática'),
                      ),
                    ],
                  ),
                ),
              ),
            FeedbackVoiceButton(
              controller: widget.controller,
              onOpening: () => unawaited(_audio.stop()),
            ),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 640),
              child: _finished ? _summary(context) : _question(context),
            ),
          ),
        ),
      ),
    );
  }

  Widget _summary(BuildContext context) {
    final correct = _results.values.where((value) => value).length;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 28),
        const Center(
          child: BrandIconBox(
            Icons.emoji_events_rounded,
            color: kBrandPurpleLight,
          ),
        ),
        const SizedBox(height: 28),
        Text(
          'Mais um passo dado!',
          style: Theme.of(context).textTheme.headlineLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        const Text(
          'O importante é continuar. O que foi difícil volta na revisão.',
          style: kSecondaryTextStyle,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 28),
        SurfaceCard(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Column(
                children: [
                  Text(
                    '+$_earnedXp',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: kBrandPurpleLight,
                    ),
                  ),
                  const Text('XP ganhos', style: kSecondaryTextStyle),
                ],
              ),
              Column(
                children: [
                  Text(
                    '$correct/${_results.length}',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: kBrandPurpleLight,
                    ),
                  ),
                  const Text('acertos', style: kSecondaryTextStyle),
                ],
              ),
            ],
          ),
        ),
        if (widget.controller.storageError != null) ...[
          const SizedBox(height: 16),
          Text(
            widget.controller.storageError!,
            style: const TextStyle(color: kError),
          ),
        ],
        const SizedBox(height: 28),
        PrimaryButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Continuar minha jornada'),
        ),
      ],
    );
  }

  Widget _question(BuildContext context) {
    final exercise = _exercise;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Row(
          children: [
            Expanded(
              child: LinearProgressIndicator(
                value: _index / widget.exercises.length,
                minHeight: 10,
                borderRadius: kPillRadius,
                color: kBrandPurpleLight,
                backgroundColor: kSurfacePurpleRaised,
                semanticsLabel: 'Progresso da sessão',
              ),
            ),
            const SizedBox(width: 16),
            Text(
              '${_index + 1}/${widget.exercises.length}',
              style: const TextStyle(color: kTextHint),
            ),
          ],
        ),
        const SizedBox(height: 28),
        if (widget.lesson?.studyNotes.isNotEmpty ?? false) ...[
          ExpansionTile(
            key: ValueKey('study-${widget.lesson!.id}'),
            title: const Text('Antes de praticar'),
            subtitle: const Text(
              'Leia a explicação e consulte durante a lição.',
              style: kSecondaryTextStyle,
            ),
            childrenPadding: const EdgeInsets.all(12),
            children: [
              SelectableText(widget.lesson!.studyNotes),
              if (widget.lesson!.sourceIds.isNotEmpty)
                TextButton(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) =>
                          SourcesScreen(sourceIds: widget.lesson!.sourceIds),
                    ),
                  ),
                  child: const Text('Leituras complementares e licenças'),
                ),
            ],
          ),
          const SizedBox(height: 16),
        ],
        Align(
          alignment: Alignment.centerLeft,
          child: Chip(
            label: Text(switch (exercise.type) {
              ExerciseType.choice => 'ESCOLHA A RESPOSTA',
              ExerciseType.typed => 'ESCREVA SUA RESPOSTA',
              ExerciseType.wordOrder => 'ORGANIZE A FRASE',
            }),
          ),
        ),
        const SizedBox(height: 12),
        if (exercise.context.isNotEmpty) ...[
          SurfaceCard(
            compact: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Texto de apoio',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                SelectableText(exercise.context),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        Text(
          exercise.prompt,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 28),
        if (exercise.type == ExerciseType.choice)
          ...exercise.options.map(
            (option) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Semantics(
                selected: _choice == option,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.all(18),
                    alignment: Alignment.centerLeft,
                    backgroundColor: _choice == option
                        ? kSurfacePurpleRaised
                        : kSurfacePurple,
                    disabledBackgroundColor: _choice == option
                        ? kSurfacePurpleRaised
                        : kSurfacePurple,
                    side: BorderSide(
                      color: _choice == option
                          ? kBrandPurpleLight
                          : kSurfaceBorder,
                      width: kBorderWidth,
                    ),
                    foregroundColor: _choice == option
                        ? kBrandPurpleLight
                        : kTextPrimary,
                    disabledForegroundColor: _choice == option
                        ? kBrandPurpleLight
                        : kTextHint,
                  ),
                  onPressed: _correct != null
                      ? null
                      : () => setState(() => _choice = option),
                  child: Text(option),
                ),
              ),
            ),
          ),
        if (exercise.type == ExerciseType.typed)
          TextField(
            controller: _text,
            enabled: _correct == null,
            autocorrect: false,
            enableSuggestions: false,
            textCapitalization: TextCapitalization.none,
            decoration: const InputDecoration(
              labelText: 'Sua resposta',
              hintText: 'Digite aqui…',
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) {
              if (_answer.trim().isNotEmpty && _correct == null) _check();
            },
          ),
        if (exercise.type == ExerciseType.wordOrder) ...[
          SurfaceCard(
            emphasized: true,
            child: _words.isEmpty
                ? const Text(
                    'Toque nas palavras abaixo para montar sua resposta.',
                    style: TextStyle(color: kTextHint),
                  )
                : Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final index in _words)
                        InputChip(
                          label: Text(exercise.options[index]),
                          selected: true,
                          showCheckmark: false,
                          labelStyle: kSelectedChipTextStyle,
                          onDeleted: _correct != null
                              ? null
                              : () => setState(() => _words.remove(index)),
                        ),
                    ],
                  ),
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final (index, word) in exercise.options.indexed)
                ActionChip(
                  label: Text(word),
                  onPressed: _correct != null || _words.contains(index)
                      ? null
                      : () => setState(() => _words.add(index)),
                ),
            ],
          ),
        ],
        const SizedBox(height: 24),
        if (_correct != null) ...[
          Semantics(
            liveRegion: true,
            child: SurfaceCard(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      BrandIconBox(
                        _correct!
                            ? Icons.check_rounded
                            : Icons.info_outline_rounded,
                        color: _correct! ? kBrandPurpleLight : kBrandCoral,
                        accent: !_correct!,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _correct! ? 'Muito bem!' : 'Vamos aprender com essa!',
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                color: _correct!
                                    ? kBrandPurpleLight
                                    : kTextPrimary,
                              ),
                        ),
                      ),
                    ],
                  ),
                  if (_feedback != null) ...[
                    const SizedBox(height: 8),
                    Text(_feedback!.text),
                    ListenableBuilder(
                      listenable: _audio,
                      builder: (context, _) => Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (_audio.status == FeedbackAudioStatus.loading)
                            const SizedBox(
                              height: 64,
                              child: AppLoading(
                                semanticsLabel: 'Carregando reação de áudio',
                              ),
                            ),
                          if (_audio.status == FeedbackAudioStatus.playing ||
                              _audio.status == FeedbackAudioStatus.loading)
                            TextButton.icon(
                              onPressed: () => unawaited(_audio.stop()),
                              icon: const Icon(Icons.stop_rounded),
                              label: const Text('Parar áudio'),
                            ),
                          if (_audio.status == FeedbackAudioStatus.unavailable)
                            const Text(
                              'Áudio indisponível. Você pode continuar pela correção escrita.',
                              style: TextStyle(color: kTextHint),
                            ),
                        ],
                      ),
                    ),
                  ],
                  if (!_correct!) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Resposta: ${exercise.answer}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(exercise.explanation, style: kSecondaryTextStyle),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
        ],
        if (_saving) ...[
          const SizedBox(
            height: 64,
            child: AppLoading(semanticsLabel: 'Salvando progresso'),
          ),
          const SizedBox(height: 12),
        ],
        PrimaryButton(
          onPressed: _saving
              ? null
              : _correct != null
              ? _continue
              : _answer.trim().isEmpty
              ? null
              : _check,
          child: Text(
            _saving
                ? 'Salvando…'
                : _correct != null
                ? 'Continuar'
                : 'Verificar',
          ),
        ),
      ],
    );
  }
}
