# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the real CLI codecs with private temporary files and no visible GUI."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class CommandLineCodecTests(unittest.TestCase):
    executable = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="BeatQuay-codec-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def command(self, operation, path):
        return subprocess.run([self.executable, operation, str(path)], capture_output=True,
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
        original = self.root / "音符-é.mmp"
        contents = b'<lmms-project version="1.0" type="song"><head bpm="120"/><song/></lmms-project>'
        original.write_bytes(contents)
        compressed = self.command("compress", original)
        self.assertEqual(0, compressed.returncode, compressed.stderr.decode(errors="replace"))
        self.assertGreater(len(compressed.stdout), 4)
        packed = self.root / "音符-é.mmpz"
        packed.write_bytes(compressed.stdout)
        dumped = self.command("dump", packed)
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
