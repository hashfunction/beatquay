# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
import array
from pathlib import Path
import tempfile
import unittest
import wave

from candidate_render import inspect_wave


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


if __name__ == "__main__": unittest.main()
