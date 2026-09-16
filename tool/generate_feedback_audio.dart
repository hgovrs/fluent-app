import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../lib/models/feedback_catalog.dart';

const maxAudioBytes = 10 * 1024 * 1024;
const _requestTimeout = Duration(seconds: 60);

const _usage = '''
Generate original Portuguese feedback with your own ElevenLabs custom voice.

dart run tool/generate_feedback_audio.dart --dry-run
dart run tool/generate_feedback_audio.dart --generate [--force]

--help      Show this help.
--dry-run   Validate the catalog and estimate usage without credentials/network.
--generate  Explicitly authorize chargeable synthesis requests.
--force     Replace existing clips. Required after changing text, model or voice.

Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment only.
Existing nonempty MP3 files with a recognized header are skipped by default.
No text/voice fingerprint is stored: use --force after changing either.
Each planned phrase makes one billable POST; failed requests are never retried.
Previously completed clips remain available if a later request fails.
''';

typedef AudioSynthesis = Future<List<int>> Function(SynthesisRequest request);

class GenerationException implements Exception {
  const GenerationException(this.message);

  final String message;
}

class SynthesisRequest {
  SynthesisRequest({
    required String voiceId,
    required String apiKey,
    required String text,
  })  : uri = Uri(
          scheme: 'https',
          host: 'api.elevenlabs.io',
          pathSegments: ['v1', 'text-to-speech', voiceId],
          queryParameters: {'output_format': 'mp3_44100_128'},
        ),
        headers = Map.unmodifiable({
          'xi-api-key': apiKey,
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg',
        }),
        body = Map.unmodifiable({
          'text': text,
          'model_id': 'eleven_multilingual_v2',
          'language_code': 'pt',
        });

  final Uri uri;
  final Map<String, String> headers;
  final Map<String, String> body;
  String get method => 'POST';
}

Directory repositoryRootForScript(Uri script) =>
    Directory.fromUri(script.resolve('../'));

Future<void> main(List<String> arguments) async {
  exitCode = await runFeedbackGeneration(
    arguments,
    repositoryRoot: repositoryRootForScript(Platform.script),
  );
}

Future<int> runFeedbackGeneration(
  List<String> arguments, {
  required Directory repositoryRoot,
  Map<String, String>? environment,
  AudioSynthesis? synthesize,
  void Function(String)? log,
}) async {
  final output = log ?? stdout.writeln;
  try {
    const allowed = {'--help', '--dry-run', '--generate', '--force'};
    if (arguments.any((argument) => !allowed.contains(argument))) {
      throw const GenerationException('Unknown argument. Use --help.');
    }
    if (arguments.contains('--help')) {
      output(_usage);
      return 0;
    }

    final dryRun = arguments.contains('--dry-run');
    final force = arguments.contains('--force');
    final catalogFile = File.fromUri(
      repositoryRoot.uri.resolve('assets/audio_feedback/catalog.json'),
    );
    final decoded = jsonDecode(await catalogFile.readAsString());
    if (decoded is! Map<String, dynamic>) {
      throw const GenerationException('Invalid feedback catalog.');
    }
    final catalog = FeedbackCatalog.fromJson(decoded);
    final clips = catalog.voices.expand((voice) => voice.clips).toList();
    final planned = <FeedbackClip>[];
    for (final clip in clips) {
      final file = File.fromUri(repositoryRoot.uri.resolve(clip.assetPath));
      if (force || !await _isExistingMp3(file)) {
        planned.add(clip);
      }
    }
    final characters =
        planned.fold<int>(0, (total, clip) => total + clip.text.runes.length);
    output(
      'Catalog: ${clips.length} phrases. Planned: ${planned.length} phrases, '
      '$characters characters. Skipped: ${clips.length - planned.length}.',
    );
    output('Use --force after changing text, model or voice.');
    if (dryRun) {
      output('Dry run: no requests sent and no files written.');
      return 0;
    }
    if (!arguments.contains('--generate')) {
      throw const GenerationException(
        'No requests sent. Use --generate to authorize charges, or --dry-run.',
      );
    }
    final env = environment ?? Platform.environment;
    final apiKey = env['ELEVENLABS_API_KEY']?.trim() ?? '';
    final voiceId = env['ELEVENLABS_VOICE_ID']?.trim() ?? '';
    if (apiKey.isEmpty || voiceId.isEmpty) {
      throw const GenerationException(
        'Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment.',
      );
    }
    final generate = synthesize ?? synthesizeWithElevenLabs;
    for (final clip in planned) {
      final bytes = await generate(SynthesisRequest(
        voiceId: voiceId,
        apiKey: apiKey,
        text: clip.text,
      ));
      _validateAudio(bytes);
      await _writeAtomically(
        File.fromUri(repositoryRoot.uri.resolve(clip.assetPath)),
        bytes,
      );
      output('Generated ${clip.assetPath}.');
    }
    output('Done: generated ${planned.length} clips.');
    return 0;
  } on GenerationException catch (error) {
    output('Error: ${error.message}');
  } on FormatException {
    output('Error: invalid feedback catalog.');
  } on TimeoutException {
    output('Error: synthesis timed out. No automatic retry was attempted.');
  } on FileSystemException {
    output('Error: unable to read the catalog or write audio files.');
  } catch (_) {
    // Provider and transport exceptions may contain credentials or response data.
    output('Error: generation failed. No automatic retry was attempted.');
  }
  return 1;
}

