# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
import array
import contextlib
import io
import os
from unittest.mock import patch
import starter_render
from pathlib import Path
import shutil
import subprocess
import sys
import json
import xml.etree.ElementTree as ET
import tempfile
import unittest
import wave
from starter_render import verify_installed_inputs, inspect_starter_wave

SOURCE = Path(__file__).resolve().parents[2]

class StarterStageTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(); self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name); self.source = self.root / "source"; self.stage = self.root / "stage"
        for base in (self.source, self.stage):
            shutil.copytree(SOURCE / "data/projects/templates", base / "data/projects/templates")
        (self.source / "distribution").mkdir()
        for name in ("starter-inputs.json", "generate_starters.py"):
            shutil.copyfile(SOURCE / "distribution" / name, self.source / "distribution" / name)

    def test_exact_stage_bytes_are_bound_to_source_inventory(self):
        self.assertEqual(len(verify_installed_inputs(self.source, self.stage)), 4)

    def test_substituted_staged_template_is_rejected(self):
        (self.stage / "data/projects/templates/BeatQuay-Drum-Grid.mpt").write_bytes(b"different")
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_missing_provenance_is_rejected(self):
        (self.stage / "data/projects/templates/BEATQUAY-PROVENANCE.md").unlink()
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_extra_upstream_project_is_rejected(self):
        (self.stage / "data/projects/demos").mkdir()
        (self.stage / "data/projects/demos/uncleared.mmp").write_bytes(b"not approved")
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_source_and_stage_modified_together_are_rejected(self):
        for base in (self.source, self.stage):
            (base / "data/projects/templates/BeatQuay-Drum-Grid.mpt").write_bytes(b"different")
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_well_formed_but_unapproved_music_or_plugin_changes_are_rejected(self):
        name = "data/projects/templates/BeatQuay-Bassline-Sketch.mpt"
        original = (self.source / name).read_bytes()
        for mutation in ("resource", "external_plugin", "effect", "invalid_note"):
            with self.subTest(mutation=mutation):
                root = ET.fromstring(original)
                if mutation == "resource": root.find(".//tripleoscillator").set("userwavefile0", "C:/outside.wav")
                elif mutation == "external_plugin": root.find(".//instrument").set("name", "vestige")
                elif mutation == "effect": ET.SubElement(root.find(".//instrumenttrack"), "effect", name="unapproved")
                else: root.find(".//note").set("key", "999")
                for base in (self.source, self.stage): (base / name).write_bytes(ET.tostring(root))
                with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_generator_source_hash_is_checked(self):
        (self.source / "distribution/generate_starters.py").write_bytes(b"different")
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_symlink_stage_entry_is_rejected(self):
        path = self.stage / "data/projects/templates/BeatQuay-Drum-Grid.mpt"
        path.unlink()
        try: path.symlink_to(self.source / "data/projects/templates/BeatQuay-Drum-Grid.mpt")
        except OSError as error: self.skipTest("Symlink creation unavailable: " + str(error))
        with self.assertRaises(ValueError): verify_installed_inputs(self.source, self.stage)

    def test_actual_cli_reports_failure_without_claiming_native_execution(self):
        evidence = self.root / "evidence"
        command = [sys.executable, str(SOURCE / "tests/scripted/starter_render.py"),
                   "--source", str(self.source), "--stage", str(self.stage),
                   "--work", str(self.root / "owned-work"), "--evidence", str(evidence)]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads((evidence / "starter-render.json").read_text())
        self.assertFalse(report["native_installed_starter_renders_passed"])
        self.assertFalse(report["gui_menu_verified"])
        self.assertIn("error", report)
        self.assertNotIn("renders", report)  # No executable was available or launched.

    def test_actual_cli_preserves_an_existing_evidence_file(self):
        evidence = self.root / "evidence"; evidence.mkdir()
        (evidence / "starter-render.json").write_bytes(b"prior evidence")
        result = subprocess.run([sys.executable, str(SOURCE / "tests/scripted/starter_render.py"),
                                 "--source", str(self.source), "--stage", str(self.stage),
                                 "--work", str(self.root / "owned-work"), "--evidence", str(evidence)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"evidence publication failed", result.stderr)
        self.assertIn(b"qualification error:", result.stderr)
        self.assertEqual((evidence / "starter-render.json").read_bytes(), b"prior evidence")


class StarterAudioTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(); self.addCleanup(self.work.cleanup)
        self.path = Path(self.work.name) / "audio.wav"

    def write(self, duration=20, peak=1000):
        with wave.open(str(self.path), "wb") as stream:
            stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(44100)
            stream.writeframes(array.array("h", [peak, -peak] * round(duration * 44100)).tobytes())

    def test_eight_bar_bass_render_has_actual_expected_duration_and_audible_pcm(self):
        self.write()
        result = inspect_starter_wave(self.path, 8, 108)
        self.assertEqual(result["frames"], 882000)
        self.assertEqual(result["peak_pcm16"], 1000)

    def test_nonempty_silent_audio_is_rejected(self):
        self.write(peak=0)
        with self.assertRaises(ValueError): inspect_starter_wave(self.path, 8, 108)

    def test_clipped_audio_is_rejected(self):
        self.write(peak=32767)
        with self.assertRaises(ValueError): inspect_starter_wave(self.path, 8, 108)

    def test_short_or_long_render_is_rejected(self):
        for duration in (2, 24):
            self.write(duration=duration)
            with self.assertRaises(ValueError): inspect_starter_wave(self.path, 8, 108)

    def test_truncated_frames_are_rejected(self):
        self.write()
        self.path.write_bytes(self.path.read_bytes()[:-100])
        with self.assertRaises(ValueError): inspect_starter_wave(self.path, 8, 108)



class StarterProcessFailureTests(unittest.TestCase):
    setUp = StarterStageTests.setUp

    def invoke_failure(self, *, timeout=False, collide_log=False, collide_report=False, large_output=False):
        # Keep input checks, report handling and the actual subprocess transport.
        # Only replace the unavailable native application with a real Python child.
        executable = self.stage / ("lmms.exe" if os.name == "nt" else "lmms")
        executable.write_bytes(b"explicit test launch adapter, not a native renderer")
        child = self.root / "child.py"
        child.write_text(
            'import sys,time\n'
            'print("retained stdout marker", flush=True)\n'
            'print("primary renderer failure marker", file=sys.stderr, flush=True)\n'
            + ('print("x" * 100000 + " stdout tail marker", flush=True)\n' if large_output else '')
            + ('time.sleep(10)\n' if timeout else 'sys.exit(7)\n')
        )
        evidence = self.root / "evidence"; evidence.mkdir()
        log = evidence / "BeatQuay-Drum-Grid.mpt.render.log"
        report_path = evidence / "starter-render.json"
        if collide_log: log.write_bytes(b"prior log bytes")
        if collide_report: report_path.write_bytes(b"prior report bytes")
        actual_run = subprocess.run
        def launch(arguments, **kwargs):
            self.assertEqual(Path(arguments[0]), executable)
            self.assertEqual(kwargs["timeout"], 180)
            kwargs["timeout"] = 2 if timeout else 10
            try:
                result = actual_run([sys.executable, str(child), *arguments[1:]], **kwargs)
                self.assertEqual(result.returncode, 7)
                self.assertIn(b"primary renderer failure marker", result.stderr)
                return result
            except subprocess.TimeoutExpired as error:
                self.assertTrue(timeout)
                self.assertIn(b"primary renderer failure marker", error.stderr)
                raise
        command = ["starter_render.py", "--source", str(self.source), "--stage", str(self.stage),
                   "--work", str(self.root / "owned-work"), "--evidence", str(evidence)]
        stderr = io.StringIO()
        with patch.object(sys, "argv", command), patch.object(starter_render.subprocess, "run", launch), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as result:
                starter_render.main()
        if collide_log: self.assertEqual(log.read_bytes(), b"prior log bytes")
        if collide_report:
            self.assertEqual(report_path.read_bytes(), b"prior report bytes")
            return str(result.exception.code) + stderr.getvalue()
        self.assertEqual(result.exception.code, 1)
        report = json.loads(report_path.read_text())
        self.assertFalse(report["native_installed_starter_renders_passed"])
        self.assertEqual(len(report["renders"]), 1)
        return report

    def test_timeout_retains_real_process_output_and_attempt(self):
        report = self.invoke_failure(timeout=True)
        attempt = report["renders"][0]
        self.assertTrue(attempt["timed_out"])
        self.assertIsNone(attempt["exit_code"])
        self.assertIn("timed out", attempt["error"])
        self.assertIn("primary renderer failure marker", attempt["stderr"]["text"])
        self.assertIn("retained stdout marker", attempt["stdout"]["text"])
        self.assertTrue(attempt["original_unchanged"])

    def test_log_collision_preserves_native_exit_and_separate_logging_error(self):
        report = self.invoke_failure(collide_log=True)
        attempt = report["renders"][0]
        self.assertEqual(attempt["exit_code"], 7)
        self.assertFalse(attempt["timed_out"])
        self.assertIn("Native starter render failed", attempt["error"])
        self.assertIn("primary renderer failure marker", attempt["stderr"]["text"])
        self.assertTrue(attempt["logging_error"])
        self.assertIn(attempt["error"], report["error"])

    def test_log_and_report_collision_retains_primary_diagnostics_in_exit_message(self):
        message = self.invoke_failure(collide_log=True, collide_report=True)
        self.assertIn("evidence publication failed", message)
        self.assertIn("Native starter render failed", message)
        self.assertIn("primary renderer failure marker", message)

    def test_large_actual_output_uses_bounded_head_and_tail_fallback(self):
        report = self.invoke_failure(collide_log=True, large_output=True)
        output = report["renders"][0]["stdout"]
        self.assertGreater(output["captured_bytes"], 100000)
        self.assertTrue(output["truncated"])
        self.assertLess(len(output["text"]), 66000)
        self.assertIn("retained stdout marker", output["text"])
        self.assertIn("stdout tail marker", output["text"])


if __name__ == "__main__": unittest.main()
