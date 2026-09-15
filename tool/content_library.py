#!/usr/bin/env python3
"""Explicit, offline-first acquisition of reviewed PDF and EPUB study books.

This tool is independent of the Flutter app. It never downloads on app startup,
extracts archives, or writes books into Flutter assets.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException, HTTPSConnection
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener
import zipfile


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "assets" / "content" / "sources.json"
DEFAULT_OUTPUT = ROOT / "content-cache"
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT_SECONDS = 30
TOTAL_SECONDS = 120
LICENSES = {"CC BY 4.0", "CC BY-NC 4.0", "CC BY-NC-SA 4.0"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


class LibraryError(Exception):
    """An actionable manifest, policy, network, or cache error."""


def checked_id(value):
    if not isinstance(value, str) or len(value) > 80 or not ID_PATTERN.fullmatch(value):
        raise LibraryError(f"Unsafe ID: {value!r}; use lowercase letters, digits and hyphens")
    return value


def public_address(address):
    address = ipaddress.ip_address(address)
    return address.is_global and not address.is_multicast


def public_endpoints(host, port=443):
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not addresses or any(not public_address(item[4][0]) for item in addresses):
            raise LibraryError(f"Host does not resolve exclusively to public addresses: {host}")
        return addresses
    except (OSError, ValueError) as exc:
        raise LibraryError(f"Cannot safely resolve host {host}: {exc}") from exc


def checked_url(url, original_host=None, resolve=False):
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url):
        raise LibraryError("URLs must be nonempty and contain no whitespace or control characters")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise LibraryError(f"Invalid URL: {url!r}") from exc
    if (parts.scheme != "https" or not host or parts.username is not None
            or parts.password is not None or port not in (None, 443)
            or parts.fragment or "\\" in url):
        raise LibraryError(f"Only credential-free public HTTPS URLs on port 443 are allowed: {url}")
    if original_host is not None and host != original_host:
        raise LibraryError(f"Redirect to an unexpected host is forbidden: {host}")
    try:
        allowed = public_address(host)
    except ValueError:
        labels = host.split(".")
        allowed = (
            len(host) <= 253 and len(labels) > 1
            and all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                    for label in labels)
            and labels[-1].isalpha()
            and labels[-1] not in {"localhost", "local", "internal", "home", "lan",
                                  "test", "invalid", "example"}
        )
    if not allowed:
        raise LibraryError(f"Local, private, reserved, or malformed host is forbidden: {host}")
    if resolve:
        public_endpoints(host)
    return host


def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryError(f"Cannot read manifest {path}: {exc}") from exc
    if (not isinstance(data, dict) or type(data.get("schemaVersion")) is not int
            or data["schemaVersion"] != 1 or not isinstance(data.get("sources"), list)):
        raise LibraryError("Manifest must have schemaVersion 1 and a sources array")
    source_ids = set()
    for source in data["sources"]:
        if not isinstance(source, dict):
            raise LibraryError("Each source must be an object")
        source_id = checked_id(source.get("id"))
        if source_id in source_ids:
            raise LibraryError(f"Duplicate source ID: {source_id}")
        source_ids.add(source_id)
        for key in ("title", "institution", "license", "description"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise LibraryError(f"{source_id}: {key} must be a nonempty string")
        authors = source.get("authors")
        if not ((isinstance(authors, str) and authors.strip())
                or (isinstance(authors, list) and authors
                    and all(isinstance(author, str) and author.strip() for author in authors))):
            raise LibraryError(f"{source_id}: authors must be a nonempty string or array of strings")
        for key in ("url", "licenseUrl"):
            checked_url(source.get(key))
        downloads = source.get("downloads")
        if not isinstance(downloads, list):
            raise LibraryError(f"{source_id}: downloads must be an array (use [] when unavailable)")
        download_ids = set()
        for download in downloads:
            if not isinstance(download, dict):
                raise LibraryError(f"{source_id}: each download must be an object")
            download_id = checked_id(download.get("id"))
            if download_id in download_ids:
                raise LibraryError(f"{source_id}: duplicate download ID: {download_id}")
            download_ids.add(download_id)
            if (not isinstance(download.get("format"), str)
                    or download["format"] not in {"pdf", "epub"}):
                raise LibraryError(f"{source_id}/{download_id}: only PDF and EPUB are supported")
            checked_url(download.get("url"))
            if "licenseReviewed" in download and type(download["licenseReviewed"]) is not bool:
                raise LibraryError(f"{source_id}/{download_id}: licenseReviewed must be a boolean")
            if "sha256" in download and (
                    not isinstance(download["sha256"], str)
                    or not SHA_PATTERN.fullmatch(download["sha256"])):
                raise LibraryError(f"{source_id}/{download_id}: invalid pinned SHA-256")
    return data["sources"]


def blocked_reason(source, download, allow_noncommercial=False, downloading=True):
    if source["license"] not in LICENSES:
        return f"unsupported license {source['license']!r}"
    if download.get("licenseReviewed") is not True:
        return "download license has not been reviewed"
    if downloading and "-NC" in source["license"] and not allow_noncommercial:
        return "noncommercial license requires --allow-noncommercial"
    return None


def output_root(output):
    root = Path(output).expanduser().resolve()
    assets = (ROOT / "assets").resolve()
    if root == assets or assets in root.parents:
        raise LibraryError("Books must not be downloaded into Flutter assets; use content-cache")
    return root


def cache_paths(root, source, download):
    folder = root / checked_id(source["id"])
    name = checked_id(download["id"]) + "." + download["format"]
    path = folder / name
    receipt = folder / (name + ".receipt.json")
    for candidate in (folder, path, receipt):
        if candidate.is_symlink():
            raise LibraryError(f"Refusing symlink in cache: {candidate}")
    return path, receipt


def attribution(source, download):
    return {
        "schemaVersion": 1,
        "sourceId": source["id"],
        "downloadId": download["id"],
        "format": download["format"],
        "url": download["url"],
        "sourceUrl": source["url"],
        "title": source["title"],
        "institution": source["institution"],
        "authors": source["authors"],
        "license": source["license"],
        "licenseUrl": source["licenseUrl"],
    }


def validate_magic(path, file_format):
    with path.open("rb") as stream:
        magic = stream.read(8)
    if file_format == "pdf":
        if not magic.startswith(b"%PDF-"):
            raise LibraryError("Invalid PDF signature (possibly an HTML error page)")
        return
    if not magic.startswith(b"PK\x03\x04"):
        raise LibraryError("Invalid EPUB ZIP signature")
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            mimetypes = [entry for entry in entries if entry.filename == "mimetype"]
            if (len(mimetypes) != 1 or entries[0] != mimetypes[0]
                    or mimetypes[0].compress_type != zipfile.ZIP_STORED
                    or mimetypes[0].file_size != len(b"application/epub+zip")):
                raise LibraryError("EPUB must start with an uncompressed application/epub+zip mimetype")
            with archive.open(mimetypes[0]) as stream:
                if stream.read(64) != b"application/epub+zip":
                    raise LibraryError("Invalid EPUB mimetype")
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, NotImplementedError) as exc:
        raise LibraryError(f"Invalid EPUB archive: {exc}") from exc


def digest_file(path):
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise LibraryError(f"Cache entry is not a regular file: {path}")
        while True:
            chunk = stream.read(min(65536, MAX_BYTES - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise LibraryError(f"Book exceeds the {MAX_BYTES}-byte size limit")
            digest.update(chunk)
    if total == 0:
        raise LibraryError("Empty book")
    return digest.hexdigest(), total


def verify_cached(root, source, download):
    path, receipt_path = cache_paths(root, source, download)
    if not path.is_file() or not receipt_path.is_file():
        raise LibraryError(f"Missing book or receipt: {path}")
    try:
        if receipt_path.stat().st_size > 65536:
            raise LibraryError(f"Oversized receipt: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryError(f"Invalid receipt: {receipt_path}: {exc}") from exc
    if not isinstance(receipt, dict):
        raise LibraryError(f"Invalid receipt object: {receipt_path}")
    for key, expected in attribution(source, download).items():
        if receipt.get(key) != expected:
            raise LibraryError(f"Receipt metadata mismatch for {key}: {receipt_path}")
    checked_url(receipt.get("finalUrl"), original_host=checked_url(download["url"]))
    try:
        timestamp = datetime.fromisoformat(receipt["retrievedAt"])
        if timestamp.tzinfo is None:
            raise ValueError("timezone required")
    except (KeyError, TypeError, ValueError) as exc:
        raise LibraryError(f"Invalid retrieval timestamp: {receipt_path}") from exc
    digest, total = digest_file(path)
    if (type(receipt.get("bytes")) is not int or receipt["bytes"] != total
            or receipt.get("sha256") != digest):
        raise LibraryError(f"Corrupt cache: receipt size/checksum mismatch: {path}")
    if download.get("sha256") and digest != download["sha256"].lower():
        raise LibraryError(f"Corrupt cache: pinned SHA-256 mismatch: {path}")
    validate_magic(path, download["format"])
    return receipt


class SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, original_host):
        super().__init__()
        self.original_host = original_host

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        checked_url(newurl, original_host=self.original_host, resolve=True)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def public_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    # Connect to the validated numeric address, not a second DNS lookup. TLS still
    # checks the original hostname in HTTPSConnection, preventing DNS rebinding.
    last_error = None
    for family, socktype, proto, _, endpoint in public_endpoints(*address):
        connection = socket.socket(family, socktype, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                connection.settimeout(timeout)
            if source_address:
                connection.bind(source_address)
            connection.connect(endpoint)
            return connection
        except OSError as exc:
            last_error = exc
            connection.close()
    raise last_error or OSError("No public endpoint available")


class PublicHTTPSConnection(HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = public_connection


class PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=self._context)


def download_book(root, source, download, allow_noncommercial=False):
    reason = blocked_reason(source, download, allow_noncommercial)
    if reason:
        raise LibraryError(reason)
    path, receipt_path = cache_paths(root, source, download)
    if path.exists() or receipt_path.exists():
        verify_cached(root, source, download)
        return "Reused verified cache", path
    host = checked_url(download["url"], resolve=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_paths(root, source, download)
    partials = []
    started = time.monotonic()
    try:
        opener = build_opener(ProxyHandler({}), PublicHTTPSHandler(), SafeRedirectHandler(host))
        request = Request(download["url"], headers={
            "User-Agent": "FluentContentLibrary/1.0",
            "Accept": "application/pdf, application/epub+zip",
            "Accept-Encoding": "identity",
        })
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise LibraryError(f"Unexpected HTTP status: {response.status}")
            final_url = response.geturl()
            checked_url(final_url, original_host=host)
            encoding = response.headers.get("Content-Encoding", "identity")
            if encoding.lower() != "identity":
                raise LibraryError(f"Unsupported Content-Encoding: {encoding}")
            declared = response.headers.get("Content-Length")
            if declared is not None:
                try:
                    declared = int(declared)
                except ValueError as exc:
                    raise LibraryError("Invalid Content-Length") from exc
                if declared < 1 or declared > MAX_BYTES:
                    raise LibraryError(f"Content-Length exceeds size limit or is empty: {declared}")
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix="." + path.name + ".",
                                             suffix=".part", delete=False) as stream:
                staged_book = Path(stream.name)
                partials.append(staged_book)
                digest = hashlib.sha256()
                total = 0
                while True:
                    if time.monotonic() - started > TOTAL_SECONDS:
                        raise LibraryError("Download exceeded total time limit")
                    chunk = response.read1(min(65536, MAX_BYTES - total + 1))
                    if time.monotonic() - started > TOTAL_SECONDS:
                        raise LibraryError("Download exceeded total time limit")
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise LibraryError(f"Book exceeds the {MAX_BYTES}-byte size limit")
                    digest.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
        if not total or (declared is not None and total != declared):
            raise LibraryError("Empty or interrupted download: Content-Length mismatch")
        validate_magic(staged_book, download["format"])
        checksum = digest.hexdigest()
        if download.get("sha256") and checksum != download["sha256"].lower():
            raise LibraryError("Downloaded book does not match pinned SHA-256")
        receipt = attribution(source, download)
        receipt.update({
            "finalUrl": final_url,
            "sha256": checksum,
            "bytes": total,
            "retrievedAt": datetime.now(timezone.utc).isoformat(),
        })
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", suffix=".part",
                                         delete=False) as stream:
            staged_receipt = Path(stream.name)
            partials.append(staged_receipt)
            json.dump(receipt, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard links publish complete files atomically without overwriting a cache
        # entry created by a concurrent invocation (unlike os.replace).
        os.link(staged_book, path)
        try:
            os.link(staged_receipt, receipt_path)
        except BaseException:
            path.unlink()
            raise
        return "Downloaded", path
    except (OSError, HTTPException, HTTPError, URLError) as exc:
        raise LibraryError(f"Download failed; existing cache was not overwritten: {exc}") from exc
    finally:
        for partial in partials:
            partial.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    def options(target, suppressed=False):
        default = argparse.SUPPRESS if suppressed else None
        target.add_argument("--manifest", type=Path,
                            default=argparse.SUPPRESS if suppressed else DEFAULT_MANIFEST)
        target.add_argument("--output", type=Path,
                            default=argparse.SUPPRESS if suppressed else DEFAULT_OUTPUT)
        target.add_argument("--source", default=default, help="select one source ID")
        target.add_argument("--allow-noncommercial", action="store_true",
                            default=argparse.SUPPRESS if suppressed else False,
                            help="explicitly accept noncommercial restrictions for downloads")

    options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
            ("list", "list indexed sources without network access"),
            ("download", "explicitly fetch reviewed, permitted books into the local cache"),
            ("verify", "check cached files and receipts without network access")):
        options(subparsers.add_parser(name, help=help_text), suppressed=True)
    args = parser.parse_args(argv)
    try:
        sources = load_manifest(args.manifest)
        if args.source is not None:
            checked_id(args.source)
            sources = [source for source in sources if source["id"] == args.source]
            if not sources:
                raise LibraryError(f"Unknown source: {args.source}")
        root = output_root(args.output)
        failures = 0
        if not sources:
            print("No sources indexed; no books are available.")
            return 0 if args.command == "list" else 1
        for source in sources:
            print(f"{source['id']}: {source['title']} — {source['institution']} [{source['license']}]")
            if not source["downloads"]:
                print("  Unavailable: no reviewed downloadable book is indexed; nothing downloaded.")
                failures += args.command != "list"
                continue
            for download in source["downloads"]:
                label = f"{source['id']}/{download['id']}"
                if args.command == "list":
                    reason = blocked_reason(source, download, args.allow_noncommercial)
                    print(f"  {download['id']} ({download['format']}): "
                          f"{'Blocked: ' + reason if reason else 'Available for explicit download'}")
                    continue
                try:
                    reason = blocked_reason(source, download, args.allow_noncommercial,
                                            downloading=args.command == "download")
                    if reason:
                        raise LibraryError(f"Blocked: {reason}")
                    if args.command == "verify":
                        verify_cached(root, source, download)
                        print(f"  Verified: {label}")
                    else:
                        status, path = download_book(root, source, download, args.allow_noncommercial)
                        print(f"  {status}: {path}")
                except (LibraryError, OSError) as exc:
                    print(f"  Error: {label}: {exc}", file=sys.stderr)
                    failures += 1
        return 1 if failures else 0
    except (LibraryError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; partial downloads removed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
