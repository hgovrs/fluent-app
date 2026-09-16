"""Offline speech regression tests using generated PCM and mocked local models."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import wave

from tool import feedback_speech as speech
from tool import generate_feedback_gifs as generator


def write_pcm(path, samples, rate=10, channels=1):
    data = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(data)
    return data


def read_pcm(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getparams(), audio.readframes(audio.getnframes())


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix=".speech-test-", dir=Path.cwd())
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)


class SpeechOptionsTest(WorkspaceTest):
    def test_disabled_by_default_and_each_processing_option_enables_speech(self):
        self.assertFalse(speech.SpeechOptions().enabled)
        self.assertFalse(speech.SpeechOptions(voices_authorized=True).enabled)
        for option in ("extract_audio", "transcribe_model", "diarization_model", "speaker_segments"):
            with self.subTest(option=option):
                self.assertTrue(speech.SpeechOptions(**{option: True}).enabled)

    def test_valid_local_models_and_manual_segments(self):
        segments = self.root / "segments.json"
        segments.write_text("[]", encoding="utf-8")
        for options in (
            speech.SpeechOptions(),
            speech.SpeechOptions(extract_audio=True),
            speech.SpeechOptions(transcribe_model=self.root, language="pt"),
            speech.SpeechOptions(diarization_model=self.root, num_speakers=1,
                                 voices_authorized=True),
            speech.SpeechOptions(diarization_model=self.root, num_speakers=100,
                                 voices_authorized=True),
            speech.SpeechOptions(speaker_segments=segments, voices_authorized=True),
        ):
            with self.subTest(options=options):
                options.validate()

    def test_invalid_option_combinations_and_model_paths(self):
        file = self.root / "not-a-model"
        file.touch()
        invalid = [
            {"diarization_model": self.root, "speaker_segments": file,
             "voices_authorized": True},
            {"diarization_model": self.root},
            {"speaker_segments": file},
            {"language": "pt"},
            {"num_speakers": 2},
            {"transcribe_model": self.root / "missing"},
            {"transcribe_model": file},
            {"diarization_model": file, "voices_authorized": True},
            {"diarization_model": self.root / "missing", "voices_authorized": True},
            {"speaker_segments": self.root, "voices_authorized": True},
            {"speaker_segments": self.root / "missing.json", "voices_authorized": True},
            *({"diarization_model": self.root, "num_speakers": number,
               "voices_authorized": True} for number in (0, -1, 101)),
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(speech.SpeechError):
                speech.SpeechOptions(**values).validate()


class SpeechAdapterTest(WorkspaceTest):
    def assert_offline(self):
        self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")
        self.assertEqual(os.environ.get("HF_HUB_DISABLE_TELEMETRY"), "1")
        self.assertEqual(os.environ.get("PYANNOTE_METRICS_ENABLED"), "0")

    def test_transcription_is_local_only_and_consumes_lazy_segments(self):
        consumed = []

        def segments():
            consumed.append(True)
            yield SimpleNamespace(start=0.25, end=0.75, text="  Olá!  ")

        model = mock.Mock()
        model.transcribe.return_value = (segments(), SimpleNamespace(language="pt"))

        def load(*args, **kwargs):
            self.assert_offline()
            return model

        constructor = mock.Mock(side_effect=load)
        audio = self.root / "audio.wav"
        with mock.patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=constructor)}), \
                mock.patch.dict(os.environ, {}, clear=True):
            result = speech.transcribe(audio, self.root, "pt")
            self.assert_offline()
        constructor.assert_called_once_with(str(self.root.resolve()), device="cpu",
                                            compute_type="int8", local_files_only=True)
        model.transcribe.assert_called_once_with(str(audio), language="pt", vad_filter=True)
        self.assertEqual(consumed, [True])
        self.assertEqual(result, {"language": "pt", "segments": [
            {"start": 0.25, "end": 0.75, "text": "Olá!"},
        ]})

    def test_lazy_transcription_failure_becomes_actionable_error(self):
        def broken_segments():
            yield SimpleNamespace(start=0, end=0.5, text="partial")
            raise RuntimeError("private model internals")

        constructor = mock.Mock()
        constructor.return_value.transcribe.return_value = (
            broken_segments(), SimpleNamespace(language="en"),
        )
        with mock.patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=constructor)}), \
                mock.patch.dict(os.environ):
            with self.assertRaisesRegex(speech.SpeechError, "Falha na transcrição local") as error:
                speech.transcribe(self.root / "audio.wav", self.root, None)
        self.assertNotIn("private model internals", str(error.exception))

    def test_transcription_model_load_failure_is_actionable(self):
        constructor = mock.Mock(side_effect=RuntimeError("incomplete local model"))
        with mock.patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=constructor)}), \
                mock.patch.dict(os.environ):
            with self.assertRaisesRegex(speech.SpeechError, "modelo completo"):
                speech.transcribe(self.root / "audio.wav", self.root, None)

    def pyannote_modules(self, pipeline):
        return {
            "pyannote": SimpleNamespace(),
            "pyannote.audio": SimpleNamespace(Pipeline=pipeline),
            "pyannote.audio.pipelines": SimpleNamespace(SpeakerDiarization=mock.Mock),
        }

    def test_diarization_uses_local_pipeline_and_disables_telemetry(self):
        for number in (None, 2):
            with self.subTest(num_speakers=number):
                annotation = mock.Mock()
                annotation.itertracks.return_value = iter([
                    (SimpleNamespace(start=0.1, end=0.6), "track", "SPEAKER_00"),
                    (SimpleNamespace(start=0.7, end=1), "track", "SPEAKER_01"),
                ])
                instance = mock.Mock(return_value=SimpleNamespace(speaker_diarization=annotation))

                def load(*args, **kwargs):
                    self.assert_offline()
                    return instance

                pipeline = SimpleNamespace(from_pretrained=mock.Mock(side_effect=load))
                audio = self.root / "audio.wav"
                with mock.patch.dict(sys.modules, self.pyannote_modules(pipeline)), \
                        mock.patch.dict(os.environ, {}, clear=True):
                    result = speech.diarize(audio, self.root, number)
                pipeline.from_pretrained.assert_called_once_with(str(self.root.resolve()), token=False)
                instance.assert_called_once_with(str(audio), **({} if number is None else {"num_speakers": 2}))
                annotation.itertracks.assert_called_once_with(yield_label=True)
                self.assertEqual(result, [
                    {"start": 0.1, "end": 0.6, "speaker": "SPEAKER_00"},
                    {"start": 0.7, "end": 1, "speaker": "SPEAKER_01"},
                ])

    def test_diarization_rejects_non_speaker_pipeline(self):
        remote = SimpleNamespace()
        pipeline = SimpleNamespace(from_pretrained=mock.Mock(return_value=remote))
        with mock.patch.dict(sys.modules, self.pyannote_modules(pipeline)), \
                mock.patch.dict(os.environ):
            with self.assertRaisesRegex(speech.SpeechError, "apenas o pipeline local SpeakerDiarization"):
                speech.diarize(self.root / "audio.wav", self.root, None)

    def test_diarization_model_load_and_inference_failures_are_actionable(self):
        for loader in (
            mock.Mock(side_effect=RuntimeError("bad model")),
            mock.Mock(return_value=mock.Mock(side_effect=RuntimeError("bad inference"))),
        ):
            pipeline = SimpleNamespace(from_pretrained=loader)
            with self.subTest(loader=loader), \
                    mock.patch.dict(sys.modules, self.pyannote_modules(pipeline)), \
                    mock.patch.dict(os.environ):
                with self.assertRaisesRegex(speech.SpeechError, "Falha na diarização local"):
                    speech.diarize(self.root / "audio.wav", self.root, None)

    def test_missing_optional_dependencies_are_actionable(self):
        for adapter, modules, message in (
            (speech.transcribe, {"faster_whisper": None}, "Instale faster-whisper"),
            (speech.diarize, {"pyannote": None, "pyannote.audio": None}, "Instale pyannote.audio"),
        ):
            with self.subTest(adapter=adapter.__name__), mock.patch.dict(sys.modules, modules), \
                    mock.patch.dict(os.environ):
                with self.assertRaisesRegex(speech.SpeechError, message):
                    adapter(self.root / "audio.wav", self.root, None)

    def test_optional_import_binary_failures_are_actionable(self):
        original_import = __import__
        for adapter, module_name, message in (
            (speech.transcribe, "faster_whisper", "Instale faster-whisper"),
            (speech.diarize, "pyannote.audio", "Instale pyannote.audio"),
            (speech.diarize, "pyannote.audio.pipelines", "Instale pyannote.audio"),
        ):
            for exception in (ImportError, OSError, RuntimeError):
                def fail_import(name, *args, **kwargs):
                    if name == module_name:
                        raise exception("broken optional binary")
                    return original_import(name, *args, **kwargs)

                with self.subTest(module=module_name, exception=exception.__name__), \
                        mock.patch.dict(sys.modules, self.pyannote_modules(mock.Mock())), \
                        mock.patch.dict(os.environ), \
                        mock.patch("builtins.__import__", side_effect=fail_import):
                    with self.assertRaisesRegex(speech.SpeechError, message) as error:
                        adapter(self.root / "audio.wav", self.root, None)
                    self.assertNotIn("broken optional binary", str(error.exception))


class SpeakerSegmentsTest(WorkspaceTest):
    def test_validation_sorts_without_mutating_manual_input(self):
        turns = [
            {"speaker": "B", "start": 1, "end": 2, "extra": "ignored"},
            {"speaker": "A", "start": 0, "end": 1},
        ]
        original = json.loads(json.dumps(turns))
        self.assertEqual(speech.validate_turns(turns, 2), [
            {"speaker": "A", "start": 0, "end": 1},
            {"speaker": "B", "start": 1, "end": 2},
        ])
        self.assertEqual(turns, original)
        self.assertEqual(speech.validate_turns([], 2), [])

    def test_invalid_manual_diarization(self):
        valid = {"speaker": "A", "start": 0, "end": 1}
        invalid = [
            None, {}, "[]", [None], [{}], [valid] * 10001,
            *([dict(valid, speaker=value)] for value in (
                None, 1, "", " ", "a" * 81, "A\nB", "A\x00B",
            )),
            *([dict(valid, **{field: value})] for field in ("start", "end")
              for value in (True, False, None, "1", float("nan"), float("inf"), -float("inf"))),
            [dict(valid, start=-0.1)], [dict(valid, end=2.1)],
            [dict(valid, end=0)], [dict(valid, start=1.5)],
            [dict(valid, speaker=str(index)) for index in range(101)],
        ]
        for index, turns in enumerate(invalid):
            with self.subTest(case=index), self.assertRaises(speech.SpeechError):
                speech.validate_turns(turns, 2)

    def test_automatic_turns_clip_partial_overlap_at_both_audio_boundaries(self):
        turns = [
            {"speaker": "B", "start": 1.5, "end": 2.05},
            {"speaker": "A", "start": -0.05, "end": 0.5},
        ]
        original = json.loads(json.dumps(turns))
        self.assertEqual(speech.validate_turns(turns, 2, clip_to_audio=True), [
            {"speaker": "A", "start": 0, "end": 0.5},
            {"speaker": "B", "start": 1.5, "end": 2},
        ])
        self.assertEqual(turns, original)
        self.assertEqual(speech.validate_turns([
            {"speaker": "A", "start": -1, "end": 3},
        ], 2, clip_to_audio=True), [{"speaker": "A", "start": 0, "end": 2}])

    def test_automatic_turns_entirely_outside_recording_are_discarded(self):
        turns = [
            {"speaker": "before", "start": -2, "end": -1},
            {"speaker": "touches-start", "start": -1, "end": 0},
            {"speaker": "touches-end", "start": 2, "end": 3},
            {"speaker": "after", "start": 3, "end": 4},
        ]
        self.assertEqual(speech.validate_turns(turns, 2, clip_to_audio=True), [])
        inside = {"speaker": "inside", "start": 0.5, "end": 1.5}
        self.assertEqual(speech.validate_turns([*turns, inside], 2, clip_to_audio=True), [inside])

    def test_automatic_turns_reject_reversed_empty_and_nonfinite_times_before_clipping(self):
        invalid = [
            (1, 0), (1, 1), (-1, -2), (4, 3),
            (float("nan"), 1), (0, float("nan")),
            (-float("inf"), 1), (0, float("inf")),
            (float("inf"), 1), (0, -float("inf")),
        ]
        for start, end in invalid:
            with self.subTest(start=start, end=end), self.assertRaises(speech.SpeechError):
                speech.validate_turns([
                    {"speaker": "A", "start": start, "end": end},
                ], 2, clip_to_audio=True)

    def test_manual_turns_still_reject_out_of_bounds_instead_of_clipping(self):
        for start, end in ((-0.05, 0.5), (1.5, 2.05), (-1, 3), (-2, -1), (3, 4)):
            for options in ({}, {"clip_to_audio": False}):
                with self.subTest(start=start, end=end, options=options), \
                        self.assertRaisesRegex(speech.SpeechError, "fora do áudio"):
                    speech.validate_turns([
                        {"speaker": "A", "start": start, "end": end},
                    ], 2, **options)

    def test_same_voice_overlaps_duplicates_and_adjacent_ranges_are_merged(self):
        intervals, overlap = speech.clean_intervals([
            {"speaker": "A", "start": 0, "end": 2},
            {"speaker": "A", "start": 1, "end": 3},
            {"speaker": "A", "start": 1, "end": 3},
            {"speaker": "A", "start": 3, "end": 4},
        ], 10)
        self.assertEqual(dict(intervals), {"A": [[0, 40]]})
        self.assertEqual(overlap, 0)

    def test_different_voice_overlap_is_excluded_and_counted_once(self):
        intervals, overlap = speech.clean_intervals([
            {"speaker": "A", "start": 0, "end": 4},
            {"speaker": "B", "start": 1, "end": 3},
            {"speaker": "C", "start": 1.5, "end": 2.5},
            {"speaker": "B", "start": 4, "end": 5},
        ], 10)
        self.assertEqual(dict(intervals), {"A": [[0, 10], [30, 40]], "B": [[40, 50]]})
        self.assertEqual(overlap, 20)

    def test_fractional_sample_boundaries_round_inward(self):
        intervals, overlap = speech.clean_intervals([
            {"speaker": "A", "start": 0.11, "end": 0.39},
            {"speaker": "A", "start": 0.41, "end": 0.49},
        ], 10)
        self.assertEqual(dict(intervals), {"A": [[2, 3]]})
        self.assertEqual(overlap, 0)

    def test_chronological_clips_and_join_preserve_exact_pcm(self):
        audio = self.root / "source.wav"
        original = write_pcm(audio, range(60))
        turns = speech.validate_turns([
            {"speaker": "A", "start": 4, "end": 5},
            {"speaker": "A", "start": 0, "end": 3},
            {"speaker": "B", "start": 1, "end": 2},
            {"speaker": "B", "start": 5, "end": 6},
        ], 6)
        speakers, overlap = speech.write_speakers(audio, self.root, turns)
        self.assertEqual(overlap, 1)
        self.assertEqual([item["label"] for item in speakers], ["A", "B"])
        for item, ranges in zip(speakers, ([(0, 10), (20, 30), (40, 50)], [(50, 60)])):
            with self.subTest(speaker=item["label"]):
                self.assertEqual([(c["start"], c["end"]) for c in item["clips"]],
                                 [(start / 10, end / 10) for start, end in ranges])
                self.assertEqual(item["duration"], sum(end - start for start, end in ranges) / 10)
                expected = b"".join(original[start * 2:end * 2] for start, end in ranges)
                params, joined = read_pcm(self.root / item["file"])
                self.assertEqual((params.nchannels, params.sampwidth, params.framerate), (1, 2, 10))
                self.assertEqual(joined, expected)
                for clip, (start, end) in zip(item["clips"], ranges):
                    self.assertEqual(read_pcm(self.root / clip["file"])[1],
                                     original[start * 2:end * 2])
        self.assertEqual(read_pcm(audio)[1], original)

    def test_large_clip_is_copied_across_multiple_read_chunks(self):
        audio = self.root / "source.wav"
        original = write_pcm(audio, range(250))
        speakers, _ = speech.write_speakers(audio, self.root, [
            {"speaker": "A", "start": 0, "end": 25},
        ])
        self.assertEqual(read_pcm(self.root / speakers[0]["file"])[1], original)
        self.assertEqual(read_pcm(self.root / speakers[0]["clips"][0]["file"])[1], original)

    def test_unsafe_speaker_labels_never_become_paths(self):
        labels = ("../../escape", "/absolute/path", r"C:\outside\voice", "voz/../outra", "Voz ç")
        audio = self.root / "source.wav"
        write_pcm(audio, range(50))
        turns = speech.validate_turns([
            {"speaker": label, "start": index, "end": index + 1}
            for index, label in enumerate(labels)
        ], 5)
        speakers, _ = speech.write_speakers(audio, self.root, turns)
        self.assertEqual([item["label"] for item in speakers], list(labels))
        for index, item in enumerate(speakers, 1):
            folder = f"speakers/speaker_{index:03d}"
            self.assertEqual(item["id"], f"speaker_{index:03d}")
            self.assertEqual(item["file"], f"{folder}/combined.wav")
            self.assertEqual(item["clips"][0]["file"], f"{folder}/clip_0001.wav")
        self.assertEqual({p.name for p in (self.root / "speakers").iterdir()},
                         {f"speaker_{index:03d}" for index in range(1, 6)})
        self.assertEqual({p.name for p in self.root.iterdir()}, {"source.wav", "speakers"})

    def test_truncated_pcm_raises_instead_of_silently_exporting_short_clip(self):
        audio = self.root / "source.wav"
        write_pcm(audio, range(10))
        audio.write_bytes(audio.read_bytes()[:-4])
        with self.assertRaisesRegex(speech.SpeechError, "Áudio truncado"):
            speech.write_speakers(audio, self.root, [{"speaker": "A", "start": 0, "end": 1}])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
class SpeechIntegrationTest(WorkspaceTest):
    @classmethod
    def setUpClass(cls):
        workspace = tempfile.TemporaryDirectory(prefix=".speech-media-", dir=Path.cwd())
        cls.addClassCleanup(workspace.cleanup)
        cls.media = Path(workspace.name)
        cls.input_audio = cls.media / "synthetic stereo.wav"
        write_pcm(cls.input_audio, [value for i in range(48000)
                                   for value in ((i % 1000) - 500,) * 2],
                  rate=48000, channels=2)
        cls.video = cls.media / "synthetic video with audio.mkv"
        cls.silent_video = cls.media / "silent.mkv"
        subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
            "testsrc2=size=64x48:rate=10:duration=1", "-i", str(cls.input_audio),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-t", "1",
            "-c:v", "mpeg4", "-c:a", "pcm_s16le", str(cls.video),
        ], check=True, capture_output=True)
        subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-i", str(cls.video),
            "-map", "0:v", "-c", "copy", "-an", str(cls.silent_video),
        ], check=True, capture_output=True)

    def generate(self, **kwargs):
        return generator.generate(self.video, self.root / "out", width=64, **kwargs)

    def test_real_extraction_first_track_and_gifs_preserve_original(self):
        original = self.video.read_bytes()
        catalog = self.generate(category="correct", speech=speech.SpeechOptions(extract_audio=True))
        output = self.root / "out"
        params, pcm = read_pcm(output / "audio.wav")
        self.assertEqual((params.nchannels, params.sampwidth, params.framerate), (1, 2, 44100))
        self.assertEqual(params.nframes, 44100)
        self.assertNotEqual(pcm, bytes(len(pcm)))
        self.assertEqual(catalog["audio"], {
            "file": "audio.wav", "duration": 1, "sampleRate": 44100, "channels": 1, "sampleWidth": 2,
        })
        self.assertTrue((output / "full.gif").is_file())
        self.assertTrue((output / catalog["clips"][0]["file"]).is_file())
        self.assertEqual(json.loads((output / "catalog.json").read_text()), catalog)
        self.assertEqual(self.video.read_bytes(), original)

    def test_existing_gif_only_contract_does_not_extract_or_load_models(self):
        with mock.patch.object(speech, "prepare", side_effect=AssertionError("speech is opt-in")):
            catalog = generator.generate(self.silent_video, self.root / "out",
                                         category="incorrect", width=64)
        self.assertEqual(set(catalog), {"schemaVersion", "fullGif", "sourceDuration",
                                       "fps", "width", "clips"})
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertEqual(catalog["fullGif"], "full.gif")
        self.assertFalse((self.root / "out" / "audio.wav").exists())

    def test_audio_only_cli_accepts_audio_source_and_creates_no_gifs(self):
        output = self.root / "out"
        with contextlib.redirect_stdout(io.StringIO()) as stdout, \
                mock.patch.object(generator, "video_duration",
                                  side_effect=AssertionError("audio-only must not probe video")):
            code = generator.main([
                str(self.input_audio), "--output", str(output), "--audio-only", "--extract-audio",
            ])
        self.assertEqual(code, 0)
        self.assertIn("Arquivos preparados", stdout.getvalue())
        self.assertEqual({p.name for p in output.iterdir()}, {"audio.wav", "catalog.json"})
        self.assertEqual(set(json.loads((output / "catalog.json").read_text())), {"schemaVersion", "audio"})

    def test_no_audio_track_rolls_back_entire_output(self):
        before = set(self.root.iterdir())
        for audio_only in (False, True):
            with self.subTest(audio_only=audio_only), self.assertRaises(generator.GenerationError):
                generator.generate(self.silent_video, self.root / "out",
                                   audio_only=audio_only, category=None if audio_only else "correct",
                                   speech=speech.SpeechOptions(extract_audio=True))
            self.assertEqual(set(self.root.iterdir()), before)

    def test_mocked_transcription_and_diarization_write_catalog_and_artifacts(self):
        transcript = {"language": "pt", "segments": [
            {"start": 0, "end": 0.5, "text": "Olá mundo."},
            {"start": 0.5, "end": 1, "text": "Outra frase."},
        ]}
        with mock.patch.object(speech, "transcribe", return_value=transcript) as transcribe, \
                mock.patch.object(speech, "diarize", return_value=[
                    {"speaker": "A", "start": 0.5, "end": 1},
                    {"speaker": "A", "start": 0, "end": 0.5},
                ]) as diarize:
            catalog = self.generate(audio_only=True, speech=speech.SpeechOptions(
                transcribe_model=self.root, diarization_model=self.root, language="pt",
                num_speakers=1, voices_authorized=True,
            ))
        output = self.root / "out"
        transcribe.assert_called_once()
        diarize.assert_called_once()
        self.assertEqual(transcribe.call_args.args[1:], (self.root, "pt"))
        self.assertEqual(diarize.call_args.args[1:], (self.root, 1))
        self.assertEqual(json.loads((output / "transcript.json").read_text()), transcript)
        self.assertEqual((output / "transcript.txt").read_text(), "Olá mundo.\nOutra frase.\n")
        self.assertEqual(catalog["audio"]["transcript"], {"text": "transcript.txt", "json": "transcript.json"})
        self.assertEqual(catalog["audio"]["speakerMethod"], "pyannote-community-1")
        self.assertTrue(catalog["audio"]["voicesAuthorized"])
        self.assertEqual(read_pcm(output / catalog["audio"]["speakers"][0]["file"])[1],
                         read_pcm(output / "audio.wav")[1])
        self.assertEqual(json.loads((output / "speaker_segments.json").read_text())[0]["start"], 0)

    def test_automatic_diarization_eof_padding_exports_clipped_exact_pcm(self):
        predictions = [
            {"speaker": "B", "start": 0.5, "end": 1.05},
            {"speaker": "A", "start": -0.05, "end": 0.5},
            {"speaker": "padding", "start": 1.1, "end": 1.2},
        ]
        with mock.patch.object(speech, "diarize", return_value=predictions) as diarize:
            catalog = self.generate(audio_only=True, speech=speech.SpeechOptions(
                diarization_model=self.root, voices_authorized=True,
            ))
        diarize.assert_called_once()
        output = self.root / "out"
        self.assertEqual(json.loads((output / "speaker_segments.json").read_text()), [
            {"speaker": "A", "start": 0, "end": 0.5},
            {"speaker": "B", "start": 0.5, "end": 1},
        ])
        audio = catalog["audio"]
        self.assertEqual(audio["speakerMethod"], "pyannote-community-1")
        self.assertEqual(audio["excludedOverlapDuration"], 0)
        self.assertEqual([item["label"] for item in audio["speakers"]], ["A", "B"])
        source_pcm = read_pcm(output / "audio.wav")[1]
        for index, item in enumerate(audio["speakers"]):
            with self.subTest(speaker=item["label"]):
                self.assertEqual(item["duration"], 0.5)
                self.assertEqual(len(item["clips"]), 1)
                clip = item["clips"][0]
                self.assertEqual((clip["start"], clip["end"]), (index * 0.5, (index + 1) * 0.5))
                expected = source_pcm[index * 44100:(index + 1) * 44100]
                self.assertEqual(read_pcm(output / item["file"])[1], expected)
                self.assertEqual(read_pcm(output / clip["file"])[1], expected)
        self.assertEqual(json.loads((output / "catalog.json").read_text()), catalog)

    def test_empty_and_fully_overlapping_turns_emit_no_clean_speech_warning(self):
        for turns in ([], [
            {"speaker": "A", "start": 0, "end": 1},
            {"speaker": "B", "start": 0, "end": 1},
        ], [{"speaker": "A", "start": 0.000001, "end": 0.000002}]):
            with self.subTest(turns=turns):
                segments = self.root / "segments.json"
                segments.write_text(json.dumps(turns), encoding="utf-8")
                output = self.root / f"out-{len(turns)}"
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
                    code = generator.main([
                        str(self.video), "--output", str(output), "--audio-only",
                        "--speaker-segments", str(segments), "--voices-authorized",
                    ])
                self.assertEqual(code, 0)
                audio = json.loads((output / "catalog.json").read_text())["audio"]
                self.assertEqual(audio["speakerMethod"], "manual")
                self.assertIn("Nenhuma fala isolada", stderr.getvalue())
                self.assertIn("não isola vozes simultâneas", stderr.getvalue())
                self.assertEqual(len(audio["warnings"]), 2)
                self.assertFalse((output / "speakers").exists())
                self.assertTrue(all(item["file"] is None and not item["clips"]
                                    and item["duration"] == 0 for item in audio["speakers"]))
                self.assertEqual(audio["excludedOverlapDuration"], 1 if len(turns) == 2 else 0)

    def test_empty_extracted_audio_rolls_back(self):
        def empty_audio(command):
            write_pcm(Path(command[-1]), [], rate=44100)

        with mock.patch.object(generator, "run_media", side_effect=empty_audio):
            with self.assertRaisesRegex(speech.SpeechError, "faixa de áudio está vazia"):
                self.generate(audio_only=True, speech=speech.SpeechOptions(extract_audio=True))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_model_failures_roll_back_extracted_audio_and_partial_transcript(self):
        options = speech.SpeechOptions(transcribe_model=self.root, diarization_model=self.root,
                                       voices_authorized=True)
        for failed_stage in ("transcribe", "diarize"):
            with self.subTest(stage=failed_stage), contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(
                    speech, "transcribe", return_value={"language": "pt", "segments": []},
                ))
                stack.enter_context(mock.patch.object(
                    speech, failed_stage, side_effect=speech.SpeechError("local model failed"),
                ))
                with self.assertRaisesRegex(speech.SpeechError, "local model failed"):
                    self.generate(audio_only=True, speech=options)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_manual_json_and_turns_roll_back(self):
        segments = self.root / "segments.json"
        for content in ("{invalid", "null", '[{"speaker":"A","start":0,"end":2}]'):
            with self.subTest(content=content):
                segments.write_text(content, encoding="utf-8")
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    code = generator.main([
                        str(self.video), "--output", str(self.root / "out"), "--audio-only",
                        "--speaker-segments", str(segments), "--voices-authorized",
                    ])
                self.assertEqual(code, 1)
                self.assertIn("Erro:", stderr.getvalue())
                self.assertEqual(list(self.root.iterdir()), [segments])

    def test_speaker_export_failure_rolls_back_already_written_artifacts(self):
        segments = self.root / "segments.json"
        segments.write_text('[{"speaker":"A","start":0,"end":1}]', encoding="utf-8")

        def fail_export(audio, destination, turns):
            self.assertTrue(audio.is_file())
            self.assertTrue((destination / "speaker_segments.json").is_file())
            (destination / "partial.wav").write_bytes(b"partial")
            raise OSError("disk full")

        with mock.patch.object(speech, "write_speakers", side_effect=fail_export):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.generate(audio_only=True, speech=speech.SpeechOptions(
                    speaker_segments=segments, voices_authorized=True,
                ))
        self.assertEqual(list(self.root.iterdir()), [segments])

    def test_gif_failure_rolls_back_successfully_extracted_audio(self):
        real_run_media = generator.run_media
        extracted = []

        def fail_gif(command):
            if command[-1].endswith(".gif"):
                self.assertTrue((Path(command[-1]).parent / "audio.wav").is_file())
                raise generator.GenerationError("GIF conversion failed")
            result = real_run_media(command)
            if command[-1].endswith("audio.wav"):
                extracted.append(True)
            return result

        with mock.patch.object(generator, "run_media", side_effect=fail_gif):
            with self.assertRaisesRegex(generator.GenerationError, "GIF conversion failed"):
                self.generate(category="correct", speech=speech.SpeechOptions(extract_audio=True))
        self.assertEqual(extracted, [True])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_output_is_not_overwritten_by_speech_preparation(self):
        output = self.root / "out"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with mock.patch.object(speech, "prepare") as prepare:
            with self.assertRaisesRegex(generator.GenerationError, "já existe"):
                self.generate(audio_only=True, speech=speech.SpeechOptions(extract_audio=True))
        prepare.assert_not_called()
        self.assertEqual(sentinel.read_text(), "keep")


class SpeechCliTest(WorkspaceTest):
    def test_malformed_cli_combinations_fail_before_conversion(self):
        video = self.root / "video.mkv"
        video.touch()
        invalid = [
            (["--audio-only"], 1),
            (["--audio-only", "--extract-audio", "--category", "correct"], 2),
            (["--audio-only", "--extract-audio", "--segments", "cuts.json"], 2),
            (["--audio-only", "--extract-audio", "--segment-duration", "1"], 2),
            (["--category", "correct", "--language", "pt"], 1),
            (["--audio-only", "--extract-audio", "--num-speakers", "2"], 1),
            (["--audio-only", "--diarization-model", str(self.root)], 1),
            (["--audio-only", "--speaker-segments", "speakers.json"], 1),
            (["--audio-only", "--transcribe-model", str(self.root / "missing")], 1),
            (["--audio-only", "--diarization-model", str(self.root),
              "--speaker-segments", "speakers.json", "--voices-authorized"], 2),
            (["--audio-only", "--diarization-model", str(self.root),
              "--voices-authorized", "--num-speakers", "101"], 1),
            (["--extract-audio"], 2),
        ]
        for arguments, expected in invalid:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()) as stderr, \
                    mock.patch.object(generator, "run_media") as run_media:
                argv = [str(video), "--output", str(self.root / "out"), *arguments]
                if expected == 2:
                    with self.assertRaises(SystemExit) as error:
                        generator.main(argv)
                    self.assertEqual(error.exception.code, 2)
                else:
                    self.assertEqual(generator.main(argv), expected)
                self.assertTrue(stderr.getvalue())
                run_media.assert_not_called()
                self.assertFalse((self.root / "out").exists())

    def test_audio_only_api_rejects_gif_cuts_or_missing_audio_operation(self):
        video = self.root / "video.mkv"
        video.touch()
        for kwargs in ({}, {"category": "correct"}, {"segments": []}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(generator.GenerationError, "--audio-only"):
                generator.generate(video, self.root / "out", audio_only=True,
                                   speech=speech.SpeechOptions(extract_audio=bool(kwargs)), **kwargs)
        self.assertFalse((self.root / "out").exists())


if __name__ == "__main__":
    unittest.main()
