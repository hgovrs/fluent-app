#!/usr/bin/env python3
"""Generate optional English scene audio with an existing voice.

By default, this CLI delegates to run_meme_english_audio.py and its GitHub-backed
credential path. Only explicit --local runs the engine below; there is no
automatic local fallback or API-key prompt in the default route.

Examples (PowerShell):
  python tool\\generate_meme_english_audio.py course-draft.json --output build\\meme-course-work\\english --dry-run
  python tool\\generate_meme_english_audio.py --local course-draft.json --output build\\meme-course-work\\english --voice-id YOUR_VOICE_ID --generate --allow-draft

Prefer the authored course-draft.json as input. Any existing englishAudio
metadata must pass duration, shape and exact English-text-hash validation.
export_english_request(course_path) returns an English-only request dictionary
for a separate dispatcher; it reads the supplied course but never writes files,
accesses credentials, or connects to services. This CLI also accepts that strict
meme_english_tts_request JSON directly. Keep the input outside the new output
directory. Neither Portuguese captions nor source media belong in that request.
Local mode prompts for voice IDs when omitted. Local keys come only from ELEVENLABS_API_KEY,
or an explicitly requested hidden terminal prompt (--prompt-api-key). There are
no retries of billable POSTs. --resume reuses verified downloads; after an
interrupted/failed request, --retry-ambiguous explicitly accepts possible repeat
billing. A stale .english-generation.lock requires manual inspection/removal
after verifying that its process has stopped.

Outputs: <sceneId>.en.mp3, english-audio-catalog.json, and private
generation-state.json. Full-course input also produces course-with-english.json;
English-only input never fabricates a runtime course. Incomplete catalogs cannot
be compiled.
Each MP3 speaks exactly the scene's trimmed English cues joined with one space.
Identical text in this batch shares one paid request, not a shared runtime path.
The saved source-course hash is provenance only. Resumption binds the course/
scene IDs, English text, voice and request settings, not JSON formatting or the
addition of matching English metadata by the compiler.

English audio is synthetic, not synchronized to the original Portuguese video.
Human listening/editorial review is still required. The local engine never
publishes, changes source files, uploads source media, or modifies the remote voice.
"""

import argparse
import copy
from dataclasses import dataclass, field
import getpass
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
import warnings

sys.dont_write_bytecode = True

if __package__:
    from . import compile_meme_course as compiler
else:
    import compile_meme_course as compiler


DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_64"
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 1.0,
}
MODEL_ID = DEFAULT_MODEL_ID
OUTPUT_FORMAT = DEFAULT_OUTPUT_FORMAT
VOICE_SETTINGS = dict(DEFAULT_VOICE_SETTINGS)
API_HOST = "api.elevenlabs.io"
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_DURATION_MS = 60000
MAX_TEXT_CHARACTERS = 10000
REQUEST_TIMEOUT = 60
ENGLISH_REQUEST_KIND = "meme_english_tts_request"
VOICE_ID = re.compile(r"[A-Za-z0-9]{20,64}")
ANNOTATION_MARKER = re.compile(r"[\[\]{}<>]|(?<!\S)\?{2,}(?!\S)|\ufffd")
REVIEW_MARKER = re.compile(
    r"^\s*(?:TODO|TBD|FIXME)(?=\s*(?:[:\-—]|translate\b|translation\b|$))", re.I,
)
STATE_FILE = "generation-state.json"
CATALOG_FILENAME = "english-audio-catalog.json"
CATALOG_FILE = CATALOG_FILENAME
COURSE_FILE = "course-with-english.json"
LOCK_FILE = ".english-generation.lock"


