import builtins
import copy
import hashlib
import io
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest import mock
import uuid

from tool import generate_meme_english_audio as generator


ROOT = Path(__file__).resolve().parent.parent
VOICE = "VP5ZIVzkURII30A4DT2x"
OTHER_VOICE = "a" * 20
FAKE_KEY = "TEST_ONLY_NOT_A_REAL_CREDENTIAL"
MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"mocked audio; decoding is separately tested"


class _Response:
    def __init__(self, data=MP3, status=200, headers=None):
        self.status = status
        self.headers = (
            [("Content-Type", "audio/mpeg"), ("Content-Length", str(len(data)))]
            if headers is None else headers
        )
        self.stream = io.BytesIO(data)

    def getheaders(self):
        return self.headers

    def read(self, size):
        return self.stream.read(size)


class EnglishAudioGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / "artifacts" / "meme-course-work" / f".english-test-{uuid.uuid4().hex}"
        self.work.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.work)
        self.source = self.work / "course.json"
        self.output = self.work / "english"
        self.original_audio = self.work / "identity.mp3"
        self.original_audio.write_bytes(b"original Portuguese is never changed")
        self.course = {
            "id": "meme_english_test",
            "title": "English in context",
            "sourceLanguage": "pt-BR", "targetLanguage": "en",
            "level": "Thematic practice", "coverage": "No certification.",
            "contentVersion": 1, "kind": "memes", "editorialStatus": "draft",
            "scenes": [
                self.scene("identity", "  Who are you?  ", "Who am I?"),
                self.scene("duplicate", "Who are you?", " Who am I? "),
                self.scene("reply", "I'm right here.", "Let's go!"),
            ],
            "units": [{
                "id": "meme_english_test_u1",
                "title": "Questions", "description": "Practise questions.",
                "lessons": [{
                    "id": "meme_english_test_l1", "title": "A scene",
                    "description": "Study meaning.", "studyNotes": "Notice the question.",
                    "exercises": [{
                        "id": f"meme_english_test_e{index}",
                        "sceneId": scene, "type": "choice",
                        "prompt": "Which purpose fits this scene?",
                        "answer": "A conversation.", "options": ["A conversation.", "A recipe."],
                        "explanation": "These speakers are having a conversation.",
                    } for index, scene in enumerate(("identity", "duplicate", "reply"))],
                }],
            }],
        }
        self.write_source()
        self.logs = []
        self.requests = []

    @staticmethod
    def scene(scene_id, first, second):
        return {
            "id": scene_id, "title": "A scene", "format": "webp",
            "durationMs": 2000, "adaptationNotes": "Preserve the speaker's tone.",
            "cues": [
                {"startMs": 0, "endMs": 1000, "pt": "Quem é você?", "en": first},
                {"startMs": 1000, "endMs": 2000, "pt": "Vamos lá!", "en": second},
            ],
        }

    def write_source(self):
        self.source.write_text(json.dumps(self.course, ensure_ascii=False), encoding="utf-8")

    def synthesize(self, request):
        self.requests.append(request)
        return MP3 + request.text.encode("utf-8")

    def run_cli(self, *extra, voice=VOICE, **kwargs):
        args = [str(self.source), "--output", str(self.output)]
        if voice is not None:
            args += ["--voice-id", voice]
        args += list(extra)
        options = {
            "environment": {"ELEVENLABS_API_KEY": FAKE_KEY},
            "interactive": False, "synthesize": self.synthesize,
            "probe": lambda _: 1234, "log": self.logs.append,
        }
        options.update(kwargs)
        return generator.run_local(args, **options)

    def generate(self, *extra, **kwargs):
        return self.run_cli("--generate", "--yes", "--allow-draft", *extra, **kwargs)

    def read(self, filename):
        return json.loads((self.output / filename).read_text(encoding="utf-8"))

    def write_english_request(self, request):
        self.source = self.work / "english-request.json"
        self.source.write_text(json.dumps(request), encoding="utf-8")

    def test_default_cli_delegates_without_reading_credentials_or_prompting_for_a_key(self):
        for mode in (["--dry-run"], ["--generate", "--yes", "--allow-draft"]):
            with self.subTest(mode=mode):
                arguments = [
                    str(self.source), "--output", str(self.output),
                    "--voice-id", VOICE, *mode,
                ]
                runner = mock.Mock()
                runner.main.return_value = 23
                environment = mock.Mock()
                environment.get.side_effect = AssertionError("default route read credentials")
                with (
                    mock.patch.object(importlib, "import_module", return_value=runner) as importer,
                    mock.patch.object(generator, "run_local", side_effect=AssertionError("default invoked local engine")) as local,
                    mock.patch.object(generator.os, "environ", environment),
                    mock.patch.object(builtins, "input", side_effect=AssertionError("default prompted")) as prompt,
                    mock.patch.object(generator.getpass, "getpass", side_effect=AssertionError("default requested a key")) as secret,
                ):
                    self.assertEqual(generator.main(arguments), 23)
                importer.assert_called_once_with("tool.run_meme_english_audio")
                runner.main.assert_called_once_with(arguments)
                local.assert_not_called()
                environment.get.assert_not_called()
                prompt.assert_not_called()
                secret.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_unavailable_default_wrapper_never_falls_back_to_a_local_key_prompt(self):
        with (
            mock.patch.object(importlib, "import_module", side_effect=ModuleNotFoundError(FAKE_KEY)),
            mock.patch.object(generator, "run_local") as local,
            mock.patch.object(builtins, "input") as prompt,
            mock.patch.object(generator.getpass, "getpass") as secret,
            mock.patch.object(builtins, "print") as log,
        ):
            self.assertEqual(generator.main(["--dry-run"]), 1)
        local.assert_not_called()
        prompt.assert_not_called()
        secret.assert_not_called()
        self.assertNotIn(FAKE_KEY, str(log.call_args_list))
        self.assertFalse(self.output.exists())

    def test_explicit_local_dispatch_does_not_import_or_invoke_the_wrapper(self):
        arguments = ["--local", str(self.source), "--output", str(self.output), "--dry-run"]
        with (
            mock.patch.object(importlib, "import_module", side_effect=AssertionError("local imported remote runner")) as importer,
            mock.patch.object(generator, "run_local", return_value=19) as local,
        ):
            self.assertEqual(generator.main(arguments), 19)
        importer.assert_not_called()
        local.assert_called_once_with(arguments[1:])
        self.assertEqual(arguments[0], "--local")

    def test_wrapper_configuration_constants_match_the_fixed_engine_defaults(self):
        self.assertEqual(generator.CATALOG_FILENAME, "english-audio-catalog.json")
        self.assertEqual(generator.CATALOG_FILENAME, generator.CATALOG_FILE)
        self.assertEqual(generator.DEFAULT_MODEL_ID, "eleven_multilingual_v2")
        self.assertEqual(generator.DEFAULT_MODEL_ID, generator.MODEL_ID)
        self.assertEqual(generator.DEFAULT_OUTPUT_FORMAT, "mp3_44100_64")
        self.assertEqual(generator.DEFAULT_OUTPUT_FORMAT, generator.OUTPUT_FORMAT)
        self.assertEqual(generator.DEFAULT_VOICE_SETTINGS, {
            "stability": 0.5, "similarity_boost": 0.75, "style": 0.0,
            "use_speaker_boost": True, "speed": 1.0,
        })
        self.assertEqual(generator.DEFAULT_VOICE_SETTINGS, generator.VOICE_SETTINGS)

    def test_export_returns_only_exact_english_data_without_writes_credentials_or_network(self):
        self.course["editorialStatus"] = "reviewed"
        self.course["scenes"][0]["adaptationNotes"] = "[Private editorial uncertainty — never upload this note.]"
        self.course["scenes"][0]["cues"][0]["en"] = "  We’re ready.\nLet’s go!  "
        self.write_source()
        before = {path.name: path.read_bytes() for path in self.work.iterdir()}
        environment = mock.Mock()
        environment.get.side_effect = AssertionError("export read a credential")
        with (
            mock.patch.object(generator.os, "environ", environment),
            mock.patch.object(generator, "synthesize_with_elevenlabs", side_effect=AssertionError("network")) as synthesize,
            mock.patch.object(generator, "require_ffprobe", side_effect=AssertionError("decoder")) as decoder,
            mock.patch.object(generator.getpass, "getpass", side_effect=AssertionError("secret prompt")) as secret,
        ):
            request = generator.export_english_request(self.source)
        self.assertEqual(set(request), {
            "schemaVersion", "kind", "courseId", "sourceCourseSha256",
            "editorialStatus", "language", "scenes",
        })
        self.assertEqual(request["schemaVersion"], 1)
        self.assertEqual(request["kind"], "meme_english_tts_request")
        self.assertEqual(request["courseId"], self.course["id"])
        self.assertEqual(request["sourceCourseSha256"], hashlib.sha256(before["course.json"]).hexdigest())
        self.assertEqual(request["editorialStatus"], "draft")
        self.assertEqual(request["language"], "en")
        self.assertEqual(len(request["scenes"]), len(self.course["scenes"]))
        for source_scene, scene in zip(self.course["scenes"], request["scenes"]):
            text = " ".join(cue["en"].strip() for cue in source_scene["cues"])
            self.assertEqual(scene, {
                "id": source_scene["id"], "text": text,
                "textSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            })
        exported = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("Private editorial", exported)
        self.assertNotIn("Quem é você?", exported)
        self.assertNotIn("Vamos lá!", exported)
        self.assertNotIn("adaptationNotes", exported)
        environment.get.assert_not_called()
        synthesize.assert_not_called()
        decoder.assert_not_called()
        secret.assert_not_called()
        self.assertEqual({path.name: path.read_bytes() for path in self.work.iterdir()}, before)

    def test_export_rejects_stale_english_metadata_without_emitting_a_request(self):
        self.course["scenes"][0]["englishAudio"] = {
            "durationMs": 1234, "textSha256": "0" * 64,
        }
        self.write_source()
        before = self.source.read_bytes()
        with self.assertRaises(generator.GenerationError):
            generator.export_english_request(self.source)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_minimal_request_generates_the_same_catalog_without_a_runtime_course_stub(self):
        request = generator.export_english_request(self.source)
        self.assertEqual(self.generate(), 0, self.logs)
        expected_catalog = self.read(generator.CATALOG_FILE)
        self.output = self.work / "english-only"
        self.write_english_request(request)
        source_bytes = self.source.read_bytes()
        self.requests.clear()
        self.logs.clear()
        with mock.patch.object(
            generator.compiler, "validate_course", side_effect=AssertionError("minimal input fabricated a course"),
        ):
            self.assertEqual(self.generate(), 0, self.logs)
        self.assertEqual([item.text for item in self.requests], [
            "Who are you? Who am I?", "I'm right here. Let's go!",
        ])
        self.assertEqual(self.read(generator.CATALOG_FILE), expected_catalog)
        self.assertEqual(
            {path.name for path in self.output.iterdir()},
            {generator.STATE_FILE, generator.CATALOG_FILE}
            | {f"{scene['id']}.en.mp3" for scene in request["scenes"]},
        )
        self.assertEqual(self.read(generator.STATE_FILE)["sourceCourseSha256"], request["sourceCourseSha256"])
        self.assertNotEqual(request["sourceCourseSha256"], hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertNotIn(generator.COURSE_FILE, "\n".join(self.logs))
        for path in self.output.iterdir():
            self.assertNotIn("Quem é você?".encode(), path.read_bytes())
            self.assertNotIn("Vamos lá!".encode(), path.read_bytes())
        environment = mock.Mock()
        environment.get.side_effect = AssertionError("completed minimal resume read credentials")
        self.assertEqual(self.generate("--resume", environment=environment), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        environment.get.assert_not_called()

    def test_minimal_request_dry_run_needs_no_portuguese_assets_decoder_or_credentials(self):
        request = generator.export_english_request(self.source)
        original = self.source
        self.write_english_request(request)
        original.unlink()
        self.original_audio.unlink()
        environment = mock.Mock()
        environment.get.side_effect = AssertionError("minimal dry-run read credentials")
        with mock.patch.object(
            generator.compiler, "validate_course", side_effect=AssertionError("read a runtime course"),
        ):
            self.assertEqual(self.run_cli(
                "--dry-run", environment=environment,
                synthesize=mock.Mock(side_effect=AssertionError("network")),
                probe=mock.Mock(side_effect=AssertionError("decoder")),
            ), 0, self.logs)
        result = subprocess.run(
            [
                sys.executable, str(ROOT / "tool" / "generate_meme_english_audio.py"),
                "--local",
                str(self.source), "--voice-id", VOICE,
                "--output", str(self.output), "--dry-run",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Scenes: 3; unique English texts: 2", result.stdout)
        self.assertIn("characters: 69 (47 unique)", result.stdout)
        environment.get.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_minimal_request_rejects_unknown_fields_unsafe_ids_bounds_and_stale_hashes(self):
        valid = generator.export_english_request(self.source)
        changes = [
            lambda value: value.update(schemaVersion=True),
            lambda value: value.update(schemaVersion=2),
            lambda value: value.update(language="pt-BR"),
            lambda value: value.update(editorialStatus="reviewed"),
            lambda value: value.update(kind="untrusted"),
            lambda value: value.update(courseId="../escape"),
            lambda value: value.update(courseId="en-a1"),
            lambda value: value.update(sourceCourseSha256="not a hash"),
            lambda value: value.update(sourceCourseSha256=True),
            lambda value: value.update(pt="Do not accept a Portuguese transcript"),
            lambda value: value.update(voiceId=VOICE),
            lambda value: value.pop("sourceCourseSha256"),
            lambda value: value.update(scenes=[]),
            lambda value: value.update(scenes=value["scenes"] * 34),
            lambda value: value["scenes"][0].update(id="../escape"),
            lambda value: value["scenes"][0].update(id="con"),
            lambda value: value["scenes"][0].update(id=value["scenes"][1]["id"]),
            lambda value: value["scenes"][0].update(pt="Unexpected source text"),
            lambda value: value["scenes"][0].update(textSha256="0" * 64),
            lambda value: value["scenes"][0].update(textSha256=True),
            lambda value: value["scenes"][0].update(text=""),
            lambda value: value["scenes"][0].update(text=False),
            lambda value: value["scenes"][0].update(text="x" * 10001),
            lambda value: value["scenes"][0].update(text="\u0001bad"),
            lambda value: value["scenes"][0].update(text="\ud800"),
        ]
        environment = mock.Mock()
        environment.get.side_effect = AssertionError("invalid request read credentials")
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                request = copy.deepcopy(valid)
                change(request)
                self.write_english_request(request)
                self.assertEqual(self.generate(environment=environment), 1)
                self.assertFalse(self.output.exists())
        for text in (" [unclear] ", "[unclear]", "TODO translate", "???", " Hello!"):
            request = copy.deepcopy(valid)
            request["scenes"][0].update(text=text, textSha256=hashlib.sha256(text.encode()).hexdigest())
            self.write_english_request(request)
            self.assertEqual(self.generate(environment=environment), 1)
            self.assertFalse(self.output.exists())
        self.write_english_request(valid)
        raw = self.source.read_text(encoding="utf-8").replace(
            '"schemaVersion": 1', '"schemaVersion": 1, "schemaVersion": 1', 1,
        )
        self.source.write_text(raw, encoding="utf-8")
        self.assertEqual(self.generate(environment=environment), 1)
        self.assertEqual(self.requests, [])
        environment.get.assert_not_called()

    def test_minimal_request_missing_secret_never_prompts_or_fabricates_audio(self):
        self.write_english_request(generator.export_english_request(self.source))
        prompt = mock.Mock(side_effect=AssertionError("unexpected prompt"))
        self.assertEqual(self.generate(environment={}, input_fn=prompt, secret_fn=prompt), 1)
        self.assertIn("ELEVENLABS_API_KEY", "\n".join(self.logs))
        self.assertFalse(self.output.exists())
        self.assertEqual(self.requests, [])
        prompt.assert_not_called()

    def test_minimal_request_failures_still_require_explicit_ambiguity_retry(self):
        request = generator.export_english_request(self.source)
        self.write_english_request(request)
        attempted = []
        def fail_second(item):
            attempted.append(item.text)
            if len(attempted) == 2:
                raise TimeoutError(FAKE_KEY)
            return MP3
        self.assertEqual(self.generate(synthesize=fail_second), 1)
        self.assertEqual(len(attempted), 2)
        self.assertEqual(self.read(generator.CATALOG_FILE)["status"], "incomplete")
        self.assertFalse((self.output / generator.COURSE_FILE).exists())
        request["sourceCourseSha256"] = "b" * 64
        self.write_english_request(request)
        self.assertEqual(self.generate("--resume", synthesize=fail_second), 1)
        self.assertEqual(len(attempted), 2)
        self.assertEqual(self.generate("--resume", "--retry-ambiguous"), 0, self.logs)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.read(generator.CATALOG_FILE)["status"], "complete")
        self.assertFalse((self.output / generator.COURSE_FILE).exists())
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))

    def test_dry_run_prompts_for_voice_but_never_reads_key_decodes_calls_or_writes(self):
        key_access = mock.Mock()
        key_access.get.side_effect = AssertionError("dry-run read a credential")
        request = mock.Mock(side_effect=AssertionError("network"))
        probe = mock.Mock(side_effect=AssertionError("decode"))
        prompt = mock.Mock(return_value=VOICE)
        before = {path: path.read_bytes() for path in self.work.iterdir()}
        self.assertEqual(self.run_cli(
            "--dry-run", voice=None, interactive=True, input_fn=prompt,
            environment=key_access, synthesize=request, probe=probe,
        ), 0)
        prompt.assert_called_once_with("ElevenLabs voice ID: ")
        key_access.get.assert_not_called()
        request.assert_not_called()
        probe.assert_not_called()
        self.assertEqual({path: path.read_bytes() for path in self.work.iterdir()}, before)
        self.assertIn("Scenes: 3; unique English texts: 2", "\n".join(self.logs))
        self.assertIn("planned billable POSTs: 2", "\n".join(self.logs))
        self.assertIn("characters: 69 (47 unique)", "\n".join(self.logs))

    def test_standalone_cli_dry_run_is_local_and_creates_no_outputs(self):
        result = subprocess.run(
            [
                sys.executable, str(ROOT / "tool" / "generate_meme_english_audio.py"),
                "--local",
                str(self.source), "--voice-id", VOICE,
                "--output", str(self.output), "--dry-run",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Scenes: 3; unique English texts: 2", result.stdout)
        self.assertIn("no credentials accessed", result.stdout)
        self.assertFalse(self.output.exists())

    def test_complete_batch_has_exact_all_scene_text_hashes_and_strict_catalog(self):
        before = self.source.read_bytes()
        original = self.original_audio.read_bytes()
        self.assertEqual(self.generate(), 0, self.logs)
        self.assertEqual([request.text for request in self.requests], [
            "Who are you? Who am I?", "I'm right here. Let's go!",
        ])
        for request in self.requests:
            self.assertEqual(request.voice_id, VOICE)
            self.assertEqual(request.body, {
                "text": request.text, "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5, "similarity_boost": 0.75, "style": 0.0,
                    "use_speaker_boost": True, "speed": 1.0,
                },
            })
            self.assertNotIn("language_code", request.body)
            self.assertEqual(request.headers["xi-api-key"], FAKE_KEY)
            self.assertEqual(
                request.path,
                f"/v1/text-to-speech/{VOICE}?output_format=mp3_44100_64",
            )
            self.assertNotIn(FAKE_KEY, repr(request))
        catalog = self.read(generator.CATALOG_FILE)
        self.assertEqual(set(catalog), {
            "schemaVersion", "courseId", "language", "voiceId", "modelId",
            "outputFormat", "voiceSettings", "status", "entries",
        })
        self.assertEqual(catalog["status"], "complete")
        self.assertEqual(catalog["language"], "en")
        self.assertEqual(len(catalog["entries"]), 3)
        enriched = self.read(generator.COURSE_FILE)
        for entry, scene, source_scene in zip(catalog["entries"], enriched["scenes"], self.course["scenes"]):
            text = " ".join(cue["en"].strip() for cue in source_scene["cues"])
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self.assertEqual(set(entry), {"sceneId", "textSha256", "file", "sha256", "bytes", "durationMs"})
            self.assertEqual(entry["textSha256"], digest)
            self.assertEqual(entry["file"], f"{scene['id']}.en.mp3")
            raw = (self.output / entry["file"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(entry["bytes"], len(raw))
            self.assertEqual(scene["englishAudio"], {"textSha256": digest, "durationMs": 1234})
        self.assertEqual(
            (self.output / "identity.en.mp3").read_bytes(),
            (self.output / "duplicate.en.mp3").read_bytes(),
        )
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.original_audio.read_bytes(), original)
        self.assertEqual(self.read(generator.STATE_FILE)["status"], "complete")
        self.assertFalse((self.output / generator.LOCK_FILE).exists())
        for path in self.output.iterdir():
            self.assertNotIn(FAKE_KEY.encode(), path.read_bytes())
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))

    def test_requires_explicit_mode_voice_draft_ack_and_billing_confirmation(self):
        for args, kwargs, fragment in [
            ((), {}, "Invalid arguments"),
            (("--dry-run",), {"voice": None}, "--voice-id"),
            (("--generate", "--yes"), {}, "--allow-draft"),
            (("--generate", "--allow-draft"), {}, "--yes"),
            (("--generate", "--allow-draft"), {"interactive": True, "input_fn": lambda _: "no"}, "not confirmed"),
            (("--generate", "--yes", "--allow-draft", "--retry-ambiguous"), {}, "requires --resume"),
        ]:
            with self.subTest(args=args, kwargs=kwargs):
                self.logs.clear()
                self.assertEqual(self.run_cli(*args, **kwargs), 1)
                self.assertIn(fragment, "\n".join(self.logs))
                self.assertFalse(self.output.exists())
        self.assertEqual(self.requests, [])

    def test_interactive_confirmation_and_hidden_key_prompt(self):
        questions = []
        def ask(question):
            questions.append(question)
            return VOICE if "voice ID" in question else "GENERATE"
        key = mock.Mock(return_value=FAKE_KEY)
        self.assertEqual(self.run_cli(
            "--generate", "--allow-draft", "--prompt-api-key",
            voice=None, interactive=True, input_fn=ask, secret_fn=key, environment={},
        ), 0, self.logs)
        self.assertEqual(len(questions), 2)
        key.assert_called_once_with("ElevenLabs API key (hidden): ")
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))

    def test_reviewed_course_does_not_need_draft_override(self):
        self.course["editorialStatus"] = "reviewed"
        self.write_source()
        self.assertEqual(self.run_cli("--generate", "--yes"), 0, self.logs)
        self.assertEqual(self.read(generator.COURSE_FILE)["editorialStatus"], "reviewed")

    def test_missing_credentials_and_decoder_fail_before_any_write_or_request(self):
        self.assertEqual(self.generate(environment={}), 1)
        self.assertFalse(self.output.exists())
        with mock.patch.object(generator.shutil, "which", return_value=None):
            self.assertEqual(self.generate(probe=None), 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.requests, [])

    def test_broken_decoder_and_oversized_enriched_course_fail_before_billing(self):
        with (
            mock.patch.object(generator.shutil, "which", return_value="ffprobe"),
            mock.patch.object(generator.subprocess, "run", side_effect=OSError(FAKE_KEY)),
        ):
            self.assertEqual(self.generate(probe=None), 1)
        with mock.patch.object(generator.compiler, "MAX_JSON_BYTES", self.source.stat().st_size + 1):
            self.assertEqual(self.generate(), 1)
        self.assertEqual(self.requests, [])
        self.assertFalse(self.output.exists())
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))

    def test_resumes_completed_batch_without_credentials_or_rebilling(self):
        self.assertEqual(self.generate(), 0, self.logs)
        hashes = {path.name: path.read_bytes() for path in self.output.iterdir()}
        key_access = mock.Mock()
        key_access.get.side_effect = AssertionError("completed resume read a key")
        self.assertEqual(self.generate("--resume", environment=key_access), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        key_access.get.assert_not_called()
        self.assertEqual({path.name: path.read_bytes() for path in self.output.iterdir()}, hashes)

    def test_source_hash_is_provenance_and_enriched_json_resumes_without_rebilling(self):
        self.assertEqual(self.generate(), 0, self.logs)
        original_state = self.read(generator.STATE_FILE)
        enriched = self.read(generator.COURSE_FILE)
        self.source.write_text(json.dumps(enriched), encoding="utf-8")
        source_bytes = self.source.read_bytes()
        self.assertNotEqual(
            hashlib.sha256(source_bytes).hexdigest(),
            original_state["sourceCourseSha256"],
        )
        key_access = mock.Mock()
        key_access.get.side_effect = AssertionError("enriched resume read a key")
        self.assertEqual(self.run_cli("--generate", "--resume", environment=key_access), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        key_access.get.assert_not_called()
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual(self.read(generator.STATE_FILE), original_state)

    def test_legacy_fingerprint_migrates_safely_when_the_course_is_enriched(self):
        self.assertEqual(self.generate(), 0, self.logs)
        current = self.read(generator.STATE_FILE)
        course, scenes, source_hash = generator.load_course(self.source)
        state = copy.deepcopy(current)
        state["fingerprint"] = generator._fingerprint(
            generator._configuration(course, VOICE), scenes,
            legacy_source_hash=source_hash,
        )
        self.assertNotEqual(state["fingerprint"], current["fingerprint"])
        (self.output / generator.STATE_FILE).write_text(json.dumps(state), encoding="utf-8")
        self.source.write_text(json.dumps(self.read(generator.COURSE_FILE)), encoding="utf-8")
        self.assertEqual(self.generate("--resume", voice=OTHER_VOICE), 1)
        self.assertEqual(self.generate("--resume", environment={}), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.read(generator.STATE_FILE), current)

    def test_using_the_generated_course_as_input_never_rewrites_that_source(self):
        self.assertEqual(self.generate(), 0, self.logs)
        enriched = self.read(generator.COURSE_FILE)
        self.source = self.output / generator.COURSE_FILE
        raw = json.dumps(enriched, separators=(",", ":")).encode("utf-8")
        self.source.write_bytes(raw)
        self.assertEqual(self.generate("--resume", environment={}), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.source.read_bytes(), raw)

    def test_failure_keeps_completed_files_marks_ambiguity_and_never_retries(self):
        calls = []
        def fail_second(request):
            calls.append(request)
            if len(calls) == 2:
                raise TimeoutError(f"provider echoed {FAKE_KEY} and private details")
            return MP3
        self.assertEqual(self.generate(synthesize=fail_second), 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.read(generator.CATALOG_FILE)["status"], "incomplete")
        self.assertEqual(len(self.read(generator.CATALOG_FILE)["entries"]), 2)
        self.assertFalse((self.output / generator.COURSE_FILE).exists())
        states = list(self.read(generator.STATE_FILE)["requests"].values())
        self.assertEqual([record["status"] for record in states], ["complete", "ambiguous"])
        self.assertEqual([record["attempts"] for record in states], [1, 1])
        self.assertTrue((self.output / "identity.en.mp3").is_file())
        self.assertFalse((self.output / generator.LOCK_FILE).exists())
        self.assertEqual(self.generate("--resume", synthesize=fail_second), 1)
        self.assertEqual(len(calls), 2)
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))
        self.assertNotIn("private details", "\n".join(self.logs))
        self.assertEqual(self.generate("--resume", "--retry-ambiguous"), 0, self.logs)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].text, "I'm right here. Let's go!")
        states = list(self.read(generator.STATE_FILE)["requests"].values())
        self.assertEqual([record["attempts"] for record in states], [1, 2])

    def test_request_started_is_persisted_before_the_only_billable_call(self):
        def inspect_and_interrupt(request):
            state = self.read(generator.STATE_FILE)
            digest = hashlib.sha256(request.text.encode()).hexdigest()
            self.assertEqual(state["requests"][digest], {"status": "request-started", "attempts": 1})
            self.assertEqual(self.read(generator.CATALOG_FILE)["status"], "incomplete")
            raise KeyboardInterrupt()
        self.assertEqual(self.generate(synthesize=inspect_and_interrupt), 1)
        self.assertEqual(list(self.read(generator.STATE_FILE)["requests"].values())[0]["status"], "ambiguous")

    def test_uncertain_request_started_after_crash_also_requires_explicit_retry(self):
        self.assertEqual(self.generate(synthesize=mock.Mock(side_effect=TimeoutError())), 1)
        state = self.read(generator.STATE_FILE)
        first = next(iter(state["requests"].values()))
        first["status"] = "request-started"
        (self.output / generator.STATE_FILE).write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.generate("--resume", "--retry-ambiguous"), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(next(iter(self.read(generator.STATE_FILE)["requests"].values()))["attempts"], 2)

    def test_recovery_of_verified_staging_and_unrecorded_deduplicated_copy_is_free(self):
        self.assertEqual(self.generate(), 0, self.logs)
        state = self.read(generator.STATE_FILE)
        state["status"] = "incomplete"
        first = next(iter(state["requests"].values()))
        first["status"] = "downloaded"
        (self.output / generator.STATE_FILE).write_text(json.dumps(state), encoding="utf-8")
        (self.output / "identity.en.mp3").rename(self.output / "identity.en.mp3.part")
        (self.output / "duplicate.en.mp3").unlink()
        (self.output / generator.COURSE_FILE).unlink()
        catalog = self.read(generator.CATALOG_FILE)
        catalog["status"] = "incomplete"
        catalog["entries"] = catalog["entries"][2:]
        (self.output / generator.CATALOG_FILE).write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(self.generate("--resume", environment={}), 0, self.logs)
        self.assertEqual(len(self.requests), 2)
        self.assertFalse((self.output / "identity.en.mp3.part").exists())
        self.assertTrue((self.output / "duplicate.en.mp3").exists())

    def test_text_voice_model_and_settings_changes_never_reuse_old_audio(self):
        self.assertEqual(self.generate(), 0, self.logs)
        baseline = {path.name: path.read_bytes() for path in self.output.iterdir()}
        self.assertEqual(self.generate("--resume", voice=OTHER_VOICE), 1)
        with mock.patch.object(generator, "MODEL_ID", "changed-model"):
            self.assertEqual(self.generate("--resume"), 1)
        with mock.patch.dict(generator.VOICE_SETTINGS, {"stability": 0.7}):
            self.assertEqual(self.generate("--resume"), 1)
        self.course["scenes"][0]["cues"][0]["en"] = "What is your name?"
        self.write_source()
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual({path.name: path.read_bytes() for path in self.output.iterdir()}, baseline)

    def test_tampered_missing_audio_and_foreign_files_are_not_overwritten_or_rebilled(self):
        self.assertEqual(self.generate(), 0, self.logs)
        target = self.output / "identity.en.mp3"
        original = target.read_bytes()
        target.write_bytes(MP3 + b"foreign")
        self.assertEqual(self.generate("--resume", "--retry-ambiguous"), 1)
        self.assertEqual(target.read_bytes(), MP3 + b"foreign")
        target.unlink()
        self.assertEqual(self.generate("--resume", "--retry-ambiguous"), 1)
        target.write_bytes(original)
        foreign = self.output / "foreign.json"
        foreign.write_text("untouched", encoding="utf-8")
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(foreign.read_text(encoding="utf-8"), "untouched")
        self.assertEqual(len(self.requests), 2)

    def test_invalid_placeholder_duplicate_json_and_path_inputs_are_rejected_preflight(self):
        original = copy.deepcopy(self.course)
        for bad in ("[unclear]", "[inaudible]", "[needs review]", "TODO translate", "???", "<pending>"):
            self.course = copy.deepcopy(original)
            self.course["scenes"][0]["cues"][0]["en"] = bad
            self.write_source()
            self.assertEqual(self.generate(), 1)
            self.assertFalse(self.output.exists())
        self.course = copy.deepcopy(original)
        self.course["scenes"][0]["id"] = "../escape"
        self.write_source()
        self.assertEqual(self.generate(), 1)
        self.source.write_text('{"id":"one","id":"two"}', encoding="utf-8")
        self.assertEqual(self.generate(), 1)
        self.course = original
        self.write_source()
        for voice in ("../" + VOICE, f"{VOICE}?evil=1", "https://evil.test", "x\r\nheader"):
            self.assertEqual(self.generate(voice=voice), 1)
        for target in (
            ROOT / "build" / "web" / "english-test",
            ROOT / "assets" / "meme_courses" / "english-test",
            ROOT / "artifacts" / "meme-course-work",
            self.work / ".." / "traversal-test",
        ):
            self.output = target
            self.assertEqual(self.run_cli("--dry-run"), 1)
        self.assertEqual(self.requests, [])

    def test_marker_validation_does_not_censor_natural_speech_or_portuguese_todo(self):
        self.course["scenes"][0]["cues"][0].update(
            pt="Todo dia eu digo isso!", en="What the fuck??",
        )
        self.write_source()
        self.assertEqual(self.generate(), 0, self.logs)
        self.assertEqual(self.requests[0].text, "What the fuck?? Who am I?")

    def test_hard_linked_source_and_resume_files_are_rejected(self):
        alias = self.work / "source-alias.json"
        try:
            os.link(self.source, alias)
        except OSError:
            self.skipTest("Hard links unavailable on this filesystem")
        self.assertEqual(self.generate(), 1)
        alias.unlink()
        self.assertEqual(self.generate(), 0, self.logs)
        os.link(self.output / "identity.en.mp3", self.work / "audio-alias.mp3")
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(len(self.requests), 2)

    def test_symlinked_output_is_rejected(self):
        target = self.work / "foreign"
        target.mkdir()
        try:
            self.output.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink permission unavailable")
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(list(target.iterdir()), [])

    def test_bad_decoded_audio_is_never_promoted_or_marked_complete(self):
        for duration in (0, True, 60001):
            with self.subTest(duration=duration):
                self.output = self.work / f"duration-{duration}"
                self.assertEqual(self.generate(probe=lambda _: duration), 1)
                self.assertEqual(self.read(generator.CATALOG_FILE)["status"], "incomplete")
                self.assertEqual(list(self.output.glob("*.mp3")), [])
                self.assertFalse((self.output / generator.COURSE_FILE).exists())

    def test_duplicate_state_keys_and_untrusted_catalog_cannot_resume(self):
        self.assertEqual(self.generate(), 0, self.logs)
        saved = (self.output / generator.STATE_FILE).read_bytes()
        (self.output / generator.STATE_FILE).write_text('{"status":"complete","status":"incomplete"}', encoding="utf-8")
        self.assertEqual(self.generate("--resume"), 1)
        (self.output / generator.STATE_FILE).write_bytes(saved)
        catalog = self.read(generator.CATALOG_FILE)
        catalog["entries"][0]["file"] = "../outside.mp3"
        (self.output / generator.CATALOG_FILE).write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(self.generate("--resume"), 1)
        self.assertEqual(len(self.requests), 2)

    def test_catalog_types_cannot_impersonate_matching_metadata(self):
        self.assertEqual(self.generate(), 0, self.logs)
        catalog = self.read(generator.CATALOG_FILE)
        for change in (
            lambda value: value.update(schemaVersion=True),
            lambda value: value["voiceSettings"].update(style=False),
            lambda value: value["entries"][0].update(durationMs=1234.0),
        ):
            altered = copy.deepcopy(catalog)
            change(altered)
            raw = json.dumps(altered).encode()
            (self.output / generator.CATALOG_FILE).write_bytes(raw)
            self.assertEqual(self.generate("--resume"), 1)
            self.assertEqual((self.output / generator.CATALOG_FILE).read_bytes(), raw)
        self.assertEqual(len(self.requests), 2)

    def test_unknown_key_argument_is_not_echoed(self):
        self.assertEqual(self.run_cli("--dry-run", "--api-key", FAKE_KEY), 1)
        self.assertNotIn(FAKE_KEY, "\n".join(self.logs))


