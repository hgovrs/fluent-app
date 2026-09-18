#!/usr/bin/env python3
"""Validate and package a DRAFT meme English course for offline review only.

This standard-library tool copies existing paired media. It does not transcribe,
translate, generate audio, connect to services, or publish anything.
"""

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import uuid


ROOT = Path(__file__).resolve().parent.parent
SESSION_STATE_ROOT = Path.home() / ".copilot" / "session-state"
SOURCE_LIBRARY = ROOT / "assets" / "content" / "sources.json"
COURSE_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}")
SCENE_ID = re.compile(r"[a-z][a-z0-9_]{0,63}")
CONTENT_ID = re.compile(r"[a-z][a-z0-9_-]{0,159}")
SOURCE_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}")
SHA256 = re.compile(r"[0-9a-fA-F]{64}")
WINDOWS_RESERVED = re.compile(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])", re.I)
PUNCTUATION = re.compile(r"""[.,!?;:"“”'’¿¡]""")
TYPED_CONSTRAINT = re.compile(
    r"\bUse (?:(?P<english>one word|a listed phrase) from|"
    r"(?P<portuguese>uma destas palavras|uma destas expressões)):"
    r"\s*(?P<forms>.+)\.\s*$",
    re.I,
)
TRANSLATION_PROMPT = re.compile(
    r"\b(translat(?:e|ion)|English (?:version|equivalent|translation)|"
    r"tradu(?:za|zir|ção|cao)|vers[aã]o em ingl[eê]s|equivalente em ingl[eê]s)\b",
    re.I,
)
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_VISUAL_BYTES = 128 * 1024
MAX_POSTER_BYTES = 512 * 1024
MAX_AUDIO_BYTES = 2 * 1024 * 1024


class CompileError(ValueError):
    """Invalid draft, unsafe local path, or inconsistent paired media."""


def fail(where, message):
    raise CompileError(f"{where}: {message}")


def normalize(value):
    """Match Exercise.normalize in lib/models/course.dart, without editing text."""
    return re.sub(r"\s+", " ", PUNCTUATION.sub("", value.strip().lower()))


