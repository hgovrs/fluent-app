"""Network-free regression tests for the explicit book acquisition CLI."""

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock
from urllib.request import Request
import zipfile

from tool import content_library as library


PDF = b"%PDF-1.7\nA small test fixture, not a complete textbook.\n%%EOF\n"
PUBLIC_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


class Response(io.BytesIO):
    def __init__(self, body=PDF, url="https://books.example.org/book.pdf", headers=None, status=200):
        super().__init__(body)
        self.url = url
        self.headers = {} if headers is None else headers
        self.status = status

    def geturl(self):
        return self.url


class ContentLibraryTest(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="fluent-content-library-")
        self.addCleanup(self.workspace.cleanup)
        self.directory = Path(self.workspace.name)
        self.output = self.directory / "cache"
        self.manifest = self.directory / "sources.json"
        self.source = {
            "id": "example-book",
            "title": "Example Book",
            "institution": "Example University",
            "authors": ["Example Author"],
            "url": "https://books.example.org/course",
            "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
            "description": "A reviewed book for tests.",
            "limitations": "The course website itself is not downloaded.",
            "downloads": [{
                "id": "textbook",
                "url": "https://books.example.org/book.pdf",
                "format": "pdf",
                "licenseReviewed": True,
            }],
        }
        self.download = self.source["downloads"][0]
        self.dns = self.enterContext(mock.patch.object(library.socket, "getaddrinfo",
                                                       return_value=PUBLIC_DNS))
        self.opener_factory = self.enterContext(mock.patch.object(library, "build_opener"))
        self.opener = self.opener_factory.return_value
        self.opener.open.side_effect = AssertionError("Unexpected network request")

    def write_manifest(self, sources=None):
        self.manifest.write_text(json.dumps({
            "schemaVersion": 1,
            "sources": [self.source] if sources is None else sources,
        }), encoding="utf-8")

    def cli(self, command, *args):
        self.write_manifest()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = library.main([command, "--manifest", str(self.manifest),
                                   "--output", str(self.output), *args])
        return result, stdout.getvalue() + stderr.getvalue()

    def fetch(self, body=PDF, **kwargs):
        self.opener.open.side_effect = None
        self.opener.open.return_value = Response(body, **kwargs)
        return library.download_book(self.output, self.source, self.download)

    def paths(self):
        return library.cache_paths(self.output, self.source, self.download)

    def assert_no_book_or_partials(self):
        if self.output.exists():
            self.assertEqual([], [path for path in self.output.rglob("*") if path.is_file()])

    def test_defaults_are_repository_relative(self):
        self.assertEqual(library.ROOT / "assets/content/sources.json", library.DEFAULT_MANIFEST)
        self.assertEqual(library.ROOT / "content-cache", library.DEFAULT_OUTPUT)

    def test_list_is_network_free(self):
        result, text = self.cli("list")
        self.assertEqual(0, result)
        self.assertIn("Example Book", text)
        self.assertIn("Available for explicit download", text)
        self.dns.assert_not_called()
        self.opener.open.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_string_authors_are_preserved_in_receipts(self):
        self.source["authors"] = "Example Author"
        self.write_manifest()
        library.load_manifest(self.manifest)
        self.fetch()
        receipt = library.verify_cached(self.output, self.source, self.download)
        self.assertEqual("Example Author", receipt["authors"])

    def test_empty_downloads_stay_indexed_but_are_unavailable(self):
        self.source["downloads"] = []
        for command, expected in (("list", 0), ("download", 1), ("verify", 1)):
            with self.subTest(command=command):
                result, text = self.cli(command, "--source", self.source["id"])
                self.assertEqual(expected, result)
                self.assertIn("Example Book", text)
                self.assertIn("Unavailable", text)
        self.dns.assert_not_called()
        self.opener.open.assert_not_called()

    def test_unknown_source_and_unsafe_selection_fail(self):
        for source_id in ("unknown-book", "../escape"):
            with self.subTest(source_id=source_id):
                result, _ = self.cli("download", "--source", source_id)
                self.assertEqual(1, result)
        self.opener.open.assert_not_called()

    def test_nc_requires_explicit_opt_in(self):
        for license_name in ("CC BY-NC 4.0", "CC BY-NC-SA 4.0"):
            self.source["license"] = license_name
            result, text = self.cli("download")
            self.assertEqual(1, result)
            self.assertIn("--allow-noncommercial", text)
        self.opener.open.assert_not_called()
        self.opener.open.side_effect = None
        self.opener.open.return_value = Response()
        result, _ = self.cli("download", "--allow-noncommercial")
        self.assertEqual(0, result)
        self.opener.open.reset_mock()
        result, _ = self.cli("verify")
        self.assertEqual(0, result)
        self.opener.open.assert_not_called()

    def test_other_licenses_are_blocked_even_with_opt_in(self):
        self.source["license"] = "All rights reserved"
        result, text = self.cli("download", "--allow-noncommercial")
        self.assertEqual(1, result)
        self.assertIn("unsupported license", text)
        self.opener.open.assert_not_called()

    def test_missing_and_false_review_are_blocked(self):
        for reviewed in (None, False):
            if reviewed is None:
                self.download.pop("licenseReviewed")
            else:
                self.download["licenseReviewed"] = reviewed
            for command in ("download", "verify"):
                result, text = self.cli(command, "--allow-noncommercial")
                self.assertEqual(1, result)
                self.assertIn("not been reviewed", text)
        self.opener.open.assert_not_called()

    def test_manifest_rejects_unsafe_source_and_download_ids(self):
        for item in (self.source, self.download):
            previous = item["id"]
            for bad_id in ("../escape", "a/b", "/absolute", ".", "Upper", "", "a\\b", "a" * 81):
                with self.subTest(bad_id=bad_id):
                    item["id"] = bad_id
                    self.write_manifest()
                    with self.assertRaises(library.LibraryError):
                        library.load_manifest(self.manifest)
            item["id"] = previous

    def test_manifest_rejects_duplicates_and_bad_review_types(self):
        self.write_manifest([self.source, copy.deepcopy(self.source)])
        with self.assertRaisesRegex(library.LibraryError, "Duplicate source"):
            library.load_manifest(self.manifest)
        self.source["downloads"].append(copy.deepcopy(self.download))
        self.write_manifest()
        with self.assertRaisesRegex(library.LibraryError, "duplicate download"):
            library.load_manifest(self.manifest)
        self.source["downloads"].pop()
        self.download["licenseReviewed"] = "true"
        self.write_manifest()
        with self.assertRaisesRegex(library.LibraryError, "must be a boolean"):
            library.load_manifest(self.manifest)

    def test_manifest_rejects_unsupported_format_and_digest(self):
        self.download["format"] = "exe"
        self.write_manifest()
        with self.assertRaises(library.LibraryError):
            library.load_manifest(self.manifest)
        self.download["format"] = "pdf"
        self.download["sha256"] = "not-a-hash"
        self.write_manifest()
        with self.assertRaises(library.LibraryError):
            library.load_manifest(self.manifest)

    def test_private_local_and_unsafe_urls_are_rejected(self):
        for url in (
                "http://books.example.org/book.pdf",
                "https://reader@books.example.org/book.pdf",
                "https://books.example.org:8443/book.pdf",
                "https://127.0.0.1/book.pdf", "https://10.0.0.1/book.pdf",
                "https://169.254.169.254/book.pdf", "https://[::1]/book.pdf",
                "https://[fc00::1]/book.pdf", "https://224.0.0.1/book.pdf",
                "https://localhost/book.pdf", "https://host.local/book.pdf",
                "https://internal/book.pdf", "file:///book.pdf",
                "https://2130706433/book.pdf", "https://127.1/book.pdf",
                "https://books.example.org/book.pdf#fragment",
                "https://books.example.org/white space",
                "https://books.example.org\\@localhost/book.pdf"):
            with self.subTest(url=url), self.assertRaises(library.LibraryError):
                library.checked_url(url)

    def test_dns_private_or_mixed_answers_are_rejected(self):
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))
        for answers in ([private], PUBLIC_DNS + [private], []):
            self.dns.return_value = answers
            with self.assertRaises(library.LibraryError):
                library.checked_url(self.download["url"], resolve=True)
        self.opener.open.assert_not_called()

    def test_connection_pins_validated_address_and_keeps_tls_hostname(self):
        with mock.patch.object(library.socket, "socket") as sockets:
            connection = library.public_connection(("books.example.org", 443), timeout=30)
            self.assertIs(connection, sockets.return_value)
            connection.connect.assert_called_once_with(("93.184.216.34", 443))
        https = library.PublicHTTPSConnection("books.example.org")
        self.assertEqual("books.example.org", https.host)
        self.assertIs(https._create_connection, library.public_connection)
        self.assertTrue(https._context.check_hostname)

    def test_rebinding_is_rejected_before_connecting(self):
        self.dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with mock.patch.object(library.socket, "socket") as sockets:
            with self.assertRaises(library.LibraryError):
                library.public_connection(("books.example.org", 443), timeout=30)
            sockets.assert_not_called()

    def test_redirects_allow_only_same_public_https_host(self):
        handler = library.SafeRedirectHandler("books.example.org")
        request = Request(self.download["url"])
        for url in ("http://books.example.org/book.pdf", "https://evil.example.org/book.pdf",
                    "https://books.example.org:444/book.pdf", "https://127.0.0.1/book.pdf"):
            with self.subTest(url=url), self.assertRaises(library.LibraryError):
                handler.redirect_request(request, None, 302, "Found", {}, url)
        redirect = handler.redirect_request(request, None, 302, "Found", {},
                                            "https://books.example.org/new-book.pdf")
        self.assertEqual("https://books.example.org/new-book.pdf", redirect.full_url)

    def test_unexpected_final_response_host_is_rejected(self):
        with self.assertRaisesRegex(library.LibraryError, "unexpected host"):
            self.fetch(url="https://other.example.org/book.pdf")
        self.assert_no_book_or_partials()

    def test_valid_pdf_receipt_and_offline_reuse(self):
        status, path = self.fetch(headers={"Content-Length": str(len(PDF))})
        self.assertEqual("Downloaded", status)
        self.assertEqual(PDF, path.read_bytes())
        receipt = library.verify_cached(self.output, self.source, self.download)
        self.assertEqual(hashlib.sha256(PDF).hexdigest(), receipt["sha256"])
        self.assertEqual(len(PDF), receipt["bytes"])
        for key, value in library.attribution(self.source, self.download).items():
            self.assertEqual(value, receipt[key])
        self.assertEqual(self.download["url"], receipt["finalUrl"])
        self.assertEqual(self.source["url"], receipt["sourceUrl"])
        self.assertIn("+00:00", receipt["retrievedAt"])
        self.opener.open.reset_mock()
        self.dns.reset_mock()
        self.assertEqual("Reused verified cache", library.download_book(
            self.output, self.source, self.download)[0])
        self.assertEqual(0, self.cli("verify")[0])
        self.opener.open.assert_not_called()
        self.dns.assert_not_called()
        self.assertEqual([], list(self.output.rglob("*.part")))

    def test_corrupted_cache_fails_verification_and_is_not_overwritten(self):
        self.fetch()
        path, _ = self.paths()
        corrupt = PDF + b"tampered"
        path.write_bytes(corrupt)
        self.opener.open.reset_mock()
        self.assertEqual(1, self.cli("verify")[0])
        result, text = self.cli("download")
        self.assertEqual(1, result)
        self.assertIn("checksum mismatch", text)
        self.assertEqual(corrupt, path.read_bytes())
        self.opener.open.assert_not_called()

    def test_receipt_metadata_tampering_is_rejected(self):
        self.fetch()
        _, receipt_path = self.paths()
        original = json.loads(receipt_path.read_text())
        for key, value in (("license", "CC0"), ("authors", ["Wrong author"]),
                           ("title", "Wrong book"), ("url", "https://other.example.org/book.pdf"),
                           ("sourceUrl", "https://other.example.org/course"),
                           ("finalUrl", "https://other.example.org/book.pdf"),
                           ("retrievedAt", "not-a-date"), ("bytes", True), ("sha256", "0" * 64)):
            with self.subTest(key=key):
                receipt = dict(original, **{key: value})
                receipt_path.write_text(json.dumps(receipt))
                with self.assertRaises(library.LibraryError):
                    library.verify_cached(self.output, self.source, self.download)

    def test_missing_book_or_receipt_never_triggers_network_in_verify(self):
        result, text = self.cli("verify")
        self.assertEqual(1, result)
        self.assertIn("Missing", text)
        self.assertFalse(self.output.exists())
        self.dns.assert_not_called()
        self.opener.open.assert_not_called()
        self.fetch()
        path, receipt_path = self.paths()
        receipt_path.unlink()
        self.opener.open.reset_mock()
        self.assertEqual(1, self.cli("download")[0])
        self.assertTrue(path.exists())
        self.opener.open.assert_not_called()

    def test_invalid_pdf_html_is_rejected_and_cleaned(self):
        with self.assertRaisesRegex(library.LibraryError, "Invalid PDF"):
            self.fetch(b"<html>Access denied</html>")
        self.assert_no_book_or_partials()

    @staticmethod
    def epub(mimetype=b"application/epub+zip"):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
            archive.writestr("EPUB/book.xhtml", "<html>A test book</html>")
        return stream.getvalue()

    def test_epub_magic_and_mimetype_are_validated_without_extraction(self):
        self.download["format"] = "epub"
        self.fetch(self.epub())
        library.verify_cached(self.output, self.source, self.download)
        self.assertFalse((self.output / "EPUB").exists())
        self.assertEqual(2, len([path for path in self.output.rglob("*") if path.is_file()]))

    def test_invalid_epub_is_rejected(self):
        self.download["format"] = "epub"
        for body in (b"not a zip", b"PK\x03\x04broken", self.epub(b"text/plain")):
            with self.subTest(body=body[:20]), self.assertRaises(library.LibraryError):
                self.fetch(body)
            self.assert_no_book_or_partials()

    def test_size_limit_checks_headers_and_stream(self):
        with mock.patch.object(library, "MAX_BYTES", len(PDF) - 1):
            for headers in ({}, {"Content-Length": str(len(PDF))}):
                with self.subTest(headers=headers), self.assertRaises(library.LibraryError):
                    self.fetch(headers=headers)
                self.assert_no_book_or_partials()

    def test_truncated_empty_and_encoded_responses_are_rejected(self):
        for body, headers in ((PDF, {"Content-Length": str(len(PDF) + 1)}),
                              (b"", {}), (PDF, {"Content-Length": "garbage"}),
                              (PDF, {"Content-Encoding": "gzip"})):
            with self.subTest(headers=headers), self.assertRaises(library.LibraryError):
                self.fetch(body, headers=headers)
            self.assert_no_book_or_partials()

    def test_pinned_hash_is_checked_during_download_and_verify(self):
        self.download["sha256"] = "0" * 64
        with self.assertRaisesRegex(library.LibraryError, "pinned SHA-256"):
            self.fetch()
        self.assert_no_book_or_partials()
        self.download["sha256"] = hashlib.sha256(PDF).hexdigest().upper()
        self.fetch()
        library.verify_cached(self.output, self.source, self.download)
        self.download["sha256"] = "0" * 64
        with self.assertRaisesRegex(library.LibraryError, "pinned SHA-256"):
            library.verify_cached(self.output, self.source, self.download)

    def test_interrupted_stream_cleans_atomic_partials(self):
        for error in (OSError("connection interrupted"), KeyboardInterrupt()):
            response = Response()
            response.read1 = mock.Mock(side_effect=[b"%PDF-1.7\n", error])
            self.opener.open.side_effect = None
            self.opener.open.return_value = response
            expected = KeyboardInterrupt if isinstance(error, KeyboardInterrupt) else library.LibraryError
            with self.subTest(error=error), self.assertRaises(expected):
                library.download_book(self.output, self.source, self.download)
            self.assert_no_book_or_partials()

    def test_total_time_limit_cleans_partials(self):
        with mock.patch.object(library.time, "monotonic", side_effect=[0, 0, 121]):
            with self.assertRaisesRegex(library.LibraryError, "total time"):
                self.fetch()
        self.assert_no_book_or_partials()

    def test_receipt_publish_failure_rolls_back_book(self):
        real_link = library.os.link
        calls = 0

        def fail_second_link(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("receipt publication interrupted")
            real_link(source, destination)

        with mock.patch.object(library.os, "link", side_effect=fail_second_link):
            with self.assertRaises(library.LibraryError):
                self.fetch()
        self.assert_no_book_or_partials()

    def test_concurrent_cache_entry_is_not_overwritten(self):
        real_link = library.os.link

        def competing_link(source, destination):
            Path(destination).write_bytes(b"another process")
            real_link(source, destination)

        with mock.patch.object(library.os, "link", side_effect=competing_link):
            with self.assertRaises(library.LibraryError):
                self.fetch()
        self.assertEqual(b"another process", self.paths()[0].read_bytes())
        self.assertEqual([], list(self.output.rglob("*.part")))

    def test_symlink_cache_and_assets_output_are_rejected(self):
        self.output.mkdir()
        (self.output / self.source["id"]).symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(library.LibraryError, "symlink"):
            self.fetch()
        with self.assertRaisesRegex(library.LibraryError, "Flutter assets"):
            library.output_root(library.ROOT / "assets" / "books")
        self.opener.open.assert_not_called()

    def test_non_200_response_is_not_published(self):
        with self.assertRaisesRegex(library.LibraryError, "HTTP status"):
            self.fetch(status=206)
        self.assert_no_book_or_partials()

    def test_options_can_precede_subcommand(self):
        self.write_manifest()
        with contextlib.redirect_stdout(io.StringIO()):
            result = library.main(["--manifest", str(self.manifest), "--source",
                                   self.source["id"], "list"])
        self.assertEqual(0, result)
        self.opener.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
