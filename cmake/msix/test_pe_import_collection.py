#!/usr/bin/env python3
"""Cross-language PE evidence regressions using the real PowerShell collector.

Copyright 2026 Trieflow LLC. MIT. Only dumpbin output is a fixture; collection,
JSON serialization, file hashes, and Python validation use production code.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import msix_qualification as msix

POWERSHELL = "pwsh"
EXPECTED_IMPORTS = [
    "api-ms-win-crt-runtime-l1-1-0.dll", "KERNEL32.dll", "lib+plus.dll",
    "lib-with-dash.dll", "lib.part.dll", "lib_.dll", "lib_with_under.dll",
    "libA.dll", "MSVCP140.dll",
    "MSVCP140_1.dll", "MSVCP140_2.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll",
]


class PeImportCollectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="beatquay-pe-imports-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stage = self.root / "stage"
        for name in EXPECTED_IMPORTS:
            self.write_binary(name, [])
        for name in msix.ALLOWED_PLUGIN_DLLS:
            self.write_binary(name, ["beatsprig.exe"])
        # Include the unsuffixed/suffixed MSVC names from run 34656962792,
        # Include punctuation versus letters: OrdinalIgnoreCase incorrectly
        # places libA.dll before lib_.dll for Python's lowercase ASCII order.
        self.write_binary("beatsprig.exe", list(reversed(EXPECTED_IMPORTS)) + ["KERNEL32.dll", "kernel32.DLL", "LIBa.DLL"])
        self.dumpbin = self.root / "dumpbin.ps1"
        self.dumpbin.write_text("Get-Content -LiteralPath $args[-1]; $global:LASTEXITCODE=0\n")
        self.output = self.root / "pe-imports.json"
        self.runner = self.root / "collect-fixture.ps1"
        self.runner.write_text(
            "param($Collector,$FixtureStage,$FixtureDumpbin,$FixtureOutput,$Culture)\n"
            "$ErrorActionPreference='Stop'\n"
            "[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo($Culture)\n"
            ". $Collector -LibraryOnly\n"
            "$record=Get-BeatQuayPeImportRecord $FixtureStage $FixtureDumpbin 'C:\\Windows\\System32'\n"
            "$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $FixtureOutput -Encoding utf8\n"
        )

    def write_binary(self, name, imports):
        path = self.stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Dump of file fixture\n" + "".join(f"    {name}\n" for name in imports))

    def collect(self, culture="en-US"):
        result = subprocess.run(
            [POWERSHELL, "-NoLogo", "-NoProfile", "-File", str(self.runner),
             str(Path(__file__).with_name("collect-pe-imports.ps1").resolve()),
             str(self.stage), str(self.dumpbin), str(self.output), culture],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.output.read_text(encoding="utf-8-sig"))

    def validate(self, record):
        self.output.write_text(json.dumps(record))
        return msix._validate_pe_imports(self.stage, self.output, msix.inventory_tree(self.stage))

    def test_actual_collector_order_and_deduplication_pass_python_in_two_cultures(self):
        for culture in ("en-US", "tr-TR"):
            with self.subTest(culture=culture):
                record = self.collect(culture)
                host = next(row for row in record["files"] if row["path"] == "beatsprig.exe")
                self.assertEqual(host["imports"], EXPECTED_IMPORTS)
                self.assertEqual(record["unresolvedImports"], [])
                self.assertEqual(record["ambiguousPackagedImports"], [])
                self.assertEqual(record["apiSetResolutions"], [])
                self.validate(record)

    def test_python_rejects_unsorted_duplicate_and_case_alias_imports(self):
        record = self.collect()
        invalid_lists = [
            ["VCRUNTIME140_1.dll", "VCRUNTIME140.dll"],
            ["libA.dll", "lib_.dll"],
            ["KERNEL32.dll", "KERNEL32.dll"],
            ["KERNEL32.dll", "kernel32.DLL"],
        ]
        for imports in invalid_lists:
            with self.subTest(imports=imports):
                corrupted = copy.deepcopy(record)
                next(row for row in corrupted["files"] if row["path"] == "beatsprig.exe")["imports"] = imports
                with self.assertRaisesRegex(ValueError, "sorted unique list"):
                    self.validate(corrupted)

    def test_python_rejects_non_ascii_and_malformed_import_names(self):
        record = self.collect()
        for imports in (["\u212aERNEL32.dll"], ["../KERNEL32.dll"], [None], [["KERNEL32.dll"]]):
            with self.subTest(imports=imports):
                corrupted = copy.deepcopy(record)
                next(row for row in corrupted["files"] if row["path"] == "beatsprig.exe")["imports"] = imports
                with self.assertRaisesRegex(ValueError, "Invalid imported module name"):
                    self.validate(corrupted)

    def test_missing_dependency_collector_evidence_is_rejected(self):
        self.write_binary("beatsprig.exe", ["beatquay-fixture-missing-runtime.dll"])
        record = self.collect()
        self.assertEqual(record["unresolvedImports"], ["beatsprig.exe:beatquay-fixture-missing-runtime.dll"])
        self.assertEqual(len(record["resolutionErrors"]), 1)
        with self.assertRaisesRegex(ValueError, "Unresolved or ambiguous"):
            self.validate(record)

    def test_ambiguous_packaged_dependency_collector_evidence_is_rejected(self):
        self.write_binary("extra/MSVCP140.dll", [])
        record = self.collect()
        self.assertEqual(record["ambiguousPackagedImports"], ["beatsprig.exe:MSVCP140.dll"])
        with self.assertRaisesRegex(ValueError, "Unresolved or ambiguous"):
            self.validate(record)

    def test_python_still_rejects_missing_and_duplicate_binary_rows(self):
        record = self.collect()
        for rows in (record["files"][:-1], record["files"] + [record["files"][0]]):
            with self.subTest(paths=[row["path"] for row in rows]):
                corrupted = dict(record, files=rows)
                with self.assertRaisesRegex(ValueError, "every staged|exact stage binary"):
                    self.validate(corrupted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--powershell", default=POWERSHELL)
    arguments, remaining = parser.parse_known_args()
    POWERSHELL = arguments.powershell
    unittest.main(argv=[sys.argv[0], *remaining])