class GenerationError(ValueError):
    """A safe, non-provider error message that contains no credentials."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal unknown-argument message can echo a misplaced key.
        raise GenerationError(
            "Invalid arguments. Use --help. API keys must not be CLI arguments."
        )


@dataclass(frozen=True)
class SceneText:
    scene_id: str
    text: str
    text_sha256: str

    @property
    def filename(self):
        return f"{self.scene_id}.en.mp3"


@dataclass(frozen=True)
class EnglishInput:
    course_id: str
    editorial_status: str
    scenes: tuple[SceneText, ...]
    source_sha256: str
    course: dict | None = field(default=None, repr=False)


@dataclass(frozen=True)
class SynthesisRequest:
    voice_id: str
    text: str
    api_key: str = field(repr=False)

    @property
    def path(self):
        if not VOICE_ID.fullmatch(self.voice_id):
            raise GenerationError("Invalid ElevenLabs voice ID.")
        return f"/v1/text-to-speech/{self.voice_id}?output_format={OUTPUT_FORMAT}"

    @property
    def body(self):
        # multilingual_v2 does NOT support language_code. English input controls
        # the language; these settings affect this request, not the saved voice.
        return {
            "text": self.text,
            "model_id": MODEL_ID,
            "voice_settings": dict(VOICE_SETTINGS),
        }

    @property
    def headers(self):
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json_bytes(data):
    return (json.dumps(
        data, ensure_ascii=False, allow_nan=False, indent=2,
    ) + "\n").encode("utf-8")


def _canonical(data):
    return json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True)


def _read_regular(path, maximum):
    path = compiler._local_path(path, "local file")
    if not path.is_file():
        raise GenerationError("A required local file is missing.")
    info = path.stat()
    if info.st_nlink != 1 or not 0 < info.st_size <= maximum:
        raise GenerationError("Linked, empty, or oversized local files are refused.")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if opened.st_nlink != 1 or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise GenerationError("A local file changed during verification.")
        raw = stream.read(maximum + 1)
    if len(raw) != info.st_size:
        raise GenerationError("A local file changed during verification.")
    return raw


def _decode_json(raw):
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=compiler._unique_object,
        parse_constant=compiler._invalid_constant,
    )


def load_course(path):
    raw = _read_regular(path, compiler.MAX_JSON_BYTES)
    return _validate_course_document(_decode_json(raw), _sha(raw))


def _validate_course_document(source, source_hash):
    if not isinstance(source, dict) or source.get("editorialStatus") not in ("draft", "reviewed"):
        raise GenerationError("The input must be a draft or reviewed meme course.")
    candidate = copy.deepcopy(source)
    status = candidate["editorialStatus"]
    candidate["editorialStatus"] = "draft"
    prior_audio = {}
    if isinstance(candidate.get("scenes"), list):
        for index, scene in enumerate(candidate["scenes"]):
            if isinstance(scene, dict) and "englishAudio" in scene:
                prior_audio[index] = scene.pop("englishAudio")
    course = compiler.validate_course(candidate)
    course["editorialStatus"] = status
    scenes = []
    for index, scene in enumerate(course["scenes"]):
        for cue in scene["cues"]:
            if (
                ANNOTATION_MARKER.search(cue["en"])
                or ANNOTATION_MARKER.search(cue["pt"])
                or REVIEW_MARKER.search(cue["en"])
            ):
                raise GenerationError(
                    f"Scene {scene['id']} has placeholder/annotation cues. "
                    "Review both captions before synthesis; no scenes may be omitted."
                )
        text = " ".join(cue["en"].strip() for cue in scene["cues"])
        if not 0 < len(text) <= MAX_TEXT_CHARACTERS:
            raise GenerationError("A scene exceeds the supported English text limit.")
        text_hash = _sha(text.encode("utf-8"))
        if index in prior_audio:
            audio = compiler._object(
                prior_audio[index], "englishAudio", ("durationMs", "textSha256"),
            )
            compiler._integer(audio["durationMs"], "englishAudio.durationMs", 1, MAX_DURATION_MS)
            if audio["textSha256"] != text_hash:
                raise GenerationError("Existing English metadata is stale; review the source course.")
        scenes.append(SceneText(scene["id"], text, text_hash))
    return course, scenes, source_hash


def export_english_request(course_path):
    """Read/validate the supplied course and return data, never files or requests."""
    course, scenes, source_hash = load_course(course_path)
    return {
        "schemaVersion": 1,
        "kind": ENGLISH_REQUEST_KIND,
        "courseId": course["id"],
        "sourceCourseSha256": source_hash,
        "editorialStatus": "draft",
        "language": "en",
        "scenes": [
            {"id": scene.scene_id, "text": scene.text, "textSha256": scene.text_sha256}
            for scene in scenes
        ],
    }


def _validate_english_request(source):
    compiler._object(
        source, "English request",
        ("schemaVersion", "kind", "courseId", "sourceCourseSha256", "editorialStatus", "language", "scenes"),
    )
    compiler._integer(source["schemaVersion"], "English request schemaVersion", 1, 1)
    if (
        source["kind"] != ENGLISH_REQUEST_KIND
        or source["editorialStatus"] != "draft"
        or source["language"] != "en"
    ):
        raise GenerationError("English-only requests require the supported kind, editorialStatus=draft, and language=en.")
    course_id = compiler._identifier(source["courseId"], compiler.COURSE_ID, "English request courseId")
    if course_id.startswith("en-"):
        raise GenerationError("The traditional en-* course namespace is protected.")
    source_hash = source["sourceCourseSha256"]
    if not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise GenerationError("English requests require a valid source-course provenance hash.")
    scenes = []
    identifiers = {course_id}
    for scene in compiler._array(source["scenes"], "English request scenes", 1, 100):
        compiler._object(scene, "English request scene", ("id", "text", "textSha256"))
        scene_id = compiler._identifier(scene["id"], compiler.SCENE_ID, "English request scene ID")
        if scene_id in identifiers:
            raise GenerationError("English request scene IDs must be distinct.")
        identifiers.add(scene_id)
        text = compiler._text(scene["text"], "English request text", MAX_TEXT_CHARACTERS)
        if text != text.strip() or ANNOTATION_MARKER.search(text) or REVIEW_MARKER.search(text):
            raise GenerationError("English request text must be exact, trimmed, reviewed speech without placeholder annotations.")
        text_hash = _sha(text.encode("utf-8"))
        if scene["textSha256"] != text_hash:
            raise GenerationError("English request textSha256 does not match the exact UTF-8 text.")
        scenes.append(SceneText(scene_id, text, text_hash))
    return EnglishInput(course_id, "draft", tuple(scenes), source_hash)


def load_input(path):
    raw = _read_regular(path, compiler.MAX_JSON_BYTES)
    source = _decode_json(raw)
    if isinstance(source, dict) and source.get("kind") == ENGLISH_REQUEST_KIND:
        return _validate_english_request(source)
    course, scenes, source_hash = _validate_course_document(source, _sha(raw))
    return EnglishInput(
        course["id"], course["editorialStatus"], tuple(scenes), source_hash, course,
    )


def _has_mp3_header(raw):
    if not 10 <= len(raw) <= MAX_AUDIO_BYTES:
        return False
    id3 = raw[:3] == b"ID3" and 2 <= raw[3] <= 4
    frame = (
        raw[0] == 0xFF and raw[1] & 0xE0 == 0xE0
        and raw[1] & 0x18 != 0x08 and raw[1] & 0x06 == 0x02
        and raw[2] & 0xF0 not in (0, 0xF0) and raw[2] & 0x0C != 0x0C
    )
    return id3 or frame


def read_synthesis_response(response, *, deadline, set_timeout=lambda _: None):
    if response.status != 200:
        raise GenerationError("ElevenLabs rejected the request; no automatic retry was attempted.")
    headers = {}
    for name, value in response.getheaders():
        headers.setdefault(name.lower(), []).append(value.strip())
    types = headers.get("content-type", [])
    if len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "audio/mpeg":
        raise GenerationError("ElevenLabs returned an unexpected audio type.")
    lengths = headers.get("content-length", [])
    if len(lengths) > 1 or (lengths and not re.fullmatch(r"[0-9]+", lengths[0])):
        raise GenerationError("ElevenLabs returned an invalid audio length.")
    length = int(lengths[0]) if lengths else None
    if length is not None and not 10 <= length <= MAX_AUDIO_BYTES:
        raise GenerationError("Audio is empty or exceeds the size limit.")
    transfer = headers.get("transfer-encoding", [])
    encoding = headers.get("content-encoding", [])
    if (
        (transfer and (len(transfer) != 1 or transfer[0].lower() != "chunked" or lengths))
        or (encoding and (len(encoding) != 1 or encoding[0].lower() != "identity"))
    ):
        raise GenerationError("ElevenLabs returned an unsupported audio encoding.")
    data = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GenerationError("Synthesis timed out; the request may have been billed.")
        set_timeout(remaining)
        chunk = response.read(min(65536, MAX_AUDIO_BYTES + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_AUDIO_BYTES:
            raise GenerationError("Audio exceeds the size limit.")
    if length is not None and len(data) != length:
        raise GenerationError("ElevenLabs returned an incomplete audio response.")
    if not _has_mp3_header(data):
        raise GenerationError("ElevenLabs returned an invalid MP3 response.")
    return bytes(data)


def synthesize_with_elevenlabs(request):
    connection = http.client.HTTPSConnection(API_HOST, timeout=15)
    deadline = time.monotonic() + REQUEST_TIMEOUT
    try:
        connection.connect()
        transport_socket = connection.sock
        transport_socket.settimeout(max(0.001, deadline - time.monotonic()))
        connection.request(
            "POST", request.path,
            body=json.dumps(request.body, ensure_ascii=False).encode("utf-8"),
            headers=request.headers,
        )
        response = connection.getresponse()
        return read_synthesis_response(
            response, deadline=deadline, set_timeout=transport_socket.settimeout,
        )
    except GenerationError:
        raise
    except Exception:
        # Transport exceptions and provider bodies/headers may contain secrets.
        raise GenerationError(
            "Synthesis failed or timed out; the request may have been billed. No automatic retry."
        ) from None
    finally:
        connection.close()


def probe_mp3(raw):
    """Decode frame sample counts locally, without writing a temporary file."""
    if not _has_mp3_header(raw):
        raise GenerationError("Empty, oversized, or invalid MP3 response.")
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-protocol_whitelist", "pipe",
                "-show_entries", "frame=nb_samples:stream=codec_name,sample_rate,channels",
                "-of", "json", "-i", "pipe:0",
            ],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
        if result.returncode != 0 or result.stderr.strip() or len(result.stdout) > compiler.MAX_JSON_BYTES:
            raise ValueError()
        metadata = _decode_json(result.stdout)
        streams = metadata["streams"]
        if len(streams) != 1:
            raise ValueError()
        stream = streams[0]
        if (
            stream["codec_name"] != "mp3" or stream["sample_rate"] != "44100"
            or type(stream["channels"]) is not int or stream["channels"] not in (1, 2)
        ):
            raise ValueError()
        frames = metadata["frames"]
        if not frames or any(type(frame.get("nb_samples")) is not int or frame["nb_samples"] <= 0 for frame in frames):
            raise ValueError()
        samples = sum(frame["nb_samples"] for frame in frames)
        if not 0 < samples <= 44100 * 60:
            raise ValueError()
        return max(1, (samples * 1000 + 22050) // 44100)
    except Exception:
        raise GenerationError(
            "MP3 decoding failed or exceeded 60 seconds. Verify ffprobe and review the audio before retrying."
        ) from None


def require_ffprobe():
    if shutil.which("ffprobe") is None:
        raise GenerationError("Install FFmpeg/ffprobe on PATH before paid synthesis; no request was sent.")
    try:
        result = subprocess.run(
            ["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False,
        )
        if result.returncode != 0 or not result.stdout.startswith(b"ffprobe version"):
            raise ValueError()
    except Exception:
        raise GenerationError("ffprobe could not run. Repair the local decoder before paid synthesis; nothing was sent.") from None


def _checked_output(value, resume):
    output = compiler._local_path(value, "output")
    if os.path.lexists(output):
        if not resume or not output.is_dir():
            raise GenerationError("Output exists; use --resume only for this generator's matching batch.")
        # A new sibling exercises the compiler's unchanged root/ancestor policy.
        compiler.checked_output(output.with_name(f".english-path-check-{uuid.uuid4().hex}"))
        if os.path.lexists(output / ".git"):
            raise GenerationError("Nested versioned repositories are protected.")
        return output
    if resume:
        raise GenerationError("--resume needs an existing matching English-audio output directory.")
    return compiler.checked_output(output)


class _Journal:
    def __init__(self, output):
        self.output = output
        self.hashes = {}

    def read(self, name):
        raw = _read_regular(self.output / name, compiler.MAX_JSON_BYTES)
        self.hashes[name] = _sha(raw)
        return _decode_json(raw)

    def _check_owned(self, name):
        path = compiler._local_path(self.output / name, "output metadata")
        if os.path.lexists(path):
            raw = _read_regular(path, compiler.MAX_JSON_BYTES)
            if self.hashes.get(name) != _sha(raw):
                raise GenerationError("Output metadata changed or belongs to another batch; nothing is overwritten.")
        elif name in self.hashes:
            raise GenerationError("Output metadata disappeared; nothing is overwritten.")
        return path

    def write(self, name, data):
        raw = _json_bytes(data)
        if len(raw) > compiler.MAX_JSON_BYTES:
            raise GenerationError("Generated metadata exceeds the local JSON limit.")
        destination = self._check_owned(name)
        stage = compiler._local_path(
            self.output / f".{name}.writing-{uuid.uuid4().hex}", "metadata staging",
        )
        try:
            with stage.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self._check_owned(name)
            if name in self.hashes:
                os.replace(stage, destination)
            else:
                compiler._commit_directory(stage, destination)
            self.hashes[name] = _sha(raw)
        finally:
            if stage.exists():
                compiler._local_path(stage, "metadata staging cleanup").unlink()


def _configuration(course, voice_id):
    return {
        "schemaVersion": 1,
        "courseId": course if isinstance(course, str) else course["id"],
        "language": "en",
        "voiceId": voice_id, "modelId": MODEL_ID, "outputFormat": OUTPUT_FORMAT,
        "voiceSettings": dict(VOICE_SETTINGS),
    }


def _fingerprint(configuration, scenes, *, legacy_source_hash=None):
    binding = {
        **configuration,
        "scenes": [{"sceneId": scene.scene_id, "textSha256": scene.text_sha256} for scene in scenes],
    }
    if legacy_source_hash is not None:
        binding["sourceCourseSha256"] = legacy_source_hash
    return _sha(_canonical(binding).encode("utf-8"))


def _initial_state(fingerprint, source_hash, scenes):
    return {
        "schemaVersion": 1, "generator": "meme-english-audio",
        "fingerprint": fingerprint, "sourceCourseSha256": source_hash,
        "status": "incomplete",
        "requests": {
            scene.text_sha256: {"status": "pending", "attempts": 0}
            for scene in scenes
        },
    }


def _audio_metadata(value):
    compiler._object(value, "audio record", ("sha256", "bytes", "durationMs"))
    if not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise GenerationError("Invalid saved audio hash.")
    compiler._integer(value["bytes"], "audio bytes", 10, MAX_AUDIO_BYTES)
    compiler._integer(value["durationMs"], "audio duration", 1, MAX_DURATION_MS)


def _verify_audio(path, audio, probe=None):
    raw = _read_regular(path, MAX_AUDIO_BYTES)
    if len(raw) != audio["bytes"] or _sha(raw) != audio["sha256"] or not _has_mp3_header(raw):
        raise GenerationError("Saved audio does not match its fingerprint/hash; it will not be reused or overwritten.")
    if probe is not None and probe(raw) != audio["durationMs"]:
        raise GenerationError("Saved audio decoded duration differs from its metadata.")
    return raw


def _entry(scene, audio):
    return {
        "sceneId": scene.scene_id, "textSha256": scene.text_sha256,
        "file": scene.filename, **audio,
    }


def _catalog(configuration, entries, *, complete=False):
    return {**configuration, "status": "complete" if complete else "incomplete", "entries": entries}


def _course_with_audio(course, scenes, requests):
    result = copy.deepcopy(course)
    for scene, text in zip(result["scenes"], scenes):
        scene["englishAudio"] = {
            "durationMs": requests[text.text_sha256]["audio"]["durationMs"],
            "textSha256": text.text_sha256,
        }
    return result


def _load_resume(journal, expected, configuration, scenes, course, probe=None):
    output = journal.output
    allowed = {STATE_FILE, CATALOG_FILE}
    if course is not None:
        allowed.add(COURSE_FILE)
    for scene in scenes:
        allowed.update((scene.filename, f"{scene.filename}.part"))
    if any(child.name not in allowed or not child.is_file() for child in output.iterdir()):
        raise GenerationError("Output contains foreign files, a lock, or unrecognized staging files; inspect it before resuming.")
    state = journal.read(STATE_FILE)
    compiler._object(state, "generation state", expected.keys())
    for key in ("schemaVersion", "generator"):
        if type(state[key]) is not type(expected[key]) or state[key] != expected[key]:
            raise GenerationError("Unrecognized generation-state format; use a new output directory.")
    for key in ("fingerprint", "sourceCourseSha256"):
        if not isinstance(state[key], str) or not re.fullmatch(r"[0-9a-f]{64}", state[key]):
            raise GenerationError("Invalid saved batch fingerprint or source provenance hash.")
    legacy = _fingerprint(configuration, scenes, legacy_source_hash=state["sourceCourseSha256"])
    if state["fingerprint"] not in (expected["fingerprint"], legacy):
        raise GenerationError("Batch fingerprint differs (course/scene/text/voice/model/settings); use a new output directory.")
    state["fingerprint"] = expected["fingerprint"]
    if state["status"] not in ("incomplete", "complete") or not isinstance(state["requests"], dict):
        raise GenerationError("Invalid saved generation state.")
    if state["requests"].keys() != expected["requests"].keys():
        raise GenerationError("Saved batch is missing or adding English texts.")
    primary = {}
    for scene in scenes:
        primary.setdefault(scene.text_sha256, scene)
    for text_hash, record in state["requests"].items():
        compiler._object(record, "request state", ("status", "attempts"), ("audio",))
        compiler._integer(record["attempts"], "attempt count", 0, 1000000)
        status = record["status"]
        if status not in ("pending", "request-started", "ambiguous", "downloaded", "complete"):
            raise GenerationError("Unrecognized saved request status.")
        if (status == "pending") != (record["attempts"] == 0):
            raise GenerationError("Invalid saved request attempt count.")
        if status in ("downloaded", "complete"):
            _audio_metadata(record.get("audio"))
        elif "audio" in record:
            raise GenerationError("An uncompleted request cannot claim verified audio.")
        if status == "complete" and not (output / primary[text_hash].filename).is_file():
            raise GenerationError("A completed download is missing; it will not be silently regenerated.")
        if state["status"] == "complete" and status != "complete":
            raise GenerationError("An incomplete batch cannot claim completion.")
    entries = []
    decoded = set()
    for scene in scenes:
        record = state["requests"][scene.text_sha256]
        for name in (scene.filename, f"{scene.filename}.part"):
            path = output / name
            if not os.path.lexists(path):
                continue
            if "audio" not in record:
                raise GenerationError("Untracked audio is not safe to reuse or overwrite.")
            _verify_audio(path, record["audio"], probe if scene.text_sha256 not in decoded else None)
            decoded.add(scene.text_sha256)
            if name == scene.filename:
                entries.append(_entry(scene, record["audio"]))
    if (output / CATALOG_FILE).exists():
        catalog = journal.read(CATALOG_FILE)
        compiler._object(catalog, "English catalog", (*configuration.keys(), "status", "entries"))
        if _canonical({key: catalog[key] for key in configuration}) != _canonical(configuration):
            raise GenerationError("The saved catalog belongs to different synthesis settings.")
        if catalog["status"] not in ("incomplete", "complete") or not isinstance(catalog["entries"], list):
            raise GenerationError("Invalid English catalog status.")
        recorded = set()
        for entry in catalog["entries"]:
            compiler._object(
                entry, "English catalog entry",
                ("sceneId", "textSha256", "file", "sha256", "bytes", "durationMs"),
            )
            _audio_metadata({key: entry[key] for key in ("sha256", "bytes", "durationMs")})
            if not isinstance(entry, dict) or entry not in entries or entry["sceneId"] in recorded:
                raise GenerationError("Saved catalog entries are missing, duplicate, stale, or changed.")
            recorded.add(entry["sceneId"])
        if catalog["status"] == "complete" and len(recorded) != len(scenes):
            raise GenerationError("A partial catalog cannot claim completion.")
    elif state["status"] == "complete":
        raise GenerationError("Completed batch catalog is missing.")
    if course is not None and (output / COURSE_FILE).exists():
        if (
            len(entries) != len(scenes)
            or _canonical(journal.read(COURSE_FILE)) != _canonical(_course_with_audio(course, scenes, state["requests"]))
        ):
            raise GenerationError("The saved English course is incomplete or changed.")
    return state, entries


def _ensure_audio_file(output, scene, audio, raw):
    path = compiler._local_path(output / scene.filename, "audio output")
    stage = compiler._local_path(output / f"{scene.filename}.part", "audio staging")
    if os.path.lexists(path):
        _verify_audio(path, audio)
        if os.path.lexists(stage):
            _verify_audio(stage, audio)
            stage.unlink()
        return
    if os.path.lexists(stage):
        _verify_audio(stage, audio)
    else:
        with stage.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _verify_audio(stage, audio)
    compiler._local_path(path, "audio output before commit")
    compiler._commit_directory(stage, path)


def _ready_primary(output, scene, record):
    if "audio" not in record:
        return None
    for filename in (scene.filename, f"{scene.filename}.part"):
        if (output / filename).is_file():
            return output / filename
    return None


def _generate(
    journal, course, scenes, configuration, state, entries, api_key, synthesize, probe,
    *, write_course=True,
):
    requests = state["requests"]
    state["status"] = "incomplete"
    journal.write(STATE_FILE, state)
    journal.write(CATALOG_FILE, _catalog(configuration, entries))
    groups = {}
    for scene in scenes:
        groups.setdefault(scene.text_sha256, []).append(scene)
    completed = {entry["sceneId"]: entry for entry in entries}
    for text_hash, group in groups.items():
        primary = group[0]
        record = requests[text_hash]
        ready = _ready_primary(journal.output, primary, record)
        if ready is not None:
            raw = _verify_audio(ready, record["audio"], probe)
        else:
            attempts = record["attempts"] + 1
            record.clear()
            record.update(status="request-started", attempts=attempts)
            journal.write(STATE_FILE, state)
            try:
                raw = synthesize(SynthesisRequest(configuration["voiceId"], primary.text, api_key))
                if not isinstance(raw, bytes) or not _has_mp3_header(raw):
                    raise GenerationError("The response is not a recognized bounded MP3.")
                duration = probe(raw)
                compiler._integer(duration, "decoded English duration", 1, MAX_DURATION_MS)
            except BaseException:
                record["status"] = "ambiguous"
                journal.write(STATE_FILE, state)
                raise GenerationError(
                    "Synthesis/download verification failed. The request may have been billed; "
                    "completed files were kept. No automatic retry. Inspect the batch, then use "
                    "--resume --retry-ambiguous only if you accept possible repeat billing."
                ) from None
            record.update(
                status="downloaded",
                audio={"sha256": _sha(raw), "bytes": len(raw), "durationMs": duration},
            )
            journal.write(STATE_FILE, state)
        for scene in group:
            _ensure_audio_file(journal.output, scene, record["audio"], raw)
            if scene is primary:
                record["status"] = "complete"
                journal.write(STATE_FILE, state)
            completed[scene.scene_id] = _entry(scene, record["audio"])
            ordered = [completed[item.scene_id] for item in scenes if item.scene_id in completed]
            journal.write(CATALOG_FILE, _catalog(configuration, ordered))
    if write_course and course is not None:
        journal.write(COURSE_FILE, _course_with_audio(course, scenes, requests))
    state["status"] = "complete"
    journal.write(STATE_FILE, state)
    journal.write(CATALOG_FILE, _catalog(configuration, [completed[item.scene_id] for item in scenes], complete=True))


def run_local(
    argv=None, *, environment=None, input_fn=None, secret_fn=None,
    interactive=None, synthesize=None, probe=None, log=None,
):
    output_message = log or print
    try:
        parser = _Parser(
            prog="generate_meme_english_audio.py --local", description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "course_json", type=Path,
            help="Authored course-draft.json or a strict English-only request JSON.",
        )
        parser.add_argument("--output", required=True, type=Path)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true", help="No credentials, requests, decoding, or file writes.")
        mode.add_argument("--generate", action="store_true", help="Explicitly authorize paid synthesis after confirmation.")
        parser.add_argument("--voice-id", help="Existing ElevenLabs voice ID; otherwise prompted, never defaulted.")
        parser.add_argument("--yes", action="store_true", help="Automation: deliberately confirm the displayed billable plan.")
        parser.add_argument("--allow-draft", action="store_true", help="Acknowledge paid synthesis of reviewed-by-you draft wording.")
        parser.add_argument("--resume", action="store_true", help="Verify and reuse this exact batch's completed files.")
        parser.add_argument("--retry-ambiguous", action="store_true", help="With --resume, accept possible double billing of uncertain requests.")
        parser.add_argument("--prompt-api-key", action="store_true", help="Allow a hidden key prompt if the environment key is absent.")
        args = parser.parse_args(argv)
        if args.retry_ambiguous and (not args.resume or not args.generate):
            raise GenerationError("--retry-ambiguous requires --resume --generate and accepts possible repeat charges.")
        source = load_input(args.course_json)
        course, scenes, source_hash = source.course, source.scenes, source.source_sha256
        if course is not None:
            largest_course = _course_with_audio(
                course, scenes,
                {scene.text_sha256: {"audio": {"durationMs": MAX_DURATION_MS}} for scene in scenes},
            )
            if len(_json_bytes(largest_course)) > compiler.MAX_JSON_BYTES:
                raise GenerationError("The enriched course exceeds the JSON size limit; reduce it before paid synthesis.")
        terminal = sys.stdin.isatty() if interactive is None else interactive
        ask = input_fn or input
        voice_id = args.voice_id
        if voice_id is None:
            if not terminal:
                raise GenerationError("Noninteractive input: supply --voice-id, or run in a terminal to be prompted.")
            voice_id = ask("ElevenLabs voice ID: ").strip()
        if not VOICE_ID.fullmatch(voice_id):
            raise GenerationError("Voice ID must contain 20..64 ASCII letters/digits, with no URL or path.")
        output = _checked_output(args.output, args.resume)
        configuration = _configuration(source.course_id, voice_id)
        expected = _initial_state(_fingerprint(configuration, scenes), source_hash, scenes)
        journal = _Journal(output)
        state, entries = (
            _load_resume(journal, expected, configuration, scenes, course)
            if args.resume else (expected, [])
        )
        unique = {}
        for scene in scenes:
            unique.setdefault(scene.text_sha256, scene)
        pending = [
            scene for digest, scene in unique.items()
            if _ready_primary(output, scene, state["requests"][digest]) is None
        ]
        ambiguous = [
            scene for scene in pending
            if state["requests"][scene.text_sha256]["status"] != "pending"
        ]
        output_message(f"Voice: {voice_id}; model: {MODEL_ID}; format: {OUTPUT_FORMAT}.")
        output_message(
            f"Scenes: {len(scenes)}; unique English texts: {len(unique)}; "
            f"characters: {sum(len(scene.text) for scene in scenes)} "
            f"({sum(len(scene.text) for scene in unique.values())} unique)."
        )
        output_message(
            f"Verified scene files: {len(entries)}; planned billable POSTs: {len(pending)}; "
            f"planned characters: {sum(len(scene.text) for scene in pending)}; "
            f"ambiguous previous requests: {len(ambiguous)}."
        )
        output_message("Only English cue text is sent. Voice settings are per request; the saved voice is never changed.")
        if args.dry_run:
            output_message("Dry run: no credentials accessed, requests sent, audio decoded, or files written.")
            return 0
        if ambiguous and not args.retry_ambiguous:
            raise GenerationError(
                "An earlier request may have been billed. Inspect the batch; --resume --retry-ambiguous "
                "is required to authorize another attempt. Nothing was sent."
            )
        if pending and source.editorial_status == "draft" and not args.allow_draft:
            raise GenerationError("Review every English cue and add --allow-draft to acknowledge paid draft synthesis.")
        if probe is None:
            require_ffprobe()
        decode = probe or probe_mp3
        if args.resume:
            state, entries = _load_resume(journal, expected, configuration, scenes, course, decode)
        api_key = ""
        if pending:
            if not args.yes:
                if not terminal:
                    raise GenerationError("Noninteractive generation requires deliberate --yes confirmation.")
                if ask("Type GENERATE to authorize these potentially chargeable requests: ").strip() != "GENERATE":
                    raise GenerationError("Generation was not confirmed; nothing was sent or written.")
            env = os.environ if environment is None else environment
            api_key = env.get("ELEVENLABS_API_KEY", "").strip()
            if not api_key and args.prompt_api_key:
                if not terminal:
                    raise GenerationError("Hidden API-key prompting requires an interactive terminal.")
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    api_key = (secret_fn or getpass.getpass)("ElevenLabs API key (hidden): ").strip()
            if not api_key:
                raise GenerationError("Set ELEVENLABS_API_KEY in your environment, or use --prompt-api-key in a terminal.")
            if not 1 <= len(api_key) <= 512 or any(ord(char) < 33 or ord(char) > 126 for char in api_key):
                raise GenerationError("The environment/hidden API key has an invalid format.")
        if not args.resume:
            output.parent.mkdir(parents=True, exist_ok=True)
            compiler.checked_output(output)
            output.mkdir(mode=0o700)
        lock = compiler._local_path(output / LOCK_FILE, "generation lock")
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
        try:
            _generate(
                journal, course, scenes, configuration, state, entries,
                api_key, synthesize or synthesize_with_elevenlabs, decode,
                write_course=course is not None and compiler._local_path(args.course_json, "source course") != output / COURSE_FILE,
            )
        finally:
            compiler._local_path(lock, "generation lock cleanup").unlink()
        course_output = f", and {COURSE_FILE}" if course is not None else ""
        output_message(f"Complete: {len(scenes)} local English MP3s, {CATALOG_FILE}{course_output}.")
        output_message("Original course/media unchanged. Human listening is required; nothing was published.")
        return 0
    except GenerationError as error:
        output_message(f"Error: {error}")
    except (compiler.CompileError, UnicodeError, json.JSONDecodeError):
        output_message("Error: invalid course/request/state JSON, text/cue metadata, or unsafe local path. Nothing is published.")
    except (OSError, EOFError, getpass.GetPassWarning):
        output_message("Error: local input/output or secure terminal input failed. No automatic retry; inspect the batch state.")
    except KeyboardInterrupt:
        output_message("Cancelled. Inspect the saved request state before retrying; a started request may have been billed.")
    except Exception:
        output_message("Error: generation failed. No provider details are logged and no automatic retry was attempted.")
    return 1


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    options_end = arguments.index("--") if "--" in arguments else len(arguments)
    if "--local" in arguments[:options_end]:
        arguments.remove("--local")
        return run_local(arguments)
    from importlib import import_module

    module_name = f"{__package__}.run_meme_english_audio" if __package__ else "run_meme_english_audio"
    try:
        runner = import_module(module_name)
    except ImportError:
        print(
            "Error: the GitHub runner is unavailable. Restore run_meme_english_audio.py "
            "or explicitly select --local. No local fallback or key prompt was attempted."
        )
        return 1
    return runner.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
