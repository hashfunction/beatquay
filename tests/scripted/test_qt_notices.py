"""Exact upstream Qt notice bundle and fail-closed collection tests."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2]
SCRIPT = SOURCE / "distribution/collect_qt_notices.py"
BUNDLE = SOURCE / "distribution/qt-notices"
MODULES = {
    "qtbase": ("runtime", "ef55f427f2c8b410d34f8a7681020a3000cf6866"),
    "qtsvg": ("runtime", "17ca512f903f935282ebeca496aac5d11ba4199a"),
    "qttools": ("build-only", "8026c0462f19e9549501718152523ea223a19fd3"),
}


class QtNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="beatquay-qt-notices-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def collect(self, bundle=BUNDLE, version="6.11.2", modules=tuple(MODULES), output=None):
        output = output or self.root / "output"
        command = [sys.executable, str(SCRIPT), "--bundle-root", str(bundle),
                   "--version", version, "--output", str(output)]
        for module in modules:
            command.extend(("--module", module))
        return subprocess.run(command, capture_output=True, text=True), output

    def test_collects_exact_official_6112_module_notices(self):
        lock = json.loads((SOURCE / "distribution/candidate-inputs.json").read_text(encoding="utf-8"))
        result, output = self.collect(version=lock["qt"]["version"], modules=tuple(lock["qt"]["archives"]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "6.11.2")
        self.assertFalse(manifest["correspondingSourceComplete"])
        self.assertEqual({row["name"]: (row["role"], row["commit"]) for row in manifest["modules"]}, MODULES)
        self.assertEqual({row["repository"] for row in manifest["modules"]}, {
            "https://code.qt.io/qt/qtbase.git",
            "https://code.qt.io/qt/qtsvg.git",
            "https://code.qt.io/qt/qttools.git",
        })
        for module in MODULES:
            for license_name in ("GPL-2.0-only.txt", "GPL-3.0-only.txt", "LGPL-3.0-only.txt", "LicenseRef-Qt-Commercial.txt"):
                self.assertTrue((output / module / "LICENSES" / license_name).is_file())
            self.assertTrue((output / module / "REUSE.toml").is_file())
        for module in manifest["modules"]:
            for relative, record in module["files"].items():
                data = (output / module["name"] / relative).read_bytes()
                self.assertEqual(len(data), record["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])

    def test_tampered_upstream_license_is_rejected_before_output_creation(self):
        bundle = self.root / "bundle"
        shutil.copytree(BUNDLE, bundle)
        target = bundle / "6.11.2/qtbase/LICENSES/LGPL-3.0-only.txt"
        target.write_bytes(target.read_bytes() + b"changed")
        result, output = self.collect(bundle=bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)
        self.assertFalse(output.exists())

    def test_missing_module_or_wrong_version_is_rejected(self):
        for version, modules in (("6.11.1", tuple(MODULES)), ("6.11.2", ("qtbase", "qtsvg"))):
            with self.subTest(version=version, modules=modules):
                result, output = self.collect(version=version, modules=modules, output=self.root / (version + str(len(modules))))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_existing_output_is_preserved(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_bytes(b"keep")
        result, _ = self.collect(output=output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_bytes(), b"keep")

if __name__ == "__main__":
    unittest.main()
