import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../tool/generate_feedback_audio.dart';

const _mp3 = <int>[0x49, 0x44, 0x33, 4, 0, 0, 0, 0, 0, 0, 0xff, 0xfb];
const _credentials = <String, String>{
  'ELEVENLABS_API_KEY': 'test-only-key',
  'ELEVENLABS_VOICE_ID': 'owner-custom-voice',
};

void main() {
  late Directory root;
  late File clip;
  late List<String> messages;
  late List<SynthesisRequest> requests;

  Future<List<int>> fakeSynthesis(SynthesisRequest request) async {
    requests.add(request);
    return _mp3;
  }

  Future<int> run(
    List<String> arguments, {
    Map<String, String> environment = _credentials,
    AudioSynthesis? synthesize,
  }) => runFeedbackGeneration(
    arguments,
    repositoryRoot: root,
    environment: environment,
    synthesize: synthesize ?? fakeSynthesis,
    log: messages.add,
  );

  setUp(() async {
    root = await Directory.systemTemp.createTemp(
      'fluent_feedback_generation_test_',
    );
    final catalog = File.fromUri(
      root.uri.resolve('assets/audio_feedback/catalog.json'),
    );
    await catalog.parent.create(recursive: true);
    await catalog.writeAsString(
      jsonEncode({
        'schemaVersion': 2,
        'voices': [
          {
            'id': 'natasha_caldeirao',
            'name': 'Natasha Caldeirão',
            'description': 'Feedback original.',
            'clips': [
              {'id': 'acerto_1', 'category': 'correct', 'text': 'Boa!'},
              {'id': 'erro_1', 'category': 'incorrect', 'text': 'Quase!'},
            ],
          },
        ],
      }),
    );
    clip = File.fromUri(
      root.uri.resolve('assets/audio_feedback/natasha_caldeirao_acerto_1.mp3'),
    );
    messages = [];
    requests = [];
  });

  tearDown(() async {
    await root.delete(recursive: true);
  });

  test('repository resolution uses the script location', () {
    expect(
      repositoryRootForScript(
        Uri.file('/project/tool/generate_feedback_audio.dart'),
      ).uri,
      Uri.directory('/project/'),
    );
  });

  test('help needs neither catalog nor credentials', () async {
    await File.fromUri(
      root.uri.resolve('assets/audio_feedback/catalog.json'),
    ).delete();
    expect(await run(['--help'], environment: {}), 0);
    expect(requests, isEmpty);
    expect(messages.join('\n'), contains('--force'));
  });

  test('dry run reports usage without credentials or network', () async {
    expect(await run(['--dry-run'], environment: {}), 0);
    expect(requests, isEmpty);
    expect(await clip.exists(), isFalse);
    expect(messages.first, contains('2 phrases, 10 characters'));
  });

  test('dry run wins even if generate is also supplied', () async {
    expect(await run(['--dry-run', '--generate'], environment: {}), 0);
    expect(requests, isEmpty);
  });

  test(
    'chargeable operations require explicit generate authorization',
    () async {
      expect(await run([]), 1);
      expect(requests, isEmpty);
      expect(messages.last, contains('--generate'));
    },
  );

  test('unknown flags never make requests', () async {
    expect(await run(['--generate', '--typo']), 1);
    expect(requests, isEmpty);
  });

  test('invalid catalog fails before requests or writes', () async {
    await File.fromUri(
      root.uri.resolve('assets/audio_feedback/catalog.json'),
    ).writeAsString('{"schemaVersion":2,"voices":[]}');
    expect(await run(['--generate']), 1);
    expect(requests, isEmpty);
    expect(await clip.exists(), isFalse);
    expect(messages.last, contains('invalid feedback catalog'));
  });

  test('missing or blank credentials stop before synthesis', () async {
    for (final environment in <Map<String, String>>[
      {},
      {'ELEVENLABS_API_KEY': 'test-only-key'},
      {'ELEVENLABS_VOICE_ID': 'owner-custom-voice'},
      {..._credentials, 'ELEVENLABS_API_KEY': '  '},
      {..._credentials, 'ELEVENLABS_VOICE_ID': '  '},
    ]) {
      expect(await run(['--generate'], environment: environment), 1);
    }
    expect(requests, isEmpty);
    expect(await clip.exists(), isFalse);
  });

  test('maps catalog text and owner voice to a single POST per clip', () async {
    expect(await run(['--generate']), 0);
    expect(requests, hasLength(2));
    final request = requests.first;
    expect(request.method, 'POST');
    expect(
      request.uri.toString(),
      'https://api.elevenlabs.io/v1/text-to-speech/owner-custom-voice'
      '?output_format=mp3_44100_128',
    );
    expect(request.headers, {
      'xi-api-key': 'test-only-key',
      'Content-Type': 'application/json',
      'Accept': 'audio/mpeg',
    });
    expect(request.body, {
      'text': 'Boa!',
      'model_id': 'eleven_multilingual_v2',
      'language_code': 'pt',
    });
    expect(await clip.readAsBytes(), _mp3);
    expect(
      await File.fromUri(
        root.uri.resolve('assets/audio_feedback/natasha_caldeirao_erro_1.mp3'),
      ).readAsBytes(),
      _mp3,
    );
    expect((await clip.parent.list().toList()).whereType<Directory>(), isEmpty);
    expect(messages.join('\n'), isNot(contains('test-only-key')));
  });

  test('voice ID is encoded as exactly one path segment', () {
    final request = SynthesisRequest(
      voiceId: 'custom/voice ?#',
      apiKey: 'test-only-key',
      text: 'Boa!',
    );
    expect(request.uri.host, 'api.elevenlabs.io');
    expect(request.uri.pathSegments, [
      'v1',
      'text-to-speech',
      'custom/voice ?#',
    ]);
    expect(request.uri.queryParameters, {'output_format': 'mp3_44100_128'});
  });

  test('existing valid MP3 is skipped unless force is supplied', () async {
    await clip.writeAsBytes(_mp3);
    expect(await run(['--generate']), 0);
    expect(requests.map((request) => request.body['text']), ['Quase!']);
    requests.clear();
    expect(await run(['--generate', '--force']), 0);
    expect(requests, hasLength(2));
  });

  test('empty and non-MP3 files are regenerated', () async {
    for (final contents in [<int>[], utf8.encode('this is not an MP3')]) {
      await clip.writeAsBytes(contents);
      requests.clear();
      expect(await run(['--generate']), 0);
      expect(requests.first.body['text'], 'Boa!');
      expect(await clip.readAsBytes(), _mp3);
    }
  });

  test(
    'provider failure stops immediately without overwriting old audio',
    () async {
      await clip.writeAsBytes(_mp3);
      var calls = 0;
      for (final status in [401, 429]) {
        expect(
          await run(
            ['--generate', '--force'],
            synthesize: (_) async {
              calls++;
              throw GenerationException('ElevenLabs returned HTTP $status.');
            },
          ),
          1,
        );
        expect(messages.last, contains('HTTP $status'));
        expect(await clip.readAsBytes(), _mp3);
      }
      expect(calls, 2);
      expect(
        (await clip.parent.list().toList()).whereType<Directory>(),
        isEmpty,
      );
    },
  );

  test('unexpected failures never expose transport secrets', () async {
    expect(
      await run(
        ['--generate'],
        synthesize: (_) async {
          throw Exception('test-only-key private provider response');
        },
      ),
      1,
    );
    expect(messages.join('\n'), isNot(contains('test-only-key')));
    expect(messages.join('\n'), isNot(contains('private provider response')));
  });

  test('timeouts stop without retries or incomplete output', () async {
    var calls = 0;
    expect(
      await run(
        ['--generate'],
        synthesize: (_) async {
          calls++;
          throw TimeoutException('test-only-key');
        },
      ),
      1,
    );
    expect(calls, 1);
    expect(await clip.exists(), isFalse);
    expect(messages.last, contains('timed out'));
    expect(messages.join('\n'), isNot(contains('test-only-key')));
  });

  test('later failure preserves completed clips for a resumable run', () async {
    var calls = 0;
    expect(
      await run(
        ['--generate'],
        synthesize: (_) async {
          if (++calls == 2) {
            throw const GenerationException('ElevenLabs returned HTTP 429.');
          }
          return _mp3;
        },
      ),
      1,
    );
    expect(calls, 2);
    expect(await clip.readAsBytes(), _mp3);
    expect(await run(['--generate']), 0);
    expect(requests.map((request) => request.body['text']), ['Quase!']);
  });

  test('invalid synthesized bytes preserve old audio with force', () async {
    await clip.writeAsBytes(_mp3);
    expect(
      await run(['--generate', '--force'], synthesize: (_) async => []),
      1,
    );
    expect(await clip.readAsBytes(), _mp3);
    expect((await clip.parent.list().toList()).whereType<Directory>(), isEmpty);
  });

  test('failed atomic rename removes staging files', () async {
    final blockedDestination = Directory(clip.path);
    await blockedDestination.create();
    final marker = File.fromUri(
      blockedDestination.uri.resolve('preserve-existing-content'),
    );
    await marker.writeAsString('preserve');
    expect(await run(['--generate', '--force']), 1);
    expect(await marker.readAsString(), 'preserve');
    final directories = (await clip.parent.list().toList())
        .whereType<Directory>()
        .toList();
    expect(directories.map((directory) => directory.path), [clip.path]);
    expect(requests, hasLength(1));
  });

  group('response validation without HTTP', () {
    Future<List<int>> read({
      int status = 200,
      String? mime = 'audio/mpeg',
      int? length,
      List<List<int>> chunks = const [_mp3],
    }) => readSynthesisResponse(
      statusCode: status,
      contentType: mime,
      contentLength: length ?? _mp3.length,
      body: Stream.fromIterable(chunks),
    );

    test('accepts bounded MPEG audio', () async {
      expect(await read(), _mp3);
    });

    test('rejects redirects and authentication or quota failures', () async {
      for (final status in [301, 302, 307, 308, 401, 429, 500]) {
        await expectLater(
          read(status: status),
          throwsA(isA<GenerationException>()),
        );
      }
    });

    test('rejects missing or incorrect MIME and empty responses', () async {
      for (final mime in [null, 'application/json', 'text/html']) {
        await expectLater(
          read(mime: mime),
          throwsA(isA<GenerationException>()),
        );
      }
      await expectLater(
        read(length: 0, chunks: []),
        throwsA(isA<GenerationException>()),
      );
    });

    test('rejects declared and streamed oversized responses', () async {
      await expectLater(
        read(length: maxAudioBytes + 1),
        throwsA(isA<GenerationException>()),
      );
      final chunk = List<int>.filled(1024 * 1024, 0);
      await expectLater(
        read(length: -1, chunks: List.filled(11, chunk)),
        throwsA(isA<GenerationException>()),
      );
    });

    test(
      'rejects a truncated response or an interrupted body stream',
      () async {
        await expectLater(
          read(length: _mp3.length + 1),
          throwsA(isA<GenerationException>()),
        );
        await expectLater(
          readSynthesisResponse(
            statusCode: 200,
            contentType: 'audio/mpeg',
            contentLength: -1,
            body: Stream<List<int>>.error(const SocketException('Interrupted')),
          ),
          throwsA(isA<SocketException>()),
        );
      },
    );
  });
}
