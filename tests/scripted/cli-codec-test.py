# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the real CLI codecs with private temporary files and no visible GUI."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zlib


class CommandLineCodecTests(unittest.TestCase):
    executable = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="BeatQuay-codec-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def command(self, *arguments):
        # A sequence lets subprocess quote Windows paths; no shell parses filenames.
        return subprocess.run([self.executable, *(str(arg) for arg in arguments)], capture_output=True,
                              timeout=20, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))

    def test_missing_dump_input_reports_failure_without_output(self):
        result = self.command("dump", self.root / "missing-project.mmpz")
        self.assertNotEqual(0, result.returncode, result.stderr.decode(errors="replace"))
        self.assertEqual(b"", result.stdout)
        self.assertIn(b"missing-project.mmpz", result.stderr)

    def test_missing_compress_input_reports_failure_without_output(self):
        result = self.command("compress", self.root / "missing-project.mmp")
        self.assertNotEqual(0, result.returncode, result.stderr.decode(errors="replace"))
        self.assertEqual(b"", result.stdout)
        self.assertIn(b"missing-project.mmp", result.stderr)

    def test_unicode_input_round_trip_preserves_original(self):
        self.assert_round_trip("音符-é")

    def test_quoted_space_and_apostrophe_paths_preserve_original(self):
        self.assert_round_trip("音符 é & 'mix'")

    def test_qt_consumed_options_keep_unicode_file_argument(self):
        # Regression boundary: reading pre-Qt arguments would see -platform as an
        # application option; rereading narrow argv loses this Windows filename.
        for geometry in ("-qwindowgeometry", "--qwindowgeometry"):
            with self.subTest(geometry=geometry):
                self.assert_round_trip("音符 é", qt_options=("-platform", "offscreen",
                                       geometry, "480x320+10+20", "-style", "Fusion"))

    def test_omitted_codec_input_after_qt_options_reports_failure(self):
        for operation in ("dump", "compress"):
            with self.subTest(operation=operation):
                result = self.command("-platform", "offscreen", operation)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertIn(b"No input file specified", result.stderr)

    def test_empty_codec_input_reports_failure_without_output(self):
        for operation in ("dump", "compress"):
            with self.subTest(operation=operation):
                result = self.command(operation, "")
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertIn(b"Cannot open input file", result.stderr)

    def test_import_final_unicode_argument_reports_requested_missing_file(self):
        # The optional -e lookahead must not read beyond this final argument.
        missing = self.root / "missing 音符 é.mid"
        result = self.command("--import", missing)
        self.assertNotEqual(0, result.returncode)
        self.assertIn(missing.name.encode("utf-8"), result.stdout)

    def assert_round_trip(self, name, qt_options=()):
        original = self.root / f"{name}.mmp"
        contents = b'<lmms-project version="1.0" type="song"><head bpm="120"/><song/></lmms-project>'
        original.write_bytes(contents)
        compressed = self.command(*qt_options, "compress", original)
        self.assertEqual(0, compressed.returncode, compressed.stderr.decode(errors="replace"))
        self.assertGreater(len(compressed.stdout), 4)
        # Verify Qt's four-byte length + zlib format independently of its decoder.
        self.assertEqual(len(contents), int.from_bytes(compressed.stdout[:4], "big"))
        self.assertEqual(contents, zlib.decompress(compressed.stdout[4:]))
        packed = self.root / f"{name}.mmpz"
        packed.write_bytes(compressed.stdout)
        dumped = self.command("dump", packed, *qt_options)
        self.assertEqual(0, dumped.returncode, dumped.stderr.decode(errors="replace"))
        self.assertEqual(contents, dumped.stdout.rstrip(b"\r\n"))
        self.assertEqual(contents, original.read_bytes())
        self.assertEqual(compressed.stdout, packed.read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True)
    args = parser.parse_args()
    CommandLineCodecTests.executable = str(Path(args.executable).resolve())
    unittest.main(argv=[__file__])
