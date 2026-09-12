"""Real Git checkout and production preflight tests; no native build is invoked."""

import logging
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2]


class SourceCheckoutTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="beatquay-source-checkout-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.seed = self.root / "seed"
        self.seed.mkdir()
        self.git("init", "-q", cwd=self.seed)
        self.git("config", "user.name", "BeatQuay fixture", cwd=self.seed)
        self.git("config", "user.email", "fixture@invalid", cwd=self.seed)
        for name in (".gitattributes", ".gitignore"):
            (self.seed / name).write_bytes((SOURCE / name).read_bytes())
        (self.seed / "CMakeLists.txt").write_bytes(b"# Owned checkout fixture\n")
        (self.seed / "cmake/msix").mkdir(parents=True)
        (self.seed / "cmake/msix/cache_fixture.py").write_bytes(b"VALUE = 1\n")
        self.git("add", ".", cwd=self.seed)
        self.git("commit", "-qm", "Fixture inputs", cwd=self.seed)
        self.work = self.root / "checkout"
        self.git("clone", "--no-checkout", str(self.seed), str(self.work), cwd=self.root)
        for key, value in (("core.autocrlf", "true"), ("core.eol", "crlf"),
                           ("core.symlinks", "false"), ("core.filemode", "false")):
            self.git("config", key, value)
        self.git("checkout", "--detach", "HEAD")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.assertEqual(self.status(), "")
        self.assertEqual((self.work / "CMakeLists.txt").read_bytes(), b"# Owned checkout fixture\n")
        (self.work / "build-evidence").mkdir()
        # Run the exact production commit/status/evidence/rejection statements,
        # outside the Windows-only host guard and before dependency bootstrap.
        script = (SOURCE / "distribution/qualify-candidate.ps1").read_text(encoding="utf-8")
        preflight = script.split("$sourceCommit=", 1)[1].split("$lock =", 1)[0]
        # Preserve the production script/helper topology outside the checkout
        # under test, so exercising preflight does not dirty that checkout.
        harness = self.root / "harness"
        self.probe = harness / "distribution/preflight.ps1"
        self.probe.parent.mkdir(parents=True)
        helper = harness / "cmake/msix/qualification-bindings.ps1"
        helper.parent.mkdir(parents=True)
        helper.write_bytes((SOURCE / "cmake/msix/qualification-bindings.ps1").read_bytes())
        self.assertEqual(helper.read_bytes(), (SOURCE / "cmake/msix/qualification-bindings.ps1").read_bytes())
        self.probe.write_text("$ErrorActionPreference='Stop'\n$sourceCommit=" + preflight,
                              encoding="utf-8")
        self.pwsh = os.environ.get("BEATQUAY_TEST_PWSH") or shutil.which("pwsh")
        self.assertTrue(self.pwsh, "Set BEATQUAY_TEST_PWSH to the PowerShell 7 executable")

    def git(self, *arguments, cwd=None):
        result = subprocess.run(["git", *arguments], cwd=cwd or self.work,
                                capture_output=True, text=True, check=True)
        return result.stdout

    def status(self):
        return self.git("status", "--porcelain", "--untracked-files=all")

    def preflight(self, **overrides):
        environment = dict(os.environ, GITHUB_SHA=self.commit, GITHUB_RUN_ID="123456", GITHUB_RUN_ATTEMPT="2")
        environment.update(overrides)
        return subprocess.run([self.pwsh, "-NoLogo", "-NoProfile", "-File", str(self.probe)],
                              cwd=self.work, env=environment, capture_output=True, text=True)

    def test_exact_generated_bootstrap_log_and_msix_cache_leave_checkout_clean(self):
        # The pinned aqt logging.ini uses FileHandler('aqtinstall.log', 'a').
        # Exercise that actual file-creation behavior; no fake Git status.
        handler = logging.FileHandler(self.work / "aqtinstall.log", mode="a")
        handler.close()
        py_compile.compile(str(self.work / "cmake/msix/cache_fixture.py"), doraise=True)
        self.assertTrue((self.work / "aqtinstall.log").is_file())
        self.assertTrue(list((self.work / "cmake/msix/__pycache__").glob("*.pyc")))
        result = self.preflight()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.status(), "")
        self.assertEqual((self.work / "build-evidence/source-status-before-build.txt").read_text(), "")
        self.assertEqual((self.work / "build-evidence/source-status-exit-code.txt").read_text().strip(), "0")

    def test_actual_helper_rejects_missing_run_and_invalid_attempt(self):
        for overrides in ({"GITHUB_RUN_ID": ""}, {"GITHUB_RUN_ATTEMPT": "0"}):
            with self.subTest(overrides=overrides):
                result = self.preflight(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Exact source commit, workflow run and attempt are required", result.stderr)
                self.assertEqual(self.status(), "")

    def test_unrelated_log_still_rejects_and_records_exact_path(self):
        for relative in ("unrelated.log", "other/aqtinstall.log", "cmake/msix/unexpected.py"):
            with self.subTest(relative=relative):
                path = self.work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("unexpected", encoding="utf-8")
                result = self.preflight()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Source checkout must be clean", result.stderr)
                evidence_path = self.work / "build-evidence/source-status-before-build.txt"
                self.assertTrue(evidence_path.is_file())
                self.assertIn("?? " + relative, evidence_path.read_text())
                self.assertEqual(path.read_text(), "unexpected")
                path.unlink()

    def test_modified_tracked_source_still_rejects_and_records_exact_path(self):
        (self.work / "CMakeLists.txt").write_bytes(b"# Changed tracked input\n")
        result = self.preflight()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Source checkout must be clean", result.stderr)
        self.assertTrue((self.work / "build-evidence/source-status-before-build.txt").is_file())
        evidence = (self.work / "build-evidence/source-status-before-build.txt").read_text()
        self.assertIn(" M CMakeLists.txt", evidence)
        self.assertEqual((self.work / "CMakeLists.txt").read_bytes(), b"# Changed tracked input\n")


if __name__ == "__main__":
    unittest.main()
