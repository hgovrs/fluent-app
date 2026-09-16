#!/usr/bin/env python3
"""Convert a local video to a GIF and temporal feedback clips using FFmpeg."""

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


CATEGORIES = ("correct", "incorrect")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}")
MAX_CLIPS = 1000


class GenerationError(Exception):
    """An actionable input or conversion error."""


def positive_number(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError("Use um número positivo.") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Use um número positivo e finito.")
    return number


def run_media(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise GenerationError(
            f"{Path(command[0]).name} falhou: {result.stderr.strip()[-2000:]}"
        )
    return result.stdout


def video_duration(video):
    metadata = json.loads(run_media([
        "ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
        "-select_streams", "v:0", "-show_entries",
        "stream=duration:format=duration", "-of", "json", str(video),
    ]))
    streams = metadata.get("streams", [])
    if not streams:
        raise GenerationError("O arquivo não contém uma faixa de vídeo.")
    for value in (streams[0].get("duration"), metadata.get("format", {}).get("duration")):
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(duration) and duration > 0:
            return duration
    raise GenerationError("Não foi possível determinar a duração do vídeo.")


def make_clips(duration, fps, segments=None, category=None, segment_duration=3):
    if segments is None:
        if category not in CATEGORIES:
            raise GenerationError("Informe --category para cortes automáticos.")
        if not math.isfinite(segment_duration) or segment_duration < 1 / fps:
            raise GenerationError("Cada trecho deve durar pelo menos um quadro.")
        count = math.ceil(duration / segment_duration)
        if count > MAX_CLIPS:
            raise GenerationError(f"Limite de {MAX_CLIPS} trechos por execução.")
        segments = [
            {
                "id": f"{category}_{index + 1:03d}",
                "category": category,
                "start": index * segment_duration,
                "end": min((index + 1) * segment_duration, duration),
            }
            for index in range(count)
        ]
        if len(segments) > 1 and segments[-1]["end"] - segments[-1]["start"] < 1 / fps:
            tail = segments.pop()
            segments[-1]["end"] = tail["end"]
    if not isinstance(segments, list) or not 1 <= len(segments) <= MAX_CLIPS:
        raise GenerationError(f"Os cortes devem ser uma lista de 1 a {MAX_CLIPS} itens.")
    clips = []
    ids = set()
    for segment in segments:
        if not isinstance(segment, dict):
            raise GenerationError("Cada corte deve ser um objeto JSON.")
        clip_id = segment.get("id")
        if (not isinstance(clip_id, str) or not ID_PATTERN.fullmatch(clip_id)
                or clip_id == "full" or clip_id in ids):
            raise GenerationError(
                "IDs devem ser únicos, com até 80 letras minúsculas, números, _ ou -; "
                "começar com letra/número e não usar 'full'."
            )
        category = segment.get("category")
        if category not in CATEGORIES:
            raise GenerationError(f"{clip_id}: category deve ser correct ou incorrect.")
        start, end = segment.get("start"), segment.get("end")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in (start, end)):
            raise GenerationError(f"{clip_id}: start/end devem ser segundos numéricos finitos.")
        if not 0 <= start < end <= duration or end - start < 1 / fps:
            raise GenerationError(
                f"{clip_id}: corte fora do vídeo ({duration:.3f}s) ou menor que um quadro."
            )
        ids.add(clip_id)
        clips.append({
            "id": clip_id, "category": category, "start": start, "end": end,
            "file": f"{clip_id}.gif",
        })
    return clips


def generate(video, output, *, fps=10, width=480, segments=None,
             category=None, segment_duration=3):
    video = Path(video).resolve()
    output = Path(output).absolute()
    if not video.is_file():
        raise GenerationError("Informe um arquivo de vídeo local existente.")
    if output.exists() or output.is_symlink():
        raise GenerationError("A pasta de saída já existe; escolha uma pasta nova.")
    if not 1 <= fps <= 50 or not 16 <= width <= 1920:
        raise GenerationError("Use fps entre 1 e 50 e largura entre 16 e 1920.")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise GenerationError(f"Instale FFmpeg e disponibilize {tool} no PATH.")
    duration = video_duration(video)
    clips = make_clips(duration, fps, segments, category, segment_duration)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".feedback-gifs-", dir=output.parent) as temporary:
        staging = Path(temporary) / "result"
        staging.mkdir()
        full_gif = staging / "full.gif"
        filters = (
            f"[0:v:0]setpts=PTS-STARTPTS,fps={fps},"
            f"scale={width}:-1:flags=lanczos,split[a][b];"
            "[a]palettegen[p];[b][p]paletteuse"
        )
        base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        run_media(base + [
            "-protocol_whitelist", "file,pipe", "-i", str(video),
            "-filter_complex_threads", "1", "-filter_complex", filters,
            "-an", "-t", str(duration), "-loop", "0", str(full_gif),
        ])
        for clip in clips:
            run_media(base + [
                "-ignore_loop", "1", "-i", str(full_gif),
                "-ss", str(clip["start"]), "-t", str(clip["end"] - clip["start"]),
                "-an", "-loop", "0", str(staging / clip["file"]),
            ])
        catalog = {
            "schemaVersion": 1,
            "fullGif": "full.gif",
            "sourceDuration": duration,
            "fps": fps,
            "width": width,
            "clips": clips,
        }
        (staging / "catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        if output.exists() or output.is_symlink():
            raise GenerationError("A pasta de saída foi criada durante a conversão.")
        staging.rename(output)
    return catalog


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Vídeo local; o original não será alterado.")
    parser.add_argument("--output", type=Path, required=True, help="Nova pasta de saída.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--category", choices=CATEGORIES, help="Categoria de todos os cortes automáticos.")
    mode.add_argument("--segments", type=Path, help="JSON com lista de cortes: id, category, start, end.")
    parser.add_argument("--segment-duration", type=positive_number, default=None,
                        help="Segundos por corte automático (padrão: 3).")
    parser.add_argument("--fps", type=int, default=10, help="Quadros por segundo, 1–50 (padrão: 10).")
    parser.add_argument("--width", type=int, default=480, help="Largura, 16–1920 (padrão: 480).")
    args = parser.parse_args(argv)
    if args.segments and args.segment_duration is not None:
        parser.error("--segment-duration não pode ser usado com --segments.")
    try:
        segments = None
        if args.segments:
            segments = json.loads(args.segments.read_text(encoding="utf-8"))
            if not isinstance(segments, list):
                raise GenerationError("O JSON de cortes deve conter uma lista.")
        catalog = generate(
            args.video, args.output, fps=args.fps, width=args.width, segments=segments,
            category=args.category, segment_duration=args.segment_duration or 3,
        )
    except (GenerationError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"GIF completo e {len(catalog['clips'])} trechos salvos em {args.output.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
