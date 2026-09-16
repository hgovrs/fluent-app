"""Local speech preparation for the video/GIF command; no ElevenLabs uploads."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import wave


class SpeechError(ValueError):
    """An actionable audio preparation error."""


@dataclass
class SpeechOptions:
    extract_audio: bool = False
    transcribe_model: Path | None = None
    diarization_model: Path | None = None
    speaker_segments: Path | None = None
    language: str | None = None
    num_speakers: int | None = None
    voices_authorized: bool = False

    @property
    def enabled(self):
        return bool(self.extract_audio or self.transcribe_model
                    or self.diarization_model or self.speaker_segments)

    def validate(self):
        if self.diarization_model and self.speaker_segments:
            raise SpeechError("Escolha --diarization-model ou --speaker-segments.")
        if (self.diarization_model or self.speaker_segments) and not self.voices_authorized:
            raise SpeechError(
                "Use --voices-authorized somente com autorização dos donos das vozes."
            )
        if self.language and not self.transcribe_model:
            raise SpeechError("--language requer --transcribe-model.")
        if self.num_speakers is not None:
            if not self.diarization_model or not 1 <= self.num_speakers <= 100:
                raise SpeechError("--num-speakers requer diarização e um valor entre 1 e 100.")
        for model in (self.transcribe_model, self.diarization_model):
            if model and not Path(model).is_dir():
                raise SpeechError("Informe uma pasta de modelo local previamente baixado.")
        if self.speaker_segments and not Path(self.speaker_segments).is_file():
            raise SpeechError("O JSON de locutores não existe.")


def offline_models():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["PYANNOTE_METRICS_ENABLED"] = "0"


def transcribe(audio, model_path, language):
    offline_models()
    try:
        from faster_whisper import WhisperModel
    except (ImportError, OSError, RuntimeError):
        raise SpeechError("Instale faster-whisper para usar --transcribe-model.") from None
    try:
        model = WhisperModel(
            str(Path(model_path).resolve()), device="cpu", compute_type="int8",
            local_files_only=True,
        )
        segments, info = model.transcribe(str(audio), language=language, vad_filter=True)
        return {
            "language": info.language,
            "segments": [
                {"start": item.start, "end": item.end, "text": item.text.strip()}
                for item in segments
            ],
        }
    except Exception:
        raise SpeechError(
            "Falha na transcrição local; confira o modelo completo, idioma e memória disponível."
        ) from None


def diarize(audio, model_path, num_speakers):
    offline_models()
    try:
        from pyannote.audio import Pipeline
        from pyannote.audio.pipelines import SpeakerDiarization
    except (ImportError, OSError, RuntimeError):
        raise SpeechError("Instale pyannote.audio para usar --diarization-model.") from None
    try:
        pipeline = Pipeline.from_pretrained(str(Path(model_path).resolve()), token=False)
        if not isinstance(pipeline, SpeakerDiarization):
            raise SpeechError("Use apenas o pipeline local SpeakerDiarization (community-1).")
        options = {} if num_speakers is None else {"num_speakers": num_speakers}
        result = pipeline(str(audio), **options)
        return [
            {"start": turn.start, "end": turn.end, "speaker": speaker}
            for turn, _, speaker in result.speaker_diarization.itertracks(yield_label=True)
        ]
    except SpeechError:
        raise
    except Exception:
        raise SpeechError(
            "Falha na diarização local; confira o modelo community-1 completo, "
            "dependências de áudio e memória disponível."
        ) from None


def validate_turns(turns, duration, *, clip_to_audio=False):
    if not isinstance(turns, list) or len(turns) > 10000:
        raise SpeechError("Os locutores devem ser uma lista com no máximo 10.000 trechos.")
    validated = []
    for turn in turns:
        if not isinstance(turn, dict):
            raise SpeechError("Cada trecho de voz deve ser um objeto JSON.")
        start, end, speaker = turn.get("start"), turn.get("end"), turn.get("speaker")
        if (not isinstance(speaker, str) or not speaker.strip() or len(speaker) > 80
                or any(ord(c) < 32 for c in speaker)):
            raise SpeechError("Cada trecho deve ter um rótulo speaker de 1 a 80 caracteres.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in (start, end)):
            raise SpeechError("start/end dos locutores devem ser segundos numéricos finitos.")
        if start >= end:
            raise SpeechError("Cada trecho de voz deve ter start menor que end.")
        if clip_to_audio:
            # Model inference can include padding beyond the recording boundaries.
            start, end = max(0, start), min(duration, end)
            if start >= end:
                continue
        if not 0 <= start < end <= duration:
            raise SpeechError(f"Trecho de voz fora do áudio extraído ({duration:.3f}s).")
        validated.append({"start": start, "end": end, "speaker": speaker})
    if len({turn["speaker"] for turn in validated}) > 100:
        raise SpeechError("Limite de 100 locutores por execução.")
    return sorted(validated, key=lambda turn: (turn["start"], turn["end"], turn["speaker"]))


def clean_intervals(turns, rate):
    """Keep only sample intervals with one distinct speaker, merging duplicates."""
    events = defaultdict(list)
    for turn in turns:
        start, end = math.ceil(turn["start"] * rate), math.floor(turn["end"] * rate)
        if end > start:
            events[start].append((turn["speaker"], 1))
            events[end].append((turn["speaker"], -1))
    active = defaultdict(int)
    clean = defaultdict(list)
    previous = 0
    overlap_frames = 0
    for position in sorted(events):
        speakers = [speaker for speaker, count in active.items() if count > 0]
        if len(speakers) == 1 and position > previous:
            intervals = clean[speakers[0]]
            if intervals and intervals[-1][1] == previous:
                intervals[-1][1] = position
            else:
                intervals.append([previous, position])
        elif len(speakers) > 1:
            overlap_frames += position - previous
        for speaker, delta in events[position]:
            active[speaker] += delta
        previous = position
    return clean, overlap_frames


def write_speakers(audio, destination, turns):
    speakers = []
    with wave.open(str(audio), "rb") as source:
        rate = source.getframerate()
        intervals, overlap_frames = clean_intervals(turns, rate)
        for index, label in enumerate(dict.fromkeys(turn["speaker"] for turn in turns), 1):
            speaker_id = f"speaker_{index:03d}"
            folder = destination / "speakers" / speaker_id
            ranges = intervals.get(label, [])
            item = {"id": speaker_id, "label": label, "file": None,
                    "duration": 0, "clips": []}
            if ranges:
                folder.mkdir(parents=True)
                combined_path = folder / "combined.wav"
                with wave.open(str(combined_path), "wb") as combined:
                    combined.setparams(source.getparams())
                    for number, (start, end) in enumerate(ranges, 1):
                        path = folder / f"clip_{number:04d}.wav"
                        source.setpos(start)
                        with wave.open(str(path), "wb") as clip:
                            clip.setparams(source.getparams())
                            remaining = end - start
                            while remaining:
                                count = min(remaining, rate * 10)
                                data = source.readframes(count)
                                if len(data) != count * source.getsampwidth() * source.getnchannels():
                                    raise SpeechError("Áudio truncado durante o corte por locutor.")
                                clip.writeframesraw(data)
                                combined.writeframesraw(data)
                                remaining -= count
                        item["clips"].append({
                            "start": start / rate, "end": end / rate,
                            "file": path.relative_to(destination).as_posix(),
                        })
                item["file"] = combined_path.relative_to(destination).as_posix()
                item["duration"] = sum(end - start for start, end in ranges) / rate
            speakers.append(item)
    return speakers, overlap_frames / rate


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def prepare(video, destination, options, run_media):
    audio = destination / "audio.wav"
    run_media([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-protocol_whitelist", "file,pipe", "-i", str(video),
        "-map", "0:a:0", "-vn", "-af", "asetpts=PTS-STARTPTS",
        "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(audio),
    ])
    with wave.open(str(audio), "rb") as source:
        duration = source.getnframes() / source.getframerate()
    if duration <= 0:
        raise SpeechError("A faixa de áudio está vazia.")
    result = {"file": "audio.wav", "duration": duration, "sampleRate": 44100,
              "channels": 1, "sampleWidth": 2}
    if options.transcribe_model:
        transcript = transcribe(audio, options.transcribe_model, options.language)
        write_json(destination / "transcript.json", transcript)
        (destination / "transcript.txt").write_text(
            "\n".join(segment["text"] for segment in transcript["segments"]) + "\n",
            encoding="utf-8",
        )
        result["transcript"] = {"text": "transcript.txt", "json": "transcript.json"}
    if options.diarization_model or options.speaker_segments:
        if options.speaker_segments:
            turns = json.loads(Path(options.speaker_segments).read_text(encoding="utf-8"))
        else:
            turns = diarize(audio, options.diarization_model, options.num_speakers)
        turns = validate_turns(turns, duration, clip_to_audio=bool(options.diarization_model))
        write_json(destination / "speaker_segments.json", turns)
        speakers, overlap = write_speakers(audio, destination, turns)
        result.update({
            "speakerSegments": "speaker_segments.json", "speakers": speakers,
            "excludedOverlapDuration": overlap,
            "speakerMethod": "manual" if options.speaker_segments else "pyannote-community-1",
            "voicesAuthorized": True,
        })
        result["warnings"] = [
            "Diarização não isola vozes simultâneas nem remove música/ruído. "
            "Revise cada WAV e a autorização antes de enviar ao ElevenLabs."
        ]
        if not any(speaker["file"] for speaker in speakers):
            result["warnings"].append("Nenhuma fala isolada disponível para exportar por voz.")
    return result
