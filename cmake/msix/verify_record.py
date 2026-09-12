"""Recheck same-run source/stage/receipt/package binding before any install mutation.
Copyright 2026 Trieflow LLC. MIT.
"""

import argparse
import os
from pathlib import Path
import subprocess

from msix_qualification import PACKAGE_INPUT_RECORD, validate_run_binding, verify_record_inputs, verify_installed, _load_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--record", type=Path, required=True)
parser.add_argument("--package", type=Path, required=True)
parser.add_argument("--source-commit", required=True)
parser.add_argument("--installed-root", type=Path)
parser.add_argument("--identity-mode", choices=("qualification", "store"), default="qualification")
args = parser.parse_args()
source = Path(__file__).resolve().parents[2]
actual = subprocess.run(
    ["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
).stdout.strip()
if actual != args.source_commit:
    raise SystemExit("Source commit differs from this installation qualification run")
dirty = subprocess.run(
    ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
if dirty:
    raise SystemExit("Dirty source checkout cannot identify qualification inputs")
record = _load_json(args.record, "qualification record")
validate_run_binding(record, os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_RUN_ATTEMPT"))
verify_record_inputs(
    args.package,
    args.record,
    source / "stage",
    source / "data/branding/beatquay-256.png",
    actual,
    source / PACKAGE_INPUT_RECORD,
    source / "build-evidence",
    source,
    args.identity_mode,
)
if args.installed_root:
    verify_installed(args.installed_root, record["payload"], args.identity_mode)
    print("PASS: exact source/run/stage/notices/package and installed payload reverified")
else:
    print("PASS: exact source/run/stage/notices/package binding reverified before installation")
