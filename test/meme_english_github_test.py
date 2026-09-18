import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

from tool import run_meme_english_audio as github
from tool import generate_meme_english_audio as synthesis


class GithubEnglishAudioTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="english-github-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = {
            "schemaVersion": 1, "kind": "meme_english_tts_request",
            "courseId": "meme_test", "sourceCourseSha256": "a" * 64,
            "editorialStatus": "draft", "language": "en",
            "scenes": [
                {"id": "one", "text": "Who are you?",
                 "textSha256": hashlib.sha256(b"Who are you?").hexdigest()},
                {"id": "two", "text": "What do you mean?",
                 "textSha256": hashlib.sha256(b"What do you mean?").hexdigest()},
            ],
        }
        self.voice = "test_voice"
        self.code_hash = "b" * 64
        self.identifier = github.batch_id(self.request, self.voice, self.code_hash)
        self.engine = SimpleNamespace(
            CATALOG_FILENAME="english-audio-catalog.json",
            DEFAULT_MODEL_ID="eleven_multilingual_v2",
            DEFAULT_OUTPUT_FORMAT="mp3_44100_64",
            DEFAULT_VOICE_SETTINGS={
                "stability": 0.5, "similarity_boost": 0.75, "style": 0.0,
                "use_speaker_boost": True, "speed": 1.0,
            },
            export_english_request=lambda _: copy.deepcopy(self.request),
        )
        self.patch = mock.patch.object(github, "engine_module", return_value=self.engine)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.request_patch = mock.patch.object(
            github, "load_request", return_value=copy.deepcopy(self.request),
        )
        self.request_patch.start()
        self.addCleanup(self.request_patch.stop)
        self.audio = b"ID3\x04\x00\x00\x00\x00\x00\x10fixture"
        self.catalog = {
            "schemaVersion": 1, "status": "complete", "courseId": "meme_test",
            "language": "en", "voiceId": self.voice,
            "modelId": self.engine.DEFAULT_MODEL_ID,
            "outputFormat": self.engine.DEFAULT_OUTPUT_FORMAT,
            "voiceSettings": self.engine.DEFAULT_VOICE_SETTINGS,
            "entries": [
                {
                    "sceneId": scene["id"], "file": f'{scene["id"]}.en.mp3',
                    "textSha256": scene["textSha256"],
                    "sha256": hashlib.sha256(self.audio).hexdigest(),
                    "bytes": len(self.audio), "durationMs": 1500,
                }
                for scene in self.request["scenes"]
            ],
        }
        self.receipt = {
            "batchId": self.identifier, "engineSha256": self.code_hash,
            "voiceId": self.voice, "environment": github.DEFAULT_ENVIRONMENT,
        }

    def archive(self, *, extra=None, audio=None):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as output:
            output.writestr(self.engine.CATALOG_FILENAME, json.dumps(self.catalog))
            output.writestr(github.RECEIPT, json.dumps(self.receipt))
            for scene in self.request["scenes"]:
                output.writestr(f'{scene["id"]}.en.mp3', self.audio if audio is None else audio)
            for name, data in (extra or {}).items():
                info = zipfile.ZipInfo("fixture")
                info.filename = name
                output.writestr(info, data)
        return stream.getvalue()

    def verify(self, raw=None):
        return github.verify_archive(
            self.archive() if raw is None else raw, self.request, self.voice,
            self.identifier, self.code_hash,
        )

    def test_fingerprint_binds_voice_text_and_engine_not_unrelated_course_edits(self):
        revised = copy.deepcopy(self.request)
        revised["sourceCourseSha256"] = "c" * 64
        self.assertEqual(self.identifier, github.batch_id(revised, self.voice, self.code_hash))
        self.assertNotEqual(self.identifier, github.batch_id(revised, "other_voice", self.code_hash))
        self.assertNotEqual(self.identifier, github.batch_id(revised, self.voice, "d" * 64))
        self.assertNotEqual(self.identifier, github.batch_id(revised, self.voice, self.code_hash, "copilot"))
        revised["scenes"][0]["textSha256"] = "e" * 64
        self.assertNotEqual(self.identifier, github.batch_id(revised, self.voice, self.code_hash))

    def test_verified_archive_contains_only_expected_audio_catalog_and_receipt(self):
        files = self.verify()
        self.assertEqual(set(files), {
            self.engine.CATALOG_FILENAME, github.RECEIPT, "one.en.mp3", "two.en.mp3",
        })
        self.assertEqual(files["one.en.mp3"], self.audio)

    def test_incomplete_or_wrong_voice_is_not_success(self):
        for key, value in (("status", "incomplete"), ("voiceId", "another"),
                           ("courseId", "meme_other"), ("language", "pt")):
            with self.subTest(key=key):
                old = self.catalog[key]
                self.catalog[key] = value
                with self.assertRaises(github.GithubGenerationError):
                    self.verify()
                self.catalog[key] = old

    def test_missing_scene_cannot_be_a_complete_download(self):
        self.catalog["entries"].pop()
        with self.assertRaisesRegex(github.GithubGenerationError, "todas"):
            self.verify()

    def test_duplicate_scene_is_rejected(self):
        self.catalog["entries"][1] = self.catalog["entries"][0]
        with self.assertRaisesRegex(github.GithubGenerationError, "repetida"):
            self.verify()

    def test_text_audio_duration_and_file_binding_are_checked(self):
        values = {
            "textSha256": "f" * 64, "sha256": "f" * 64,
            "durationMs": True, "file": "../other.mp3",
        }
        for key, value in values.items():
            with self.subTest(key=key):
                old = self.catalog["entries"][0][key]
                self.catalog["entries"][0][key] = value
                with self.assertRaises(github.GithubGenerationError):
                    self.verify()
                self.catalog["entries"][0][key] = old

    def test_corrupt_audio_is_not_copied(self):
        with self.assertRaisesRegex(github.GithubGenerationError, "corrompido"):
            self.verify(self.archive(audio=b"changed recording"))

    def test_mismatched_generator_receipt_is_rejected(self):
        self.receipt["engineSha256"] = "c" * 64
        with self.assertRaisesRegex(github.GithubGenerationError, "recibo"):
            self.verify()

    def test_even_unused_archive_traversal_is_rejected(self):
        for name in ("../outside.txt", "/absolute.txt", "a\\b.txt", "C:other.txt"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(github.GithubGenerationError, "inseguro"):
                    self.verify(self.archive(extra={name: b"no"}))
        self.assertFalse((self.root / "outside.txt").exists())

    def test_profile_booleans_cannot_impersonate_numbers(self):
        self.catalog["voiceSettings"] = {**self.engine.DEFAULT_VOICE_SETTINGS, "style": False}
        with self.assertRaises(github.GithubGenerationError):
            self.verify()

    def test_dry_run_never_requests_a_key_or_uses_network_or_output(self):
        output = self.root / "new"
        with mock.patch.object(github, "gh") as request, \
                mock.patch("builtins.input") as prompt, \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            result = github.main(["course.json", "--output", str(output), "--dry-run"])
        self.assertEqual(result, 0)
        request.assert_not_called()
        prompt.assert_not_called()
        self.assertFalse(output.exists())

    def test_english_only_request_uses_the_engine_validation_contract(self):
        with mock.patch.object(github, "engine_module", return_value=synthesis):
            self.assertEqual(github.validate_request(self.request), self.request)
            invalid = copy.deepcopy(self.request)
            invalid["scenes"][0]["text"] = "A different line."
            with self.assertRaises(github.GithubGenerationError):
                github.validate_request(invalid)

    def test_worker_passes_only_authorized_flags_to_local_engine(self):
        environment = {
            "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "example/repo",
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
            "TTS_REQUEST_JSON": json.dumps(self.request), "TTS_VOICE_ID": self.voice,
            "TTS_BATCH_ID": self.identifier, "TTS_ENGINE_SHA256": self.code_hash,
            "TTS_SECRET_ENVIRONMENT": github.DEFAULT_ENVIRONMENT,
            "TTS_ALLOW_DRAFT": "true", "TTS_REGENERATE": "false",
        }

        def execute(arguments, **_):
            output = Path(arguments[arguments.index("--output") + 1])
            output.mkdir()
            return subprocess.CompletedProcess(arguments, 0)

        with mock.patch.dict("os.environ", environment, clear=True), \
                mock.patch.object(github, "ROOT", self.root), \
                mock.patch.object(github.compiler, "ROOT", self.root), \
                mock.patch.object(github, "engine_hash", return_value=self.code_hash), \
                mock.patch.object(github, "validate_request", side_effect=lambda value: value), \
                mock.patch.object(github, "gh", return_value=[]), \
                mock.patch.object(github.subprocess, "run", side_effect=execute) as run, \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            github.worker()
        arguments = run.call_args.args[0]
        for flag in ("--local", "--generate", "--yes", "--allow-draft"):
            self.assertIn(flag, arguments)
        saved = self.root / "build" / "meme-course-work" / "github-123-1" / "audio" / github.RECEIPT
        self.assertEqual(json.loads(saved.read_text())["environment"], github.DEFAULT_ENVIRONMENT)

    def test_noninteractive_generation_requires_voice_not_api_key(self):
        with mock.patch.object(github, "gh") as request, \
                mock.patch("builtins.input") as prompt, \
                mock.patch("sys.stdin.isatty", return_value=False), \
                mock.patch("sys.stdout", new_callable=io.StringIO), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as error:
            result = github.main(["course.json", "--generate", "--yes"])
        self.assertEqual(result, 1)
        self.assertIn("--voice-id", error.getvalue())
        request.assert_not_called()
        prompt.assert_not_called()

    def test_gh_child_does_not_receive_elevenlabs_key(self):
        completed = subprocess.CompletedProcess([], 0, stdout=b"{}", stderr=b"")
        with mock.patch.dict("os.environ", {"ELEVENLABS_API_KEY": "private-fixture-value"}), \
                mock.patch.object(github.subprocess, "run", return_value=completed) as run:
            github.gh(["api", "repos/example/repo"])
        self.assertNotIn("ELEVENLABS_API_KEY", run.call_args.kwargs["env"])

    def test_gh_failure_never_prints_provider_output_or_retries(self):
        completed = subprocess.CompletedProcess(
            [], 1, stdout=b"", stderr=b"private-fixture-value",
        )
        with mock.patch.object(github.subprocess, "run", return_value=completed) as run:
            with self.assertRaises(github.GithubGenerationError) as error:
                github.gh(["api", "repos/example/repo"])
        self.assertNotIn("private-fixture-value", str(error.exception))
        self.assertEqual(run.call_count, 1)

    def test_failed_remote_run_does_not_dispatch_a_retry(self):
        with mock.patch.object(github, "gh", return_value={
            "status": "completed", "conclusion": "failure",
        }) as call:
            with self.assertRaisesRegex(github.GithubGenerationError, "sem sucesso"):
                github.wait_for_run("example/repo", 1)
        self.assertEqual(call.call_count, 1)
        self.assertNotIn("POST", call.call_args.args[0])

    def test_workflow_uses_existing_secret_without_deploy_or_secret_export(self):
        text = (github.ROOT / ".github" / "workflows" / github.WORKFLOW).read_text(encoding="utf-8")
        self.assertIn("environment: ${{ inputs.secret_environment }}", text)
        self.assertIn("default: fluent", text)
        self.assertIn("inputs.secret_environment == 'fluent'", text)
        self.assertIn("secrets.ELEVENLABS_API_KEY", text)
        self.assertIn("github.event.repository.default_branch", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertNotIn("firebase deploy", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("secrets.ELEVENLABS_API_KEY }}\"", text)


if __name__ == "__main__":
    unittest.main()