class EnglishAudioTransportTest(unittest.TestCase):
    def read(self, response):
        return generator.read_synthesis_response(response, deadline=time.monotonic() + 60)

    def test_valid_audio_is_read_bounded_with_optional_length(self):
        self.assertEqual(self.read(_Response()), MP3)
        self.assertEqual(self.read(_Response(headers=[("Content-Type", "audio/mpeg; charset=binary")])), MP3)
        self.assertEqual(self.read(_Response(headers=[
            ("Content-Type", "audio/mpeg"), ("Transfer-Encoding", "chunked"),
        ])), MP3)

    def test_redirect_wrong_type_empty_oversize_duplicate_length_and_truncated_body_fail(self):
        for response in (
            _Response(status=302), _Response(status=429), _Response(status=503),
            _Response(headers=[("Content-Type", "application/json")]),
            _Response(data=b""),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Length", str(len(MP3) + 1))]),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Length", "-1")]),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Length", str(3 * 1024 * 1024))]),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Length", "10"), ("Content-Length", "10")]),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Encoding", "gzip")]),
            _Response(headers=[("Content-Type", "audio/mpeg"), ("Content-Length", str(len(MP3))), ("Transfer-Encoding", "chunked")]),
            _Response(data=b"<html>not audio</html>"),
        ):
            with self.subTest(response=response.headers, status=response.status):
                with self.assertRaises(generator.GenerationError):
                    self.read(response)
        with mock.patch.object(generator, "MAX_AUDIO_BYTES", len(MP3) - 1):
            with self.assertRaises(generator.GenerationError):
                self.read(_Response(headers=[("Content-Type", "audio/mpeg")]))
        with self.assertRaises(generator.GenerationError):
            generator.read_synthesis_response(_Response(), deadline=time.monotonic() - 1)

    def test_fixed_https_host_only_one_post_no_redirect_or_retry_and_secret_redaction(self):
        request = generator.SynthesisRequest(VOICE, "Hello there!", FAKE_KEY)
        with mock.patch.object(generator.http.client, "HTTPSConnection") as factory:
            connection = factory.return_value
            connection.getresponse.return_value = _Response(status=302)
            with self.assertRaises(generator.GenerationError) as error:
                generator.synthesize_with_elevenlabs(request)
            factory.assert_called_once_with("api.elevenlabs.io", timeout=15)
            connection.request.assert_called_once()
            args, kwargs = connection.request.call_args
            self.assertEqual(args, ("POST", request.path))
            self.assertEqual(json.loads(kwargs["body"]), request.body)
            self.assertEqual(kwargs["headers"]["xi-api-key"], FAKE_KEY)
            connection.close.assert_called_once()
            self.assertNotIn(FAKE_KEY, str(error.exception))
        with mock.patch.object(generator.http.client, "HTTPSConnection") as factory:
            factory.return_value.request.side_effect = TimeoutError(FAKE_KEY)
            with self.assertRaises(generator.GenerationError) as error:
                generator.synthesize_with_elevenlabs(request)
            factory.return_value.request.assert_called_once()
            self.assertNotIn(FAKE_KEY, str(error.exception))
        with mock.patch.object(generator.http.client, "HTTPSConnection") as factory:
            connection = factory.return_value
            def closing_response():
                connection.sock = None
                return _Response()
            connection.getresponse.side_effect = closing_response
            self.assertEqual(generator.synthesize_with_elevenlabs(request), MP3)
            connection.request.assert_called_once()

    def test_ffprobe_requires_decoded_mp3_frames_and_safe_local_pipe(self):
        metadata = {
            "streams": [{"codec_name": "mp3", "sample_rate": "44100", "channels": 1}],
            "frames": [{"nb_samples": 44100}, {"nb_samples": 22050}],
        }
        with mock.patch.object(generator.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout=json.dumps(metadata).encode(), stderr=b"")
            self.assertEqual(generator.probe_mp3(MP3), 1500)
            command = run.call_args.args[0]
            self.assertEqual(command[:5], ["ffprobe", "-v", "error", "-protocol_whitelist", "pipe"])
            self.assertEqual(command[-2:], ["-i", "pipe:0"])
            self.assertEqual(run.call_args.kwargs["input"], MP3)
            self.assertEqual(run.call_args.kwargs["timeout"], 30)
            for change in (
                {"frames": []},
                {"frames": [{"nb_samples": 44100 * 61}]},
                {"frames": [{"nb_samples": True}]},
                {"streams": [{"codec_name": "aac", "sample_rate": "44100", "channels": 1}]},
                {"streams": [{"codec_name": "mp3", "sample_rate": "22050", "channels": 1}]},
            ):
                run.return_value.stdout = json.dumps({**metadata, **change}).encode()
                with self.assertRaises(generator.GenerationError):
                    generator.probe_mp3(MP3)
            run.return_value.stdout = json.dumps(metadata).encode()
            run.return_value.stderr = FAKE_KEY.encode()
            with self.assertRaises(generator.GenerationError) as error:
                generator.probe_mp3(MP3)
            self.assertNotIn(FAKE_KEY, str(error.exception))
            run.return_value.stderr = b""
            run.return_value.stdout = b"{}"
            with self.assertRaises(generator.GenerationError):
                generator.probe_mp3(MP3)


if __name__ == "__main__":
    unittest.main()