def _object(value, where, required=(), optional=()):
    if not isinstance(value, dict):
        fail(where, "expected an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing:
        fail(where, f"missing fields: {', '.join(sorted(missing))}")
    if unknown:
        fail(where, f"unsupported fields: {', '.join(sorted(unknown))}")
    return value


def _text(value, where, maximum=3000, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        fail(where, "expected nonempty text" if not allow_empty else "expected text")
    if len(value) > maximum or any(
        (ord(char) < 32 and char not in "\n\r\t") or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    ):
        fail(where, f"text exceeds {maximum} characters or contains invalid characters")
    return value


def _array(value, where, minimum=1, maximum=200):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        fail(where, f"expected an array with {minimum}..{maximum} items")
    return value


def _integer(value, where, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        fail(where, f"expected an integer in {minimum}..{maximum}")
    return value


def _number(value, where, minimum=0):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    if not valid:
        fail(where, f"expected a finite number >= {minimum}")
    return value


def _identifier(value, pattern, where):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        fail(where, "invalid ID")
    if WINDOWS_RESERVED.fullmatch(value):
        fail(where, "reserved filesystem name")
    return value


def _reject_comparison(value, where):
    if isinstance(value, dict):
        if "comparisonOnly" in value and value["comparisonOnly"] is not False:
            fail(where, "comparisonOnly input cannot be compiled")
        for key, child in value.items():
            _reject_comparison(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_comparison(child, f"{where}[{index}]")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("JSON", f"duplicate key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    fail("JSON", f"nonfinite number: {value}")


def _is_reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _local_path(value, where):
    path = Path(value).expanduser()
    if (
        str(path).startswith(("\\\\", "//"))
        or (path.drive and not path.is_absolute())
        or ".." in path.parts
    ):
        fail(where, "only local paths without traversal or UNC shares are allowed")
    for part in path.parts:
        if part == path.anchor:
            continue
        if (
            ":" in part
            or "\x00" in part
            or part.endswith((".", " "))
            or WINDOWS_RESERVED.fullmatch(part.split(".")[0])
        ):
            fail(where, "unsafe path component")
    path = Path(os.path.abspath(path))
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if _is_reparse(info):
            fail(where, f"symlink/junction/reparse point is not allowed: {candidate}")
    return path


def _read_json(value, where):
    path = _local_path(value, where)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_JSON_BYTES:
        fail(where, "JSON file must exist and contain 1 byte..4 MiB")
    raw = path.read_bytes()
    if not 0 < len(raw) <= MAX_JSON_BYTES:
        fail(where, "JSON file size changed while reading")
    data = json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=_invalid_constant,
    )
    _reject_comparison(data, where)
    return path, data, hashlib.sha256(raw).hexdigest()


def _known_source_ids():
    _, library, _ = _read_json(SOURCE_LIBRARY, "source library")
    if not isinstance(library, dict) or not isinstance(library.get("sources"), list):
        fail("source library", "expected a sources array")
    return {
        source["id"]
        for source in library["sources"]
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }


def _validate_exercise(exercise, where, scene_ids, register_id):
    _object(
        exercise, where,
        ("id", "type", "prompt", "answer", "explanation", "sceneId"),
        ("options", "acceptedAnswers", "englishReveal"),
    )
    register_id(exercise["id"], where)
    if exercise["type"] not in ("choice", "typed", "wordOrder"):
        fail(where, "type must be choice, typed, or wordOrder")
    if not isinstance(exercise["sceneId"], str) or exercise["sceneId"] not in scene_ids:
        fail(where, "sceneId must resolve to a declared scene")
    prompt = _text(exercise["prompt"], f"{where}.prompt")
    _text(exercise["explanation"], f"{where}.explanation")
    answer = _text(exercise["answer"], f"{where}.answer", 1000)
    accepted = _array(exercise.get("acceptedAnswers", []), where, 0, 16)
    answers = [answer] + [
        _text(item, f"{where}.acceptedAnswers", 1000) for item in accepted
    ]
    normalized_answers = [normalize(item) for item in answers]
    if not all(normalized_answers) or len(set(normalized_answers)) != len(answers):
        fail(where, "answers must be nonempty and distinct after runtime normalization")
    options = [
        _text(item, f"{where}.options", 1000)
        for item in _array(exercise.get("options", []), f"{where}.options", 0, 40)
    ]
    normalized_options = [normalize(item) for item in options]
    if not all(normalized_options):
        fail(where, "an option is empty after runtime normalization")
    reveal = exercise.setdefault("englishReveal", "afterAnswer")
    if reveal not in ("afterAnswer", "beforeAnswer"):
        fail(where, "englishReveal must be afterAnswer or beforeAnswer")
    if reveal == "beforeAnswer" and (
        exercise["type"] != "choice" or TRANSLATION_PROMPT.search(prompt)
    ):
        fail(where, "answer-production/translation questions need afterAnswer")

    if exercise["type"] == "choice":
        if not 2 <= len(options) <= 12 or len(set(normalized_options)) != len(options):
            fail(where, "choice requires 2..12 distinct normalized options")
        if normalized_options.count(normalized_answers[0]) != 1 or sum(
            option in normalized_answers for option in normalized_options
        ) != 1:
            fail(where, "exactly one normalized choice must be correct")
    elif exercise["type"] == "wordOrder":
        if not options or any(" " in option for option in normalized_options):
            fail(where, "wordOrder options must be individual nonempty tokens")
        for candidate in normalized_answers:
            if Counter(candidate.split(" ")) != Counter(normalized_options):
                fail(where, "wordOrder tokens must match every accepted answer")
    else:
        constraint = TYPED_CONSTRAINT.search(prompt)
        if options or prompt.count("___") != 1 or not constraint:
            fail(
                where,
                "typed needs one ___ blank, no options, and an ending "
                "'Use uma destas palavras/expressões: a | b.' "
                "or the supported legacy English word/phrase list",
            )
        candidates = [normalize(item) for item in constraint["forms"].split("|")]
        if (
            not 2 <= len(candidates) <= 20
            or not all(candidates)
            or len(set(candidates)) != len(candidates)
            or any(len(item.split(" ")) > 12 for item in candidates)
        ):
            fail(where, "typed candidate list must contain 2..20 distinct short forms")
        one_word = (constraint["english"] or "").lower() == "one word" or (
            constraint["portuguese"] or ""
        ).lower() == "uma destas palavras"
        if one_word and any(
            " " in item for item in candidates
        ):
            fail(where, "'one word' candidates must each be one normalized word")
        if any(candidate not in candidates for candidate in normalized_answers):
            fail(where, "typed answer and every accepted variant must be explicitly listed")


def validate_course(data, known_source_ids=None):
    """Return a validated copy, retaining authored text and draft status.

    Language, translation quality, factual wording and semantic uniqueness still
    require a human; syntactic validity cannot certify any of those properties.
    """
    _reject_comparison(data, "course")
    course = copy.deepcopy(_object(
        data, "course",
        ("id", "title", "sourceLanguage", "targetLanguage", "level", "coverage",
         "contentVersion", "kind", "editorialStatus", "scenes", "units"),
        ("englishLocale", "contentWarning"),
    ))
    course_id = _identifier(course["id"], COURSE_ID, "course.id")
    if course_id.startswith("en-"):
        fail("course.id", "the traditional en-* namespace is protected")
    if course["kind"] != "memes" or course["editorialStatus"] != "draft":
        fail("course", "this local workflow accepts only kind=memes, editorialStatus=draft")
    if course["sourceLanguage"] != "pt-BR" or course["targetLanguage"] != "en":
        fail("course", "this bilingual workflow uses sourceLanguage=pt-BR, targetLanguage=en")
    if course.setdefault("englishLocale", "en-US") not in ("en-US", "en-GB"):
        fail("course.englishLocale", "choose en-US or en-GB")
    for key in ("title", "level"):
        _text(course[key], f"course.{key}", 200)
    _text(course["coverage"], "course.coverage")
    _text(course.setdefault("contentWarning", ""), "course.contentWarning", allow_empty=True)
    _integer(course["contentVersion"], "course.contentVersion", 1, 2**31 - 1)

    all_ids = {course_id}
    scene_ids = set()
    for scene in _array(course["scenes"], "course.scenes", 1, 100):
        _object(scene, "scene", ("id", "title", "format", "durationMs", "adaptationNotes", "cues"))
        scene_id = _identifier(scene["id"], SCENE_ID, "scene.id")
        if scene_id in all_ids:
            fail(scene_id, "duplicate ID")
        all_ids.add(scene_id)
        scene_ids.add(scene_id)
        _text(scene["title"], f"{scene_id}.title", 200)
        _text(scene["adaptationNotes"], f"{scene_id}.adaptationNotes")
        if scene["format"] not in ("webp", "gif"):
            fail(scene_id, "format must be webp or gif")
        duration = _integer(scene["durationMs"], scene_id, 1, 30000)
        previous_end = 0
        for cue in _array(scene["cues"], f"{scene_id}.cues", 1, 200):
            _object(cue, f"{scene_id}.cue", ("startMs", "endMs", "pt", "en"))
            start = _integer(cue["startMs"], scene_id, 0, duration - 1)
            end = _integer(cue["endMs"], scene_id, 1, duration)
            if start < previous_end or end <= start:
                fail(scene_id, "cues must be ordered, nonoverlapping and within the clip")
            previous_end = end
            _text(cue["pt"], f"{scene_id}.cue.pt", 1000)
            _text(cue["en"], f"{scene_id}.cue.en", 1000)

    def register_id(value, where):
        value = _identifier(value, CONTENT_ID, f"{where}.id")
        if not value.startswith(f"{course_id}_"):
            fail(where, "unit, lesson and exercise IDs must use the courseId_ namespace")
        if value in all_ids:
            fail(where, "duplicate ID")
        all_ids.add(value)

    references = set()
    used_scenes = set()
    for unit in _array(course["units"], "course.units", 1, 100):
        _object(unit, "unit", ("id", "title", "description", "lessons"))
        register_id(unit["id"], "unit")
        _text(unit["title"], "unit.title", 200)
        _text(unit["description"], "unit.description")
        for lesson in _array(unit["lessons"], "unit.lessons", 1, 100):
            _object(
                lesson, "lesson", ("id", "title", "description", "studyNotes", "exercises"),
                ("readingPassage", "sourceIds"),
            )
            register_id(lesson["id"], "lesson")
            _text(lesson["title"], "lesson.title", 200)
            _text(lesson["description"], "lesson.description")
            _text(lesson["studyNotes"], "lesson.studyNotes", 12000)
            if "readingPassage" in lesson:
                _text(lesson["readingPassage"], "lesson.readingPassage", 12000)
            source_ids = _array(lesson.get("sourceIds", []), "lesson.sourceIds", 0, 40)
            for source in source_ids:
                _identifier(source, SOURCE_ID, "lesson.sourceIds")
            if len(set(source_ids)) != len(source_ids):
                fail("lesson.sourceIds", "duplicate reference")
            references.update(source_ids)
            for exercise in _array(lesson["exercises"], "lesson.exercises", 1, 200):
                _validate_exercise(exercise, "exercise", scene_ids, register_id)
                used_scenes.add(exercise["sceneId"])
    if used_scenes != scene_ids:
        fail("course.scenes", "every packaged scene must be used by an exercise")
    if references:
        known = _known_source_ids() if known_source_ids is None else set(known_source_ids)
        if references - known:
            fail("lesson.sourceIds", f"unknown references: {', '.join(sorted(references - known))}")
    return course


def _signature(data, suffix, where):
    if suffix == ".webp":
        valid = (
            len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
            and int.from_bytes(data[4:8], "little") + 8 == len(data)
        )
    elif suffix == ".gif":
        valid = data.startswith((b"GIF87a", b"GIF89a"))
    elif suffix == ".png":
        valid = data.startswith(b"\x89PNG\r\n\x1a\n")
    else:
        valid = data.startswith(b"ID3") or (
            len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
        )
    if not valid:
        fail(where, f"file signature is inconsistent with {suffix}")


def _media_file(path, declared_bytes, maximum, suffix, where):
    path = _local_path(path, where)
    if not path.is_file():
        fail(where, "missing media file")
    info = path.stat()
    if info.st_nlink != 1:
        fail(where, "hard-linked media files are not allowed")
    _integer(declared_bytes, f"{where}.bytes", 1, maximum)
    if not 0 < info.st_size <= maximum or info.st_size != declared_bytes:
        fail(where, "actual media size differs from its byte record or exceeds the limit")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) != declared_bytes:
        fail(where, "media size changed while reading")
    _signature(data, suffix, where)
    return path, hashlib.sha256(data).hexdigest(), len(data)


def validate_media(course, catalog, catalog_path):
    """Check pair provenance records, sizes and signatures, not decoded speech."""
    _reject_comparison(catalog, "media catalog")
    if not isinstance(catalog, dict) or type(catalog.get("schemaVersion")) is not int:
        fail("media catalog", "expected a schemaVersion=1 object")
    if catalog["schemaVersion"] != 1 or catalog.get("clipAudio") is not True:
        fail("media catalog", "requires schemaVersion=1 and original clipAudio=true")
    if not isinstance(catalog.get("sourceSha256"), str) or not SHA256.fullmatch(catalog["sourceSha256"]):
        fail("media catalog", "sourceSha256 must identify the original video")
    source_duration = _number(catalog.get("sourceDuration"), "sourceDuration", 0.001)
    if catalog.get("format") not in ("webp", "gif"):
        fail("media catalog", "format must be webp or gif")
    clips = {}
    for clip in _array(catalog.get("clips"), "media catalog.clips", 1, 1000):
        if not isinstance(clip, dict):
            fail("media catalog.clips", "each clip must be an object")
        clip_id = _identifier(clip.get("id"), SCENE_ID, "media clip.id")
        if clip_id in clips:
            fail(clip_id, "duplicate catalog clip ID")
        clips[clip_id] = clip

    files, scene_records = [], []
    for scene in course["scenes"]:
        scene_id = scene["id"]
        if scene_id not in clips:
            fail(scene_id, "scene has no paired clip in the media catalog")
        clip = clips[scene_id]
        if scene["format"] != catalog["format"]:
            fail(scene_id, "scene format does not match the paired catalog")
        duration = _integer(clip.get("durationMs"), scene_id, 1, 30000)
        start = _number(clip.get("start"), f"{scene_id}.start")
        end = _number(clip.get("end"), f"{scene_id}.end")
        if (
            end <= start or end > source_duration + 0.001
            or not math.isclose((end - start) * 1000, duration, abs_tol=1, rel_tol=0)
            or scene["durationMs"] != duration
        ):
            fail(scene_id, "source interval, course and catalog durations must match")
        visual_duration = _number(clip.get("visualDurationMs"), f"{scene_id}.visualDurationMs", 0.001)
        if not math.isclose(visual_duration, duration, abs_tol=1, rel_tol=0):
            fail(scene_id, "visualDurationMs does not match the paired interval")
        encoding = clip.get("audioEncoding")
        if not isinstance(encoding, dict) or encoding.get("codec") != "mp3":
            fail(scene_id, "original MP3 audioEncoding record is required")
        rate = _integer(encoding.get("sampleRate"), scene_id, 8000, 192000)
        samples = _integer(encoding.get("decodedSamples"), scene_id, 1, 192000 * 30 + 1152)
        source_samples = _integer(encoding.get("sourceSamples"), scene_id, 1, 192000 * 30)
        padding = _integer(encoding.get("trailingPaddingSamples", 0), scene_id, 0, 1152)
        audio_duration = _number(clip.get("audioDurationMs"), f"{scene_id}.audioDurationMs", 0.001)
        if samples - source_samples != padding or not math.isclose(
            source_samples * 1000 / rate, duration, abs_tol=1, rel_tol=0
        ):
            fail(scene_id, "audio sample record does not match the source interval")
        if not math.isclose(audio_duration, samples * 1000 / rate, abs_tol=1, rel_tol=0):
            fail(scene_id, "audioDurationMs does not match the decoded sample record")
        for key, byte_key, suffix, maximum, role in (
            ("file", "visualBytes", f'.{scene["format"]}', MAX_VISUAL_BYTES, "animation"),
            ("audioFile", "audioBytes", ".mp3", MAX_AUDIO_BYTES, "originalAudio"),
            ("posterFile", "posterBytes", ".png", MAX_POSTER_BYTES, "poster"),
        ):
            filename = f"{scene_id}{suffix}"
            if clip.get(key) != filename:
                fail(scene_id, f"{key} must be the matching bare filename {filename}")
            path, digest, size = _media_file(
                catalog_path.parent / filename, clip.get(byte_key), maximum, suffix,
                f"{scene_id}.{key}",
            )
            relative = Path("assets") / "meme_courses" / course["id"] / filename
            files.append({
                "source": path, "relative": relative, "sha256": digest, "bytes": size,
                "sceneId": scene_id, "role": role,
            })
        scene_records.append({
            "id": scene_id, "sourceStartSeconds": start, "sourceEndSeconds": end,
            "durationMs": duration, "cueCount": len(scene["cues"]),
            "audioSourceDurationMs": source_samples * 1000 / rate,
            "audioDecodedDurationMs": audio_duration,
            "audioTrailingPaddingSamples": padding,
            "transcriptStatus": "draft-unverified", "cueTimingStatus": "pending-review",
            "adaptationNotes": scene["adaptationNotes"],
        })
    return files, scene_records


def checked_output(value):
    output = _local_path(value, "output")
    root = _local_path(ROOT, "repository")
    allowed_roots = [
        root / "build" / "meme-course-work",
        root / "artifacts" / "meme-course-work",
    ]
    session_root = _local_path(SESSION_STATE_ROOT, "session artifact root")
    if output.is_relative_to(session_root):
        parts = output.relative_to(session_root).parts
        if (
            len(parts) >= 4
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", parts[0])
            and parts[1:3] == ("files", "meme-course-work")
            and (session_root / parts[0] / "files").is_dir()
        ):
            allowed_roots.append(session_root / parts[0] / "files" / "meme-course-work")
    allowed = next(
        (candidate for candidate in allowed_roots
         if output != candidate and output.is_relative_to(candidate)),
        None,
    )
    if allowed is None:
        fail(
            "output",
            "use a NEW child of build\\meme-course-work, artifacts\\meme-course-work, "
            "or an existing Copilot session's files\\meme-course-work; "
            "outside/protected repository paths are refused",
        )
    for parent in (output.parent, *output.parent.parents):
        if not parent.is_relative_to(allowed):
            break
        if os.path.lexists(parent / ".git"):
            fail("output", "nested versioned repositories are protected")
    if os.path.lexists(output):
        fail("output", "destination already exists; nothing is overwritten")
    return output


def _commit_directory(stage, output):
    """Atomic no-replace promotion, including an empty competing directory."""
    if os.name == "nt":
        os.rename(stage, output)
        return
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        operation = libc.renameat2
        operation.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,
        ]
        operation.restype = ctypes.c_int
        result = operation(-100, os.fsencode(stage), -100, os.fsencode(output), 1)
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        operation = libc.renamex_np
        operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        result = operation(os.fsencode(stage), os.fsencode(output), 4)
    else:
        fail("output", "this platform has no supported atomic no-overwrite directory rename")
    if result:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(output))


def _write_json(path, data):
    raw = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
    return {"path": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def compile_course(draft_json, media_catalog, output):
    output = checked_output(output)
    _, draft, draft_hash = _read_json(draft_json, "draft")
    catalog_path, catalog, catalog_hash = _read_json(media_catalog, "media catalog")
    course = validate_course(draft)
    files, scene_records = validate_media(course, catalog, catalog_path)
    lessons = [lesson for unit in course["units"] for lesson in unit["lessons"]]
    exercises = [exercise for lesson in lessons for exercise in lesson["exercises"]]
    manifest = {
        "schemaVersion": 1, "courseId": course["id"], "kind": "memes",
        "editorialStatus": "draft", "localOnly": True, "reviewRequired": True,
        "publicationApproved": False, "originalVideoIncluded": False,
        "sourceSha256": catalog["sourceSha256"].lower(),
        "sourceHashEvidence": "declared by paired media catalog; original video not read",
        "draftSha256": draft_hash, "mediaCatalogSha256": catalog_hash,
        "reviewFlags": {
            "transcriptAndCueTiming": "pending-human-review",
            "speakerIdentity": "unverified-do-not-infer",
            "englishAdaptationAndSeverity": "pending-human-review",
            "englishOnlyPedagogyAndSemanticAnswerUniqueness": "pending-human-review",
            "pairedPlaybackAndDecodedMedia": "pending-local-review",
            "optInAndContentWarning": "pending-local-review",
            "publication": "blocked-until-fresh-explicit-approval-after-local-review",
        },
        "mediaVerification": "filenames, byte counts, signatures, hashes and duration/sample records; no decoding",
        "counts": {
            "scenes": len(course["scenes"]), "units": len(course["units"]),
            "lessons": len(lessons), "exercises": len(exercises), "mediaFiles": len(files),
            "exerciseTypes": dict(Counter(exercise["type"] for exercise in exercises)),
        },
        "scenes": scene_records,
        "files": [],
        "perFileSHA256": {},
        "hashScope": "course.json and all packaged media; this manifest excludes its own hash",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    checked_output(output)
    stage = output.parent / f".meme-course-stage-{uuid.uuid4().hex[:16]}"
    stage.mkdir(mode=0o700)
    try:
        manifest["files"].append(_write_json(stage / "course.json", course))
        for item in files:
            source = _local_path(item["source"], "source before copy")
            destination = stage / item["relative"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            actual = destination.read_bytes()
            if len(actual) != item["bytes"] or hashlib.sha256(actual).hexdigest() != item["sha256"]:
                fail(str(source), "media changed after validation; package discarded")
            manifest["files"].append({
                "path": item["relative"].as_posix(), "bytes": item["bytes"],
                "sha256": item["sha256"], "sceneId": item["sceneId"], "role": item["role"],
            })
        manifest["perFileSHA256"] = {
            item["path"]: item["sha256"] for item in manifest["files"]
        }
        _write_json(stage / "review-manifest.json", manifest)
        checked_output(output)
        _commit_directory(stage, output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft_json", type=Path)
    parser.add_argument("--media-catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = compile_course(args.draft_json, args.media_catalog, args.output)
    except (OSError, ValueError, UnicodeError, RecursionError) as error:
        print(f"Draft not compiled: {error}", file=sys.stderr)
        return 1
    counts = manifest["counts"]
    print(
        f'DRAFT {manifest["courseId"]}: {counts["scenes"]} scenes, '
        f'{counts["lessons"]} lessons, {counts["exercises"]} exercises.\n'
        f"Local package: {Path(os.path.abspath(args.output))}\n"
        "Human review required. Nothing published."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
