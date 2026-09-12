# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Check the actual authored assets and the actual explicit CMake install."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[2]
TEMPLATES = SOURCE / "data/projects/templates"
CASES = {"BeatSprig-Drum-Grid.mpt": (4, 3, 55, 112, "kicker"),
         "BeatSprig-Bassline-Sketch.mpt": (8, 1, 40, 108, "tripleoscillator")}


class StarterTemplateTests(unittest.TestCase):
    def test_generator_reproduces_exact_source_and_refuses_to_replace_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            command = [sys.executable, str(SOURCE / "distribution/generate_starters.py"), "--output-dir", str(target)]
            subprocess.run(command, check=True, capture_output=True)
            for name in CASES:
                self.assertEqual((target / name).read_bytes(), (TEMPLATES / name).read_bytes())
            (target / next(iter(CASES))).write_bytes(b"preserve existing file")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((target / next(iter(CASES))).read_bytes(), b"preserve existing file")

    def test_original_arrangements_exist_with_exact_native_semantics(self):
        for name, (bars, tracks, notes, bpm, synth) in CASES.items():
            with self.subTest(name=name):
                path = TEMPLATES / name
                self.assertTrue(path.is_file(), "The approved original starter has not been authored")
                root = ET.fromstring(path.read_bytes())
                self.assertEqual(root.tag, "lmms-project")
                self.assertEqual(root.attrib["version"], "31")
                self.assertEqual(root.attrib["type"], "songtemplate")
                self.assertEqual(int(root.find("head").attrib["bpm"]), bpm)
                actual_tracks = root.findall("songtemplate/trackcontainer/track")
                self.assertEqual(len(actual_tracks), tracks)
                self.assertEqual(len(root.findall(".//note")), notes)
                for track in actual_tracks:
                    self.assertEqual(track.attrib["type"], "0")
                    self.assertEqual(track.find("instrumenttrack/instrument").attrib["name"], synth)
                    clips = track.findall("midiclip")
                    self.assertEqual(len(clips), bars)
                    self.assertEqual([int(clip.attrib["pos"]) for clip in clips], list(range(0, bars * 192, 192)))
                    for clip in clips:
                        self.assertEqual(int(clip.attrib["len"]), 192)
                        for note in clip.findall("note"):
                            self.assertGreater(int(note.attrib["len"]), 0)
                            self.assertGreaterEqual(int(note.attrib["pos"]), 0)
                            self.assertLessEqual(int(note.attrib["pos"]) + int(note.attrib["len"]), 192)
                            self.assertTrue(0 <= int(note.attrib["key"]) <= 127)
                            self.assertTrue(0 < int(note.attrib["vol"]) <= 100)
                forbidden = {"sampleclip", "audiofileprocessor", "effect", "fxchain", "midiport", "automationclip", "controller"}
                for element in root.iter():
                    self.assertNotIn(element.tag, forbidden)
                    for key, value in element.attrib.items():
                        self.assertFalse(key.lower().startswith(("src", "file", "userwave")), key)
                        self.assertNotIn("local:", value)
                        self.assertNotIn(":/", value)
                        self.assertNotIn("\\", value)

    def test_actual_cmake_install_contains_only_the_two_templates_and_notices(self):
        self.assertTrue((SOURCE / "data/projects/CMakeLists.txt").is_file())
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "CMakeLists.txt").write_text(
                'cmake_minimum_required(VERSION 3.24)\nproject(StarterInstall NONE)\n'
                'set(LMMS_DATA_DIR data)\nadd_subdirectory("' + (SOURCE / 'data/projects').as_posix() + '" projects)\n')
            subprocess.run(["cmake", "-S", str(work), "-B", str(work / "build")], check=True, capture_output=True)
            subprocess.run(["cmake", "--install", str(work / "build"), "--prefix", str(work / "stage")], check=True, capture_output=True)
            files = {p.relative_to(work / "stage").as_posix(): p for p in (work / "stage").rglob("*") if p.is_file()}
            expected = {"data/projects/templates/" + n for n in (*CASES, "BEATSPRIG-PROVENANCE.md", "CC0-1.0.txt")}
            self.assertEqual(set(files), expected)
            for relative, installed in files.items():
                self.assertEqual(installed.read_bytes(), (TEMPLATES / Path(relative).name).read_bytes())


if __name__ == "__main__": unittest.main()
