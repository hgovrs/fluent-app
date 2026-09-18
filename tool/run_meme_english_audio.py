"""Generate English meme audio through the existing GitHub environment secret.

The default workflow never requests, retrieves, copies, or stores an API key.
Only English text is sent to the repository's manually triggered workflow.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid
import zipfile

if __package__:
    from . import compile_meme_course as compiler
else:
    import compile_meme_course as compiler


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = "generate-meme-english-audio.yml"
DEFAULT_ENVIRONMENT = "fluent"
ENVIRONMENTS = ("fluent", "copilot")
RECEIPT = "github-generation.json"
LOCAL_RECEIPT = "github-request.json"
TITLE_PREFIX = "English meme audio "
MAX_DISPATCH_BYTES = 60000
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_AUDIO_BYTES = 2 * 1024 * 1024
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
VOICE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class GithubGenerationError(ValueError):
    pass


def engine_module():
    if __package__:
        from . import generate_meme_english_audio
    else:
        import generate_meme_english_audio
    return generate_meme_english_audio


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def engine_hash():
    text = Path(engine_module().__file__).read_text(encoding="utf-8-sig")
    return digest(text.replace("\r\n", "\n").encode("utf-8"))


def load_request(path):
    _, document, _ = compiler._read_json(path, "curso ou solicitação inglesa")
    if isinstance(document, dict) and document.get("kind") == "meme_english_tts_request":
        return validate_request(document)
    engine = engine_module()
    try:
        return engine.export_english_request(path)
    except engine.GenerationError as error:
        raise GithubGenerationError(str(error)) from None


def validate_request(document):
    engine = engine_module()
    try:
        engine._validate_english_request(document)
    except engine.GenerationError as error:
        raise GithubGenerationError(str(error)) from None
    return document


def batch_id(request, voice_id, code_hash, secret_environment=DEFAULT_ENVIRONMENT):
    return digest(canonical({
        "courseId": request["courseId"],
        "scenes": [{"id": item["id"], "textSha256": item["textSha256"]}
                   for item in request["scenes"]],
        "voiceId": voice_id,
        "engineSha256": code_hash,
        "secretEnvironment": secret_environment,
    }).encode("utf-8"))


def gh(arguments, *, payload=None, binary=False, timeout=120):
    environment = os.environ.copy()
    environment.pop("ELEVENLABS_API_KEY", None)
    try:
        result = subprocess.run(
            ["gh", *arguments], cwd=ROOT, env=environment,
            input=None if payload is None else payload.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise GithubGenerationError(
            "GitHub CLI indisponível ou sem resposta. Não houve tentativa automática "
            "de repetir a operação; confira o recibo e a execução no GitHub."
        ) from error
    if result.returncode:
        raise GithubGenerationError(
            "O GitHub recusou a operação. Confira autenticação, permissões de Actions "
            "e se o workflow inglês já está na branch padrão. O secret existente no "
            "ambiente selecionado não precisa ser copiado para este terminal."
        )
    if binary:
        return result.stdout
    try:
        return json.loads(result.stdout) if result.stdout.strip() else None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GithubGenerationError("Resposta de metadados do GitHub inválida.") from error


def repository_name(override=None):
    if override:
        name = override
    elif os.environ.get("GITHUB_REPOSITORY"):
        name = os.environ["GITHUB_REPOSITORY"]
    else:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=ROOT,
                capture_output=True, text=True, check=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise GithubGenerationError("Informe --repository no formato dono/repositório.") from error
        remote = result.stdout.strip()
        if remote.startswith("git@github.com:"):
            name = remote.removeprefix("git@github.com:")
        else:
            parsed = urlsplit(remote)
            if parsed.scheme != "https" or parsed.hostname != "github.com":
                raise GithubGenerationError("Use um origin GitHub ou informe --repository.")
            name = parsed.path.lstrip("/")
        name = name.removesuffix(".git")
    if not REPOSITORY.fullmatch(name) or any(part in (".", "..") for part in name.split("/")):
        raise GithubGenerationError("Repositório inválido; use dono/repositório.")
    return name


def run_list(repository, identifier):
    runs = gh([
        "run", "list", "--repo", repository, "--workflow", WORKFLOW, "--limit", "100",
        "--json", "databaseId,displayTitle,status,conclusion,createdAt",
    ])
    if not isinstance(runs, list):
        raise GithubGenerationError("Lista de execuções inválida.")
    prefix = f"{TITLE_PREFIX}{identifier}/"
    return [item for item in runs if isinstance(item, dict)
            and str(item.get("displayTitle", "")).startswith(prefix)]


def artifact_name(identifier):
    return f"meme-english-{identifier}"


def save_json(path, value):
    pending = path.with_suffix(path.suffix + ".pending")
    with pending.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)


def verify_archive(raw, request, voice_id, identifier, code_hash,
                   secret_environment=DEFAULT_ENVIRONMENT):
    if not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
        raise GithubGenerationError("Artefato ausente ou acima do limite de download.")
    engine = engine_module()
    catalog_name = engine.CATALOG_FILENAME
    expected = {item["id"]: item for item in request["scenes"]}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (len(entries) > 4 * len(expected) + 32
                    or len(names) != len(set(names))
                    or sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES):
                raise GithubGenerationError("Artefato com nomes duplicados ou conteúdo excessivo.")
            for entry in entries:
                name = entry.orig_filename
                path = PurePosixPath(name)
                if (name != entry.filename or path.is_absolute() or ".." in path.parts
                        or "\\" in name or ":" in name
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise GithubGenerationError("Caminho inseguro no artefato.")
            by_name = {entry.filename: entry for entry in entries}

            def read(name, maximum):
                info = by_name.get(name)
                if (info is None or info.is_dir() or not 0 < info.file_size <= maximum
                        or PurePosixPath(name).name != name
                        or stat.S_ISLNK(info.external_attr >> 16)):
                    raise GithubGenerationError("Arquivo esperado ausente ou inválido no artefato.")
                content = archive.read(info)
                if len(content) != info.file_size:
                    raise GithubGenerationError("Arquivo incompleto no artefato.")
                return content

            receipt = json.loads(
                read(RECEIPT, 16384), object_pairs_hook=compiler._unique_object,
                parse_constant=compiler._invalid_constant,
            )
            if (receipt.get("batchId") != identifier or receipt.get("engineSha256") != code_hash
                    or receipt.get("voiceId") != voice_id
                    or receipt.get("environment") != secret_environment):
                raise GithubGenerationError("O recibo não corresponde ao lote/voz/gerador solicitado.")
            catalog_bytes = read(catalog_name, 1024 * 1024)
            catalog = json.loads(
                catalog_bytes, object_pairs_hook=compiler._unique_object,
                parse_constant=compiler._invalid_constant,
            )
            if (catalog.get("schemaVersion") != 1 or catalog.get("status") != "complete"
                    or catalog.get("courseId") != request["courseId"]
                    or catalog.get("language") != "en" or catalog.get("voiceId") != voice_id
                    or catalog.get("modelId") != engine.DEFAULT_MODEL_ID
                    or catalog.get("outputFormat") != engine.DEFAULT_OUTPUT_FORMAT
                    or canonical(catalog.get("voiceSettings")) != canonical(engine.DEFAULT_VOICE_SETTINGS)):
                raise GithubGenerationError("O lote inglês está incompleto ou usa outra configuração.")
            items = catalog.get("entries")
            if not isinstance(items, list) or len(items) != len(expected):
                raise GithubGenerationError("O artefato não contém todas as traduções.")
            files = {catalog_name: catalog_bytes, RECEIPT: read(RECEIPT, 16384)}
            seen = set()
            for item in items:
                if not isinstance(item, dict):
                    raise GithubGenerationError("Entrada de áudio inválida.")
                scene_id = item.get("sceneId")
                if scene_id not in expected or scene_id in seen:
                    raise GithubGenerationError("Cena inglesa ausente, repetida ou estranha ao curso.")
                seen.add(scene_id)
                name = f"{scene_id}.en.mp3"
                if (item.get("file") != name
                        or item.get("textSha256") != expected[scene_id]["textSha256"]
                        or type(item.get("durationMs")) is not int
                        or not 1 <= item["durationMs"] <= 60000):
                    raise GithubGenerationError("O áudio inglês não corresponde à tradução atual.")
                data = read(name, MAX_AUDIO_BYTES)
                if (item.get("bytes") != len(data) or item.get("sha256") != digest(data)
                        or len(data) < 10
                        or not (data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0))):
                    raise GithubGenerationError("MP3 inglês corrompido ou divergente.")
                files[name] = data
            return files
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError,
            TypeError, AttributeError) as error:
        raise GithubGenerationError("Artefato de áudio inglês inválido.") from error


def download_run(repository, run_id, request, voice_id, identifier, code_hash, output,
                 secret_environment=DEFAULT_ENVIRONMENT):
    response = gh(["api", f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"])
    matches = [item for item in response.get("artifacts", [])
               if item.get("name") == artifact_name(identifier) and not item.get("expired")]
    if len(matches) != 1 or not 0 < matches[0].get("size_in_bytes", 0) <= MAX_ARCHIVE_BYTES:
        raise GithubGenerationError(
            "A execução não tem um artefato completo disponível. Nenhuma nova síntese "
            "foi disparada automaticamente. Confira falha/expiração no GitHub."
        )
    artifact_id = matches[0]["id"]
    raw = gh(["api", f"repos/{repository}/actions/artifacts/{artifact_id}/zip"], binary=True, timeout=180)
    files = verify_archive(raw, request, voice_id, identifier, code_hash, secret_environment)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        destination = output / name
        if destination.exists():
            if destination.read_bytes() != data:
                raise GithubGenerationError("Arquivo local existente diverge do artefato; não será substituído.")
            continue
        pending = destination.with_suffix(destination.suffix + ".pending")
        with pending.open("xb") as stream:
            stream.write(data)
        pending.replace(destination)
    return output / engine_module().CATALOG_FILENAME


def wait_for_run(repository, run_id, *, seconds=1800):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        run = gh(["api", f"repos/{repository}/actions/runs/{run_id}"])
        if run.get("status") == "completed":
            if run.get("conclusion") != "success":
                raise GithubGenerationError(
                    f"Execução {run_id} terminou sem sucesso. Os créditos podem ter sido "
                    "consumidos parcialmente; não houve repetição automática."
                )
            return
        time.sleep(10)
    raise GithubGenerationError(
        f"Execução {run_id} continua pendente. Retome com --resume; confira também "
        "eventual aprovação do ambiente no GitHub. Não dispare outro lote."
    )


def worker():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise GithubGenerationError("--worker só pode executar no workflow GitHub configurado.")
    request = validate_request(json.loads(
        os.environ["TTS_REQUEST_JSON"], object_pairs_hook=compiler._unique_object,
        parse_constant=compiler._invalid_constant,
    ))
    voice_id = os.environ["TTS_VOICE_ID"]
    identifier = os.environ["TTS_BATCH_ID"]
    secret_environment = os.environ["TTS_SECRET_ENVIRONMENT"]
    code_hash = engine_hash()
    if (secret_environment not in ENVIRONMENTS or not VOICE_ID.fullmatch(voice_id)
            or os.environ["TTS_ENGINE_SHA256"] != code_hash
            or batch_id(request, voice_id, code_hash, secret_environment) != identifier):
        raise GithubGenerationError("A solicitação não corresponde ao gerador/voz publicados.")
    repository = repository_name()
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    if not run_id.isdigit() or not attempt.isdigit():
        raise GithubGenerationError("Identificador de execução inválido.")
    work = compiler.checked_output(ROOT / "build" / "meme-course-work" / f"github-{run_id}-{attempt}")
    work.mkdir(parents=True)
    source = work / "english-request.json"
    save_json(source, request)
    output = work / "audio"
    for previous in run_list(repository, identifier):
        if (str(previous.get("databaseId")) != run_id
                and previous.get("conclusion") == "success"
                and os.environ.get("TTS_REGENERATE") != "true"):
            download_run(repository, previous["databaseId"], request, voice_id, identifier,
                         code_hash, output, secret_environment)
            print("Lote idêntico recuperado; nenhuma síntese adicional.", flush=True)
            break
    else:
        arguments = [
            sys.executable, "-B", str(ROOT / "tool" / "generate_meme_english_audio.py"),
            str(source), "--local", "--output", str(output), "--voice-id", voice_id,
            "--generate", "--yes",
        ]
        if os.environ.get("TTS_ALLOW_DRAFT") == "true":
            arguments.append("--allow-draft")
        result = subprocess.run(arguments, cwd=ROOT, check=False)
        if result.returncode:
            raise GithubGenerationError(
                "Síntese incompleta. Downloads concluídos permanecem no artefato parcial; "
                "não execute novamente sem conferir o estado para evitar cobranças duplicadas."
            )
    save_json(output / RECEIPT, {
        "schemaVersion": 1, "batchId": identifier, "engineSha256": code_hash,
        "voiceId": voice_id, "environment": secret_environment,
        "repository": repository, "runId": run_id, "runAttempt": attempt,
    })
    print(f"English audio output: {output}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--voice-id")
    parser.add_argument("--repository")
    parser.add_argument("--secret-environment", choices=ENVIRONMENTS, default=DEFAULT_ENVIRONMENT,
                        help="Ambiente GitHub já configurado; fluent foi usado no lote anterior.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--generate", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            worker()
            return 0
        if args.course is None:
            parser.error("Informe o course.json preparado localmente.")
        request = load_request(args.course)
        texts = {item["text"] for item in request["scenes"]}
        characters = sum(len(text) for text in texts)
        voice_id = args.voice_id
        if voice_id and not VOICE_ID.fullmatch(voice_id):
            raise GithubGenerationError("voice_id inválido.")
        print(f"{len(request['scenes'])} cenas; {len(texts)} textos únicos; {characters} caracteres estimados.")
        print(f"Credencial: GitHub Actions / ambiente {args.secret_environment}. Nenhuma chave local é necessária.")
        if not args.generate and not args.resume:
            print("Prévia: nenhuma requisição, cobrança ou gravação de arquivo.")
            return 0
        if not voice_id:
            if not sys.stdin.isatty():
                raise GithubGenerationError("Informe --voice-id; a chave da API não é solicitada.")
            voice_id = input("ID da voz ElevenLabs: ").strip()
            if not VOICE_ID.fullmatch(voice_id):
                raise GithubGenerationError("voice_id inválido.")
        if request["editorialStatus"] == "draft" and not args.allow_draft:
            raise GithubGenerationError(
                "As traduções estão em revisão. Use --allow-draft somente após autorizar "
                "explicitamente a síntese desse rascunho."
            )
        if args.output is None:
            parser.error("Informe uma pasta local isolada em --output.")
        if not args.yes:
            if not sys.stdin.isatty() or input(
                f"Voz {voice_id}; até {len(texts)} sínteses / {characters} caracteres. "
                "Autoriza o consumo de créditos deste lote? [sim/N]: "
            ).strip().lower() != "sim":
                raise GithubGenerationError("Nenhuma geração autorizada. Use --yes apenas com aprovação do lote.")
        repository = repository_name(args.repository)
        code_hash = engine_hash()
        identifier = batch_id(request, voice_id, code_hash, args.secret_environment)
        payload_text = canonical(request)
        if len(payload_text.encode("utf-8")) > MAX_DISPATCH_BYTES:
            raise GithubGenerationError(
                "O roteiro inglês excede o limite de entrada deste workflow. Nenhuma "
                "parte foi omitida ou enviada; use o modo local explicitamente autorizado."
            )
        output = engine_module()._checked_output(args.output, args.resume)
        receipt_path = output / LOCAL_RECEIPT
        if args.resume and receipt.get("status") != "planned":
            _, receipt, _ = compiler._read_json(receipt_path, "recibo da execução")
            if (receipt.get("batchId") != identifier or receipt.get("repository") != repository
                    or receipt.get("voiceId") != voice_id
                    or receipt.get("secretEnvironment") != args.secret_environment):
                raise GithubGenerationError("A pasta existente pertence a outra solicitação.")
            request_id = receipt["requestId"]
        else:
            output.mkdir(parents=True)
            request_id = uuid.uuid4().hex
            receipt = {
                "batchId": identifier, "repository": repository, "voiceId": voice_id,
                "secretEnvironment": args.secret_environment,
                "requestId": request_id, "status": "planned",
            }
            save_json(receipt_path, receipt)
        runs = run_list(repository, identifier)
        current = [run for run in runs
                   if run.get("displayTitle") == f"{TITLE_PREFIX}{identifier}/{request_id}"]
        reusable = [] if args.regenerate else [
            run for run in runs if run.get("conclusion") == "success"
            or run.get("status") != "completed"
        ]
        selected = current[0] if current else reusable[0] if reusable else None
        if selected is None:
            if args.resume:
                raise GithubGenerationError(
                    "Não foi possível confirmar o disparo anterior. Confira as execuções "
                    "no GitHub; --resume nunca repete uma solicitação de geração."
                )
            metadata = gh(["api", f"repos/{repository}"])
            branch = metadata.get("default_branch")
            if not isinstance(branch, str) or not branch:
                raise GithubGenerationError("Não foi possível resolver a branch padrão.")
            receipt["status"] = "dispatch_started"
            save_json(receipt_path, receipt)
            gh(["api", "--method", "POST",
                f"repos/{repository}/actions/workflows/{WORKFLOW}/dispatches", "--input", "-"],
               payload=canonical({
                   "ref": branch,
                   "inputs": {
                       "request_json": payload_text, "voice_id": voice_id,
                       "batch_id": identifier, "request_id": request_id,
                       "engine_sha256": code_hash, "generate": "true",
                       "secret_environment": args.secret_environment,
                       "allow_draft": str(args.allow_draft).lower(),
                       "regenerate": str(args.regenerate).lower(),
                   },
               }))
            for _ in range(24):
                found = run_list(repository, identifier)
                selected = next((run for run in found if run.get("displayTitle")
                                 == f"{TITLE_PREFIX}{identifier}/{request_id}"), None)
                if selected:
                    break
                time.sleep(5)
            if selected is None:
                raise GithubGenerationError("Disparo enviado, ainda não localizado. Retome com --resume, não gere outro lote.")
        run_id = selected["databaseId"]
        receipt.update(runId=run_id, status="waiting")
        save_json(receipt_path, receipt)
        print(f"https://github.com/{repository}/actions/runs/{run_id}", flush=True)
        wait_for_run(repository, run_id)
        catalog = download_run(repository, run_id, request, voice_id, identifier,
                               code_hash, output, args.secret_environment)
        receipt["status"] = "downloaded_and_verified"
        save_json(receipt_path, receipt)
        print(f"Áudios ingleses baixados e conferidos: {catalog}", flush=True)
        return 0
    except (GithubGenerationError, compiler.CompileError, OSError, ValueError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except (KeyError, TypeError, AttributeError):
        print("Erro: metadados da solicitação ou da execução incompatíveis.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
