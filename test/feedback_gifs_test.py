"""Offline unit and FFmpeg integration tests for the feedback GIF generator."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tool import generate_feedback_gifs as generator


class FeedbackGifsTest(unittest.TestCase):
    def test_automatic_clips_include_remainder(self):
        clips = generator.make_clips(7, 10, category="correct", segment_duration=3)
        self.assertEqual([(c["start"], c["end"]) for c in clips], [(0, 3), (3, 6), (6, 7)])
        self.assertEqual(clips[0]["file"], "correct_001.gif")

    def test_subframe_remainder_is_merged(self):
        clips = generator.make_clips(3.05, 10, category="incorrect", segment_duration=3)
        self.assertEqual([(c["start"], c["end"]) for c in clips], [(0, 3.05)])

    def test_manual_clips_keep_categories_and_allow_gaps(self):
        segments = [
            {"id": "acerto", "category": "correct", "start": 0, "end": 1},
            {"id": "erro", "category": "incorrect", "start": 2, "end": 3},
        ]
        clips = generator.make_clips(4, 10, segments)
        self.assertEqual([c["category"] for c in clips], ["correct", "incorrect"])
        self.assertNotIn("file", segments[0])

    def test_invalid_manual_clips(self):
        valid = {"id": "acerto", "category": "correct", "start": 0, "end": 1}
        invalid = [
            [], {}, ["bad"], [valid, valid],
            *[[dict(valid, id=value)] for value in ("../escape", "full", "X", "", None)],
            [dict(valid, category="other")], [dict(valid, start=True)],
            [dict(valid, start=-1)], [dict(valid, end=5)],
            [dict(valid, end=0)], [dict(valid, end=0.01)],
            [dict(valid, end="1")], [dict(valid, end=float("nan"))],
            [dict(valid, end=float("inf"))],
        ]
        for segments in invalid:
            with self.subTest(segments=segments), self.assertRaises(generator.GenerationError):
                generator.make_clips(4, 10, segments)

    def test_invalid_automatic_clips(self):
        for duration in (0, -1, float("nan"), float("inf"), 0.01):
            with self.subTest(duration=duration), self.assertRaises(generator.GenerationError):
                generator.make_clips(4, 10, category="correct", segment_duration=duration)
        with self.assertRaises(generator.GenerationError):
            generator.make_clips(4000, 10, category="correct")
        with self.assertRaises(generator.GenerationError):
            generator.make_clips(4, 10)

    def test_probe_requires_video_and_finite_duration(self):
        for metadata in ({"streams": []}, {"streams": [{"duration": "N/A"}]},
                         {"streams": [{"duration": "inf"}]}):
            with mock.patch.object(generator, "run_media", return_value=json.dumps(metadata)):
                with self.assertRaises(generator.GenerationError):
                    generator.video_duration(Path("/tmp/video.mp4"))

    def test_probe_falls_back_to_format_duration(self):
        metadata = {"streams": [{"duration": "N/A"}], "format": {"duration": "2.5"}}
        with mock.patch.object(generator, "run_media", return_value=json.dumps(metadata)):
            self.assertEqual(generator.video_duration(Path("/tmp/video.mp4")), 2.5)

    def test_help_without_ffmpeg(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
            generator.main(["--help"])
        self.assertEqual(error.exception.code, 0)

    def test_missing_input_and_malformed_json_report_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            segments = root / "segments.json"
            for content in ("{invalid", "null", "{}"):
                segments.write_text(content, encoding="utf-8")
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(generator.main([
                        str(root / "missing.mp4"), "--output", str(root / "out"),
                        "--segments", str(segments),
                    ]), 1)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(generator.main([
                    str(root / "missing.mp4"), "--output", str(root / "out"),
                    "--category", "correct",
                ]), 1)
            self.assertFalse((root / "out").exists())

    def test_missing_ffmpeg_and_conversion_failure_leave_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "video.mp4"
            video.touch()
            output = root / "out"
            with mock.patch.object(generator.shutil, "which", return_value=None):
                with self.assertRaisesRegex(generator.GenerationError, "Instale FFmpeg"):
                    generator.generate(video, output, category="correct")
            with mock.patch.object(generator.shutil, "which", return_value="/usr/bin/tool"), \
                    mock.patch.object(generator, "video_duration", return_value=2), \
                    mock.patch.object(generator, "run_media",
                                      side_effect=generator.GenerationError("conversion failed")):
                with self.assertRaises(generator.GenerationError):
                    generator.generate(video, output, category="correct")
            self.assertEqual(list(root.iterdir()), [video])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
class FeedbackGifsIntegrationTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="fluent-gifs-")
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.video = self.root / "video with spaces.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=96x64:rate=10:duration=2.5",
            "-c:v", "mpeg4", str(self.video),
        ], check=True, capture_output=True)

    def assert_gif(self, path, duration):
        self.assertIn(path.read_bytes()[:6], (b"GIF87a", b"GIF89a"))
        info = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ], check=True, capture_output=True, text=True).stdout)
        self.assertEqual(info["streams"][0]["width"], 80)
        self.assertGreater(int(info["streams"][0]["nb_frames"]), 1)
        self.assertAlmostEqual(float(info["format"]["duration"]), duration, delta=0.11)

    def test_full_gif_and_automatic_clips(self):
        original = self.video.read_bytes()
        output = self.root / "automatic"
        catalog = generator.generate(
            self.video, output, category="correct", segment_duration=1, width=80,
        )
        self.assertEqual(len(catalog["clips"]), 3)
        self.assert_gif(output / "full.gif", 2.5)
        for clip in catalog["clips"]:
            self.assert_gif(output / clip["file"], clip["end"] - clip["start"])
        self.assertEqual(json.loads((output / "catalog.json").read_text()), catalog)
        self.assertEqual(self.video.read_bytes(), original)
        with self.assertRaisesRegex(generator.GenerationError, "já existe"):
            generator.generate(self.video, output, category="correct")

    def test_manual_cuts_from_cli(self):
        segments = self.root / "segments.json"
        segments.write_text(json.dumps([
            {"id": "acerto", "category": "correct", "start": 0, "end": 0.8},
            {"id": "erro", "category": "incorrect", "start": 1.2, "end": 2.5},
        ]))
        output = self.root / "manual"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(generator.main([
                str(self.video), "--output", str(output),
                "--segments", str(segments), "--width", "80",
            ]), 0)
        self.assert_gif(output / "acerto.gif", 0.8)
        self.assert_gif(output / "erro.gif", 1.3)


if __name__ == "__main__":
    unittest.main()
