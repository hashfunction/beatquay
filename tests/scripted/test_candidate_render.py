# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
import array
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from candidate_render import inspect_wave
import candidate_render


class RenderInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="BeatQuay-wave-check-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "render.wav"

    def write_wave(self, audible):
        with wave.open(str(self.path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(44100)
            output.writeframes(array.array("h", [1000 if audible else 0, -1000 if audible else 0] * 88200).tobytes())

    def test_valid_audible_pcm_reports_real_frames_and_peak(self):
        self.write_wave(True)
        result = inspect_wave(self.path)
        self.assertEqual(88200, result["frames"])
        self.assertEqual(1000, result["peak_pcm16"])
        self.assertEqual(2.0, result["duration_seconds"])

    def test_nonempty_silent_wave_is_rejected(self):
        self.write_wave(False)
        with self.assertRaisesRegex(ValueError, "silent"):
            inspect_wave(self.path)

    def test_empty_output_is_rejected(self):
        self.path.touch()
        with self.assertRaisesRegex(ValueError, "empty"):
            inspect_wave(self.path)


class RenderErrorInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="BeatQuay-render-error-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "original 音符.mmp"
        self.source.write_bytes(b"original project")
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.destination = self.root / "blocked 音符.wav"
        self.destination.mkdir()
        (self.destination / "keep.txt").write_bytes(b"keep")
        self.result = subprocess.CompletedProcess([], 1, b"", b"Render failed or cancelled:\n" + str(self.destination).encode("utf-8") + b": expected error")

    def inspect(self):
        return candidate_render.inspect_render_error(self.result, self.source, self.source_hash, self.destination, b"keep")

    def test_typed_failure_exit_with_preserved_files_is_accepted(self):
        report = self.inspect()
        self.assertEqual(1, report["exit_code"])
        self.assertTrue(report["original_unchanged"])
        self.assertTrue(report["blocked_destination_unchanged"])

    def test_success_exit_is_rejected(self):
        self.result.returncode = 0
        with self.assertRaisesRegex(ValueError, "exit"):
            self.inspect()

    def test_crash_exit_is_rejected(self):
        self.result.returncode = 3221225477
        with self.assertRaisesRegex(ValueError, "exit"):
            self.inspect()

    def test_constructor_exit_without_typed_completion_is_rejected(self):
        self.result.stderr = b"Could not open file for writing"
        with self.assertRaisesRegex(ValueError, "terminal result"):
            self.inspect()

    def test_failure_for_an_unrelated_path_is_rejected(self):
        self.result.stderr = b"Render failed or cancelled: different.wav"
        with self.assertRaisesRegex(ValueError, "destination"):
            self.inspect()

    def test_failure_for_a_path_with_the_same_prefix_is_rejected(self):
        self.result.stderr = b"Render failed or cancelled:\n" + str(self.destination).encode("utf-8") + b".different: failed"
        with self.assertRaisesRegex(ValueError, "destination"):
            self.inspect()

    def test_changed_source_is_rejected(self):
        self.source.write_bytes(b"changed project")
        with self.assertRaisesRegex(ValueError, "original"):
            self.inspect()

    def test_changed_sentinel_is_rejected(self):
        (self.destination / "keep.txt").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "destination"):
            self.inspect()

    def test_unexpected_destination_file_is_rejected(self):
        (self.destination / "unexpected.wav").write_bytes(b"unexpected")
        with self.assertRaisesRegex(ValueError, "destination"):
            self.inspect()

    def test_replaced_destination_is_rejected(self):
        (self.destination / "keep.txt").unlink()
        self.destination.rmdir()
        self.destination.write_bytes(b"replaced")
        with self.assertRaisesRegex(ValueError, "destination"):
            self.inspect()


if __name__ == "__main__": unittest.main()
