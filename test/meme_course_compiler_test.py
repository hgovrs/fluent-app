import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest import mock
import uuid

from tool import compile_meme_course as compiler


REPOSITORY = Path(__file__).resolve().parent.parent


class MemeCourseCompilerTest(unittest.TestCase):
    def setUp(self):
        # Never use the system temporary directory or an active app asset.
        self.work = (
            REPOSITORY / "artifacts" / "meme-course-work"
            / f".compiler-test-{uuid.uuid4().hex[:12]}"
        )
        self.work.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.work)
        self.repo = self.work / "repository"
        self.repo.mkdir()
        self.session_root = self.work / "sessions"
        self.session_files = self.session_root / "test-session" / "files"
        self.session_files.mkdir(parents=True)
        self.library = self.work / "sources.json"
        self.library.write_text('{"sources": [{"id": "reviewed-book"}]}', encoding="utf-8")
        for name, value in (
            ("ROOT", self.repo),
            ("SESSION_STATE_ROOT", self.session_root),
            ("SOURCE_LIBRARY", self.library),
        ):
            patch = mock.patch.object(compiler, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.pairs = self.work / "pairs"
        self.pairs.mkdir()
        self.draft_path = self.work / "draft.json"
        self.catalog_path = self.pairs / "catalog.json"
        self.output = self.repo / "build" / "meme-course-work" / "review-001"
        self.scene_id = "cena_identity"
        payload = b"synthetic signature fixture, not decoded media"
        webp = b"RIFF" + (len(payload) + 4).to_bytes(4, "little") + b"WEBP" + payload
        self.media = {
            ".webp": webp,
            ".mp3": b"ID3\x04\x00\x00\x00\x00\x00\x00" + payload,
            ".png": b"\x89PNG\r\n\x1a\n" + payload,
        }
        for suffix, data in self.media.items():
            (self.pairs / f"{self.scene_id}{suffix}").write_bytes(data)
        self.catalog = {
            "schemaVersion": 1,
            "sourceDuration": 10,
            "sourceSha256": "a" * 64,
            "format": "webp",
            "clipAudio": True,
            "reviewRequired": True,
            "approvalStatus": "NOT APPROVED",
            "clips": [{
                "id": self.scene_id,
                "category": "incorrect",
                "start": 2, "end": 3, "durationMs": 1000,
                "audioDurationMs": 1000, "visualDurationMs": 1000,
                "file": f"{self.scene_id}.webp",
                "audioFile": f"{self.scene_id}.mp3",
                "posterFile": f"{self.scene_id}.png",
                "visualBytes": len(self.media[".webp"]),
                "audioBytes": len(self.media[".mp3"]),
                "posterBytes": len(self.media[".png"]),
                "audioEncoding": {
                    "codec": "mp3", "sampleRate": 44100,
                    "decodedSamples": 44100, "sourceSamples": 44100,
                },
                "approved": False,
                "labelIsCertifiedTranscript": False,
            }],
        }
        self.course = {
            "id": "meme_fixture_identity",
            "title": "Identidade — rascunho",
            "sourceLanguage": "pt-BR", "targetLanguage": "en",
            "level": "Básico–intermediário · inglês informal",
            "coverage": "Thematic practice, not CEFR certification.",
            "contentVersion": 1, "kind": "memes", "editorialStatus": "draft",
            "contentWarning": "Optional adult slang; draft captions.",
            "scenes": [{
                "id": self.scene_id, "title": "What do you mean?",
                "format": "webp", "durationMs": 1000,
                "adaptationNotes": "Draft wording and tone; review before use.",
                "cues": [{
                    "startMs": 100, "endMs": 900,
                    "pt": "Como assim?", "en": "What do you mean?",
                }],
            }],
            "units": [{
                "id": "meme_fixture_identity_u1",
                "title": "Ask for meaning",
                "description": "Ask for a clear explanation.",
                "lessons": [{
                    "id": "meme_fixture_identity_u1_l1",
                    "title": "A useful reply",
                    "description": "Use a direct question.",
                    "studyNotes": "What do you mean? asks for an explanation.",
                    "sourceIds": [],
                    "exercises": [
                        {
                            "id": "meme_fixture_identity_u1_l1_e1", "type": "choice",
                            "sceneId": self.scene_id,
                            "prompt": "What does the draft English line ask the other person to do?",
                            "answer": "Give an explanation.",
                            "options": ["Say goodbye.", "Give an explanation."],
                            "explanation": "The speaker asks for a clearer meaning.",
                        },
                        {
                            "id": "meme_fixture_identity_u1_l1_e2", "type": "typed",
                            "sceneId": self.scene_id,
                            "prompt": "Complete the question: What ___ you mean? Use one word from: do | is | am.",
                            "answer": "do",
                            "explanation": "Use do with you in this question.",
                        },
                        {
                            "id": "meme_fixture_identity_u1_l1_e3", "type": "wordOrder",
                            "sceneId": self.scene_id,
                            "prompt": "Build the question used to ask for an explanation.",
                            "answer": "What do you mean?",
                            "options": ["mean", "What", "you", "do"],
                            "explanation": "Put do before you in this direct question.",
                        },
                    ],
                }],
            }],
        }

    @property
    def lesson(self):
        return self.course["units"][0]["lessons"][0]

    @property
    def exercises(self):
        return self.lesson["exercises"]

    @property
    def scene(self):
        return self.course["scenes"][0]

    @property
    def clip(self):
        return self.catalog["clips"][0]

    def write_inputs(self):
        self.draft_path.write_text(
            json.dumps(self.course, ensure_ascii=False), encoding="utf-8"
        )
        self.catalog_path.write_text(json.dumps(self.catalog), encoding="utf-8")

    def compile(self):
        self.write_inputs()
        return compiler.compile_course(self.draft_path, self.catalog_path, self.output)

    def invalid_course(self, message=None):
        with self.assertRaisesRegex(compiler.CompileError, message or "."):
            compiler.validate_course(self.course)

    def invalid_package(self, message=None):
        with self.assertRaisesRegex(compiler.CompileError, message or "."):
            self.compile()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob(".meme-course-stage-*")), [])

    def test_package_contains_only_course_manifest_and_selected_derived_pairs(self):
        original = copy.deepcopy(self.course)
        (self.pairs / "original-do-not-package.mp4").write_bytes(b"private original")
        manifest = self.compile()
        self.assertEqual(self.course, original)
        self.assertEqual(manifest["counts"]["scenes"], 1)
        self.assertEqual(manifest["counts"]["exercises"], 3)
        self.assertEqual(manifest["counts"]["mediaFiles"], 3)
        self.assertEqual(
            manifest["counts"]["exerciseTypes"], {"choice": 1, "typed": 1, "wordOrder": 1}
        )
        paths = {path.relative_to(self.output).as_posix() for path in self.output.rglob("*") if path.is_file()}
        expected_media = {
            f"assets/meme_courses/{self.course['id']}/{self.scene_id}{suffix}"
            for suffix in self.media
        }
        self.assertEqual(paths, {"course.json", "review-manifest.json"} | expected_media)
        for entry in manifest["files"]:
            raw = (self.output / entry["path"]).read_bytes()
            self.assertEqual(len(raw), entry["bytes"])
            digest = hashlib.sha256(raw).hexdigest()
            self.assertEqual(digest, entry["sha256"])
            self.assertEqual(digest, manifest["perFileSHA256"][entry["path"]])
        for suffix, raw in self.media.items():
            path = self.output / "assets" / "meme_courses" / self.course["id"] / f"{self.scene_id}{suffix}"
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual((self.pairs / f"{self.scene_id}{suffix}").read_bytes(), raw)
        compiled = json.loads((self.output / "course.json").read_text(encoding="utf-8"))
        self.assertEqual(compiled["englishLocale"], "en-US")
        for exercise in compiled["units"][0]["lessons"][0]["exercises"]:
            self.assertEqual(exercise["englishReveal"], "afterAnswer")
        self.assertEqual(manifest["sourceSha256"], "a" * 64)
        self.assertEqual(manifest["editorialStatus"], "draft")
        self.assertTrue(manifest["reviewRequired"])
        self.assertFalse(manifest["publicationApproved"])
        self.assertFalse(manifest["originalVideoIncluded"])
        self.assertIn("unverified", manifest["reviewFlags"]["speakerIdentity"])
        self.assertIn("no decoding", manifest["mediaVerification"])
        self.assertEqual(manifest["draftSha256"], hashlib.sha256(self.draft_path.read_bytes()).hexdigest())
        self.assertEqual(manifest["mediaCatalogSha256"], hashlib.sha256(self.catalog_path.read_bytes()).hexdigest())
        self.assertEqual(manifest, json.loads((self.output / "review-manifest.json").read_text(encoding="utf-8")))

    def test_authored_adaptations_are_not_literal_translation_or_profanity_mapping(self):
        cue = self.scene["cues"][0]
        cue["pt"] = "E aí, viado? Porra!"
        self.scene["adaptationNotes"] = "Draft: possible friendly address. Do not escalate hostility."
        for adaptation in ("Hey, girl! Damn!", "Hey, buddy! Damn!"):
            with self.subTest(adaptation=adaptation):
                cue["en"] = adaptation
                result = compiler.validate_course(self.course)
                self.assertEqual(result["scenes"][0]["cues"][0], cue)
                self.assertNotIn("faggot", json.dumps(result))
        self.compile()
        compiled = json.loads((self.output / "course.json").read_text(encoding="utf-8"))
        self.assertEqual(compiled["scenes"][0]["cues"][0]["pt"], cue["pt"])
        self.assertEqual(compiled["scenes"][0]["cues"][0]["en"], "Hey, buddy! Damn!")

    def test_draft_only_and_english_locale(self):
        for key, invalid_values in {
            "kind": ["traditional", None],
            "editorialStatus": ["reviewed", None],
            "sourceLanguage": ["en"],
            "targetLanguage": ["pt-BR"],
            "englishLocale": ["en-AU", "pt-BR"],
            "contentVersion": [0, True, 1.5],
        }.items():
            original = self.course.get(key)
            for value in invalid_values:
                with self.subTest(key=key, value=value):
                    self.course[key] = value
                    self.invalid_course()
            if original is None:
                self.course.pop(key, None)
            else:
                self.course[key] = original
        self.course["englishLocale"] = "en-GB"
        self.course["contentWarning"] = ""
        self.assertEqual(compiler.validate_course(self.course)["englishLocale"], "en-GB")

    def test_required_fields_and_paths_cannot_be_smuggled_into_schema(self):
        for value, key in (
            (self.course, "kind"), (self.scene, "adaptationNotes"),
            (self.lesson, "studyNotes"), (self.exercises[0], "sceneId"),
        ):
            old = value.pop(key)
            with self.subTest(missing=key):
                self.invalid_course("missing fields")
            value[key] = old
        for value, key in (
            (self.course, "assetPath"), (self.scene, "audioFile"),
            (self.exercises[0], "englishAudio"), (self.lesson, "publish"),
        ):
            value[key] = "https://invalid.test/asset"
            with self.subTest(extra=key):
                self.invalid_course("unsupported fields")
            del value[key]

    def test_comparison_only_rejected_at_every_input_level(self):
        for target in (self.course, self.scene, self.exercises[0], self.catalog, self.clip):
            target["comparisonOnly"] = True
            with self.subTest(target=list(target)[:2]):
                self.invalid_package("comparisonOnly")
            del target["comparisonOnly"]

    def test_protected_and_unsafe_course_ids(self):
        for value in ("en-a1", "en-new", "../escape", "Uppercase", "a" * 81, "con"):
            self.course["id"] = value
            with self.subTest(value=value):
                self.invalid_course()

    def test_scene_ids_and_namespace_are_checked(self):
        for value in ("../escape", "scene-id", "a" * 65, "con"):
            self.scene["id"] = value
            with self.subTest(value=value):
                self.invalid_course()
        self.scene["id"] = self.scene_id
        self.exercises[0]["id"] = "other_course_e1"
        self.invalid_course("namespace")

    def test_duplicate_ids_across_levels_rejected(self):
        self.exercises[0]["id"] = self.lesson["id"]
        self.invalid_course("duplicate ID")

    def test_duplicate_scene_ids_rejected(self):
        self.course["scenes"].append(copy.deepcopy(self.scene))
        self.invalid_course("duplicate ID")

    def test_unknown_and_unused_scenes_rejected(self):
        self.exercises[0]["sceneId"] = "missing"
        self.invalid_course("resolve")
        self.exercises[0]["sceneId"] = self.scene_id
        unused = copy.deepcopy(self.scene)
        unused["id"] = "unused"
        self.course["scenes"].append(unused)
        self.invalid_course("every packaged scene")

    def test_source_references_must_exist_and_not_repeat(self):
        self.lesson["sourceIds"] = ["invented-source"]
        self.invalid_course("unknown references")
        self.lesson["sourceIds"] = ["reviewed-book", "reviewed-book"]
        self.invalid_course("duplicate reference")
        self.lesson["sourceIds"] = ["reviewed-book"]
        self.lesson["readingPassage"] = "This is an original practice example."
        self.assertEqual(compiler.validate_course(self.course)["units"][0]["lessons"][0]["sourceIds"], ["reviewed-book"])

    def test_cue_gaps_are_legal_but_order_overlap_and_full_video_times_are_not(self):
        self.scene["cues"] = [
            {"startMs": 0, "endMs": 100, "pt": "Oi.", "en": "Hi."},
            {"startMs": 200, "endMs": 800, "pt": "Quem é você?", "en": "Who are you?"},
        ]
        compiler.validate_course(self.course)
        for start, end in ((99, 800), (800, 800), (-1, 800), (200, 1001), (16050, 16950), (True, 800)):
            self.scene["cues"][1].update(startMs=start, endMs=end)
            with self.subTest(start=start, end=end):
                self.invalid_course()
        self.scene["cues"].reverse()
        self.invalid_course()

    def test_duration_and_cue_text_bounds(self):
        for duration in (0, 30001, True, 1000.0):
            self.scene["durationMs"] = duration
            with self.subTest(duration=duration):
                self.invalid_course()
        self.scene["durationMs"] = 1000
        for key in ("pt", "en"):
            original = self.scene["cues"][0][key]
            for value in ("", " ", "a" * 1001, "\ud800"):
                self.scene["cues"][0][key] = value
                with self.subTest(key=key, value_length=len(value)):
                    self.invalid_course()
            self.scene["cues"][0][key] = original
        self.scene["cues"] = []
        self.invalid_course()

    def test_scene_title_and_adaptation_notes_limits(self):
        for field, size in (("title", 201), ("adaptationNotes", 3001)):
            old = self.scene[field]
            self.scene[field] = "x" * size
            self.invalid_course()
            self.scene[field] = old

    def test_choice_normalization_and_exactly_one_correct_option(self):
        self.exercises[0]["answer"] = "  GIVE AN EXPLANATION! "
        compiler.validate_course(self.course)
        self.exercises[0]["options"].append("give an explanation?")
        self.invalid_course("distinct normalized")
        self.exercises[0]["options"].pop()
        self.exercises[0]["acceptedAnswers"] = ["Say goodbye."]
        self.invalid_course("exactly one")
        self.exercises[0]["acceptedAnswers"] = []
        self.exercises[0]["answer"] = "A different answer"
        self.invalid_course("exactly one")

    def test_answers_cannot_be_empty_or_redundant_after_normalization(self):
        self.exercises[0]["answer"] = "?!"
        self.invalid_course("answers")
        self.exercises[0]["answer"] = "Give an explanation."
        self.exercises[0]["acceptedAnswers"] = ["GIVE AN EXPLANATION"]
        self.invalid_course("distinct after runtime normalization")

    def test_word_order_checks_duplicate_tokens_and_all_accepted_variants(self):
        item = self.exercises[2]
        item["answer"] = "Do you know what you mean?"
        item["options"] = ["you", "what", "mean", "Do", "you", "know"]
        compiler.validate_course(self.course)
        item["options"].remove("you")
        self.invalid_course("tokens")
        item["options"].append("you")
        item["acceptedAnswers"] = ["Do you know what I mean?"]
        self.invalid_course("tokens")
        item["acceptedAnswers"] = []
        item["options"][0] = "you know"
        self.invalid_course("individual")

    def test_typed_questions_require_one_blank_and_a_bounded_english_prompt(self):
        original = self.exercises[1]["prompt"]
        for prompt in (
            "Translate the whole scene.", "Write anything you like: ___.",
            "Complete: ___ ___. Use one word from: do | am.",
            "Complete: ___. Use one word from: do.",
            "Complete: ___. Use one word from: do | DO!",
            "Complete: ___. Use one word from: do | do not.",
        ):
            self.exercises[1]["prompt"] = prompt
            with self.subTest(prompt=prompt):
                self.invalid_course("typed|one word")
        self.exercises[1]["prompt"] = original
        self.exercises[1]["answer"] = "does"
        self.invalid_course("explicitly listed")
        self.exercises[1]["answer"] = "do"
        self.exercises[1]["acceptedAnswers"] = ["does"]
        self.invalid_course("explicitly listed")
        self.exercises[1]["acceptedAnswers"] = []
        self.exercises[1]["options"] = ["do", "is"]
        self.invalid_course("typed")

    def test_typed_accepted_forms_are_explicit_and_preserved(self):
        item = self.exercises[1]
        item["prompt"] = "Complete a statement about yourself: ___ ready. Use a listed phrase from: I'm | I am | You're."
        item["answer"] = "I'm"
        item["acceptedAnswers"] = ["I am"]
        result = compiler.validate_course(self.course)
        validated = result["units"][0]["lessons"][0]["exercises"][1]
        self.assertEqual(validated["answer"], "I'm")
        self.assertEqual(validated["acceptedAnswers"], ["I am"])

    def test_portuguese_teaching_keeps_english_word_choices(self):
        item = self.exercises[1]
        item["prompt"] = "Complete em inglês: What ___ you mean? Use uma destas palavras: do | is | am."
        item["explanation"] = "Use do com you nesta pergunta."
        result = compiler.validate_course(self.course)
        self.assertEqual(
            result["units"][0]["lessons"][0]["exercises"][1]["prompt"],
            item["prompt"],
        )
        item["prompt"] = "Complete: What ___ you mean? Use uma destas palavras: do | do not."
        self.invalid_course("one word")

    def test_portuguese_phrase_choices_preserve_meaningful_variants(self):
        item = self.exercises[1]
        item["prompt"] = "Complete a frase sobre você: ___ ready. Use uma destas expressões: I'm | I am | You're."
        item["answer"] = "I'm"
        item["acceptedAnswers"] = ["I am"]
        result = compiler.validate_course(self.course)
        self.assertEqual(
            result["units"][0]["lessons"][0]["exercises"][1]["acceptedAnswers"],
            ["I am"],
        )

    def test_portuguese_translation_questions_keep_answers_hidden(self):
        item = self.exercises[0]
        item["englishReveal"] = "beforeAnswer"
        for prompt in ("Traduza a fala.", "Escolha a tradução.", "Qual é a versão em inglês?"):
            with self.subTest(prompt=prompt):
                item["prompt"] = prompt
                self.invalid_course("afterAnswer")

    def test_english_reveal_never_exposes_production_or_obvious_translation_answers(self):
        for item in self.exercises[1:]:
            item["englishReveal"] = "beforeAnswer"
            self.invalid_course("afterAnswer")
            item["englishReveal"] = "afterAnswer"
        self.exercises[0]["englishReveal"] = "beforeAnswer"
        compiler.validate_course(self.course)
        self.exercises[0]["prompt"] = "Translate the draft Portuguese line."
        self.invalid_course("afterAnswer")
        self.exercises[0]["englishReveal"] = "always"
        self.invalid_course("englishReveal")

    def test_missing_and_duplicate_catalog_clip_ids(self):
        self.clip["id"] = "another_scene"
        self.invalid_package("no paired clip")
        self.clip["id"] = self.scene_id
        self.catalog["clips"].append(copy.deepcopy(self.clip))
        self.invalid_package("duplicate catalog")

    def test_media_source_and_encoding_records_are_required(self):
        for key, invalid in (
            ("sourceSha256", "not-a-hash"), ("clipAudio", False),
            ("schemaVersion", True), ("sourceDuration", 2),
            ("format", "mp4"),
        ):
            old = self.catalog[key]
            self.catalog[key] = invalid
            self.invalid_package()
            self.catalog[key] = old
        self.clip["audioEncoding"]["codec"] = "aac"
        self.invalid_package("MP3")

    def test_catalog_and_scene_duration_mismatches(self):
        for key, value in (
            ("durationMs", 900), ("start", 1), ("end", 11),
            ("audioDurationMs", 950), ("visualDurationMs", 950),
            ("durationMs", True), ("end", float("inf")),
        ):
            old = self.clip[key]
            self.clip[key] = value
            with self.subTest(key=key):
                self.invalid_package()
            self.clip[key] = old
        self.clip["audioEncoding"]["decodedSamples"] = 43000
        self.invalid_package("sample record")

    def test_explicit_mp3_padding_must_match_both_sample_and_duration_records(self):
        encoding = self.clip["audioEncoding"]
        encoding["trailingPaddingSamples"] = 100
        encoding["decodedSamples"] = 44200
        self.clip["audioDurationMs"] = 44200 * 1000 / 44100
        manifest = self.compile()
        self.assertEqual(manifest["scenes"][0]["audioTrailingPaddingSamples"], 100)
        self.assertEqual(manifest["scenes"][0]["audioSourceDurationMs"], 1000)
        self.output = self.output.with_name("padding-invalid")
        encoding["trailingPaddingSamples"] = 99
        self.invalid_package("sample record")
        encoding["trailingPaddingSamples"] = 1153
        self.invalid_package()
        encoding["trailingPaddingSamples"] = 100
        self.clip["audioDurationMs"] = 1000
        self.invalid_package("decoded sample record")

    def test_wrong_format_and_mismatched_or_escaping_media_paths(self):
        for key in ("file", "audioFile", "posterFile"):
            old = self.clip[key]
            for value in ("other.mp3", "../outside.mp3", "sub\\file.mp3", "C:\\outside.mp3", "https://invalid.test/file.mp3"):
                self.clip[key] = value
                with self.subTest(key=key, value=value):
                    self.invalid_package("matching bare filename")
            self.clip[key] = old
        self.scene["format"] = "gif"
        self.invalid_package("format")

    def test_gif_catalog_packages_without_renaming_or_reencoding(self):
        raw = b"GIF89a" + b"synthetic signature fixture"
        filename = f"{self.scene_id}.gif"
        (self.pairs / filename).write_bytes(raw)
        self.scene["format"] = self.catalog["format"] = "gif"
        self.clip["file"] = filename
        self.clip["visualBytes"] = len(raw)
        self.compile()
        self.assertEqual(
            (self.output / "assets" / "meme_courses" / self.course["id"] / filename).read_bytes(),
            raw,
        )
        self.assertFalse(list(self.output.rglob("*.webp")))

    def test_missing_empty_wrong_size_and_invalid_signatures(self):
        path = self.pairs / f"{self.scene_id}.mp3"
        original = path.read_bytes()
        for raw in (None, b"", b"wrong", b"BAD" + original[3:]):
            if raw is None:
                path.unlink()
            else:
                path.write_bytes(raw)
            with self.subTest(raw=raw):
                self.invalid_package("missing|size|signature")
        path.write_bytes(original)
        self.clip["audioBytes"] += 1
        self.invalid_package("size")

    def test_each_asset_budget_is_enforced(self):
        for key, filename, limit in (
            ("visualBytes", self.clip["file"], compiler.MAX_VISUAL_BYTES),
            ("audioBytes", self.clip["audioFile"], compiler.MAX_AUDIO_BYTES),
            ("posterBytes", self.clip["posterFile"], compiler.MAX_POSTER_BYTES),
        ):
            path = self.pairs / filename
            original = path.read_bytes()
            old_size = self.clip[key]
            path.write_bytes(b"x" * (limit + 1))
            self.clip[key] = limit + 1
            with self.subTest(key=key):
                self.invalid_package()
            path.write_bytes(original)
            self.clip[key] = old_size

    def test_output_allowlist_refuses_outside_and_protected_paths(self):
        for output in (
            self.work / "outside",
            self.repo / "assets" / "meme_courses" / "new-course",
            self.repo / "lib" / "new-output",
            self.repo / "build" / "web" / "new-output",
            self.repo / "build" / "other-preview",
            self.repo / "build" / "meme-course-work",
            self.session_files / "unapproved-output",
            self.session_files / "meme-course-work",
        ):
            self.output = output
            with self.subTest(output=output):
                self.invalid_package("outside/protected")
        self.assertFalse((self.repo / "assets").exists())
        self.assertFalse((self.repo / "build" / "web").exists())

    def test_session_artifact_and_repo_artifact_children_are_allowed(self):
        self.output = self.session_files / "meme-course-work" / "review-001"
        self.compile()
        self.assertTrue((self.output / "review-manifest.json").is_file())
        self.output = self.repo / "artifacts" / "meme-course-work" / "review-002"
        self.compile()
        self.assertTrue((self.output / "course.json").is_file())

    def test_path_traversal_is_refused_even_if_it_returns_to_an_allowed_root(self):
        self.output = self.output.parent / ".." / "meme-course-work" / "new"
        self.invalid_package("traversal")
        self.output = Path("\\\\server\\share\\package")
        self.invalid_package("UNC")

    def test_existing_output_even_empty_is_never_overwritten(self):
        self.output.mkdir(parents=True)
        self.write_inputs()
        with self.assertRaisesRegex(compiler.CompileError, "already exists"):
            compiler.compile_course(self.draft_path, self.catalog_path, self.output)
        self.assertEqual(list(self.output.iterdir()), [])
        sentinel = self.output / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(compiler.CompileError, "already exists"):
            compiler.compile_course(self.draft_path, self.catalog_path, self.output)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_completed_package_cannot_be_replaced(self):
        self.compile()
        before = (self.output / "course.json").read_bytes()
        self.course["title"] = "A changed draft"
        with self.assertRaisesRegex(compiler.CompileError, "already exists"):
            self.compile()
        self.assertEqual((self.output / "course.json").read_bytes(), before)

    def test_nested_repository_below_work_root_is_refused(self):
        self.output.parent.mkdir(parents=True)
        (self.output.parent / ".git").write_text("synthetic nested repository marker", encoding="utf-8")
        self.invalid_package("versioned repositories")

    def test_reparse_points_are_rejected_without_following_them(self):
        with mock.patch.object(compiler, "_is_reparse", return_value=True):
            self.invalid_package("symlink/junction")

    def test_source_symlink_to_an_outside_file_is_refused(self):
        path = self.pairs / self.clip["audioFile"]
        outside = self.work / "outside.mp3"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"OS does not permit creating test symlinks: {error}")
        self.invalid_package("symlink/junction")

    def test_output_ancestor_symlink_is_refused(self):
        target = self.work / "outside-output"
        target.mkdir()
        link = self.repo / "build"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"OS does not permit creating test symlinks: {error}")
        self.invalid_package("symlink/junction")
        self.assertEqual(list(target.iterdir()), [])

    def test_hard_linked_media_is_refused(self):
        source = self.pairs / self.clip["audioFile"]
        try:
            os.link(source, self.work / "alias.mp3")
        except OSError as error:
            self.skipTest(f"OS does not permit creating test hard links: {error}")
        self.invalid_package("hard-linked")

    def test_invalid_duplicate_json_keys_fail_before_staging(self):
        self.write_inputs()
        raw = self.draft_path.read_text(encoding="utf-8")
        self.draft_path.write_text(raw[:-1] + ', "kind": "memes"}', encoding="utf-8")
        with self.assertRaisesRegex(compiler.CompileError, "duplicate key"):
            compiler.compile_course(self.draft_path, self.catalog_path, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.parent.exists())

    def test_copy_failure_removes_stage_and_leaves_no_partial_package(self):
        original_copy = shutil.copyfile
        calls = 0

        def fail_after_one(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated disk failure")
            return original_copy(source, destination)

        with mock.patch.object(compiler.shutil, "copyfile", side_effect=fail_after_one):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.compile()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])

    def test_copy_mutation_is_detected_by_hash_not_just_size(self):
        original_copy = shutil.copyfile

        def mutate(source, destination):
            original_copy(source, destination)
            raw = destination.read_bytes()
            destination.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))

        with mock.patch.object(compiler.shutil, "copyfile", side_effect=mutate):
            self.invalid_package("changed after validation")
        self.assertEqual(list(self.output.parent.iterdir()), [])

    def test_atomic_rename_does_not_replace_a_racing_empty_destination(self):
        original_commit = compiler._commit_directory

        def collision(stage, output):
            output.mkdir()
            return original_commit(stage, output)

        with mock.patch.object(compiler, "_commit_directory", side_effect=collision):
            with self.assertRaises(OSError):
                self.compile()
        self.assertTrue(self.output.is_dir())
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(list(self.output.parent.glob(".meme-course-stage-*")), [])

    def test_cli_success_and_actionable_failure(self):
        self.write_inputs()
        arguments = [
            str(self.draft_path), "--media-catalog", str(self.catalog_path),
            "--output", str(self.output),
        ]
        with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(compiler.main(arguments), 0)
        self.assertIn("DRAFT meme_fixture_identity", stdout.getvalue())
        self.assertIn("Nothing published.", stdout.getvalue())
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(compiler.main(arguments), 1)
        self.assertIn("already exists", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