Future<List<int>> synthesizeWithElevenLabs(SynthesisRequest input) async {
  final client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 15);
  try {
    return await _sendRequest(client, input).timeout(_requestTimeout);
  } finally {
    client.close(force: true);
  }
}

Future<List<int>> _sendRequest(
  HttpClient client,
  SynthesisRequest input,
) async {
  final request = await client.openUrl(input.method, input.uri);
  request.followRedirects = false;
  input.headers.forEach((name, value) => request.headers.set(name, value));
  request.add(utf8.encode(jsonEncode(input.body)));
  final response = await request.close();
  return readSynthesisResponse(
    statusCode: response.statusCode,
    contentType: response.headers.contentType?.mimeType,
    contentLength: response.contentLength,
    body: response,
  );
}

// Kept separate from transport so rejection paths can be tested without a server.
Future<List<int>> readSynthesisResponse({
  required int statusCode,
  required String? contentType,
  required int contentLength,
  required Stream<List<int>> body,
}) async {
  if (statusCode != HttpStatus.ok) {
    throw GenerationException('ElevenLabs returned HTTP $statusCode.');
  }
  if (contentType?.toLowerCase() != 'audio/mpeg') {
    throw const GenerationException(
      'ElevenLabs returned an unexpected audio type.',
    );
  }
  if (contentLength > maxAudioBytes) {
    throw const GenerationException('Audio exceeds the size limit.');
  }
  final bytes = <int>[];
  await for (final chunk in body) {
    if (bytes.length + chunk.length > maxAudioBytes) {
      throw const GenerationException('Audio exceeds the size limit.');
    }
    bytes.addAll(chunk);
  }
  if (contentLength >= 0 && bytes.length != contentLength) {
    throw const GenerationException('Incomplete audio response.');
  }
  _validateAudio(bytes);
  return bytes;
}

void _validateAudio(List<int> bytes) {
  if (bytes.length > maxAudioBytes || !_hasMp3Header(bytes)) {
    throw const GenerationException('Empty, oversized or invalid MP3 response.');
  }
}

bool _hasMp3Header(List<int> bytes) {
  if (bytes.length < 10) return false;
  final hasId3 = bytes[0] == 0x49 &&
      bytes[1] == 0x44 &&
      bytes[2] == 0x33 &&
      bytes[3] >= 2 &&
      bytes[3] <= 4;
  final hasFrame = bytes[0] == 0xff &&
      (bytes[1] & 0xe0) == 0xe0 &&
      (bytes[1] & 0x18) != 0x08 &&
      (bytes[1] & 0x06) == 0x02 &&
      (bytes[2] & 0xf0) != 0 &&
      (bytes[2] & 0xf0) != 0xf0 &&
      (bytes[2] & 0x0c) != 0x0c;
  return hasId3 || hasFrame;
}

Future<bool> _isExistingMp3(File file) async {
  if (!await file.exists()) return false;
  final length = await file.length();
  if (length < 10 || length > maxAudioBytes) return false;
  final handle = await file.open();
  try {
    return _hasMp3Header(await handle.read(10));
  } finally {
    await handle.close();
  }
}

Future<void> _writeAtomically(File destination, List<int> bytes) async {
  await destination.parent.create(recursive: true);
  final staging = await destination.parent.createTemp('.feedback_generation_');
  try {
    final stagedFile = File.fromUri(staging.uri.resolve('clip.mp3'));
    await stagedFile.writeAsBytes(bytes, flush: true);
    await stagedFile.rename(destination.path);
  } finally {
    await staging.delete(recursive: true);
  }
}
