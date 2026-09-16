import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';

import '../models/feedback_catalog.dart';

enum FeedbackAudioStatus { idle, loading, playing, unavailable }

abstract interface class FeedbackAudioOutput {
  Future<void> load(String assetPath);
  Future<void> play();
  Future<void> dispose();
}

class _JustAudioOutput implements FeedbackAudioOutput {
  final AudioPlayer _player = AudioPlayer();
  Future<void>? _closing;

  @override
  Future<void> load(String assetPath) async {
    await _player.setAsset(assetPath);
  }

  @override
  Future<void> play() async {
    final completed = Completer<void>();
    final errors = _player.errorStream.listen((error) {
      if (!completed.isCompleted) completed.completeError(error);
    });
    try {
      unawaited(
        _player.play().then(
          (_) {
            if (!completed.isCompleted) completed.complete();
          },
          onError: (Object error, StackTrace stack) {
            if (!completed.isCompleted) completed.completeError(error, stack);
          },
        ),
      );
      await completed.future;
    } finally {
      await errors.cancel();
    }
  }

  @override
  Future<void> dispose() => _closing ??= _player.dispose();
}

class FeedbackAudioPlayer extends ChangeNotifier {
  FeedbackAudioPlayer({FeedbackAudioOutput Function()? createOutput})
    : _createOutput = createOutput ?? _JustAudioOutput.new;

  final FeedbackAudioOutput Function() _createOutput;
  FeedbackAudioOutput? _output;
  int _revision = 0;
  bool _disposed = false;
  FeedbackAudioStatus _status = FeedbackAudioStatus.idle;

  FeedbackAudioStatus get status => _status;

  Future<void> play(FeedbackClip clip) async {
    if (_disposed) return;
    final revision = ++_revision;
    final previous = _output;
    _output = null;
    _setStatus(FeedbackAudioStatus.loading);
    await _close(previous);
    if (!_current(revision)) return;
    FeedbackAudioOutput? output;
    try {
      output = _createOutput();
      _output = output;
      await output.load(clip.assetPath).timeout(const Duration(seconds: 8));
      if (!_current(revision)) return;
      _setStatus(FeedbackAudioStatus.playing);
      await output.play().timeout(const Duration(seconds: 30));
      if (_current(revision)) _setStatus(FeedbackAudioStatus.idle);
    } catch (_) {
      if (_current(revision)) _setStatus(FeedbackAudioStatus.unavailable);
    } finally {
      if (identical(_output, output)) _output = null;
      await _close(output);
    }
  }

  Future<void> stop() async {
    ++_revision;
    final output = _output;
    _output = null;
    _setStatus(FeedbackAudioStatus.idle);
    await _close(output);
  }

  bool _current(int revision) => !_disposed && revision == _revision;

  Future<void> _close(FeedbackAudioOutput? output) async {
    try {
      await output?.dispose().timeout(const Duration(seconds: 2));
    } catch (_) {
      // Audio is optional and must never block an exercise or navigation.
    }
  }

  void _setStatus(FeedbackAudioStatus value) {
    if (_disposed || _status == value) return;
    _status = value;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    unawaited(stop());
    super.dispose();
  }
}
