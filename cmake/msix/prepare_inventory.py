#!/usr/bin/env python3
"""Create the exclusive source-bound BeatQuay package input record."""
import argparse, json, os
from pathlib import Path
import subprocess, sys
from msix_qualification import PACKAGE_INPUT_RECORD, create_input_inventory, validate_run_binding, _canonical_json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--release',type=Path,default=Path('stage')); p.add_argument('--evidence-root',type=Path,default=Path('build-evidence'))
p.add_argument('--source-root',type=Path,default=Path('.')); p.add_argument('--artwork',type=Path,default=Path('data/branding/beatquay-256.png'))
p.add_argument('--source-commit',required=True); p.add_argument('--output',type=Path,default=Path(PACKAGE_INPUT_RECORD))
a=p.parse_args()
if os.path.lexists(a.output): p.error('Output exists and will not be replaced')
actual=subprocess.run(['git','-C',str(a.source_root),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
if actual!=a.source_commit: p.error('Source commit mismatch')
record=create_input_inventory(a.release,a.source_root,a.source_commit,a.evidence_root,a.artwork)
validate_run_binding(record,os.environ.get('GITHUB_RUN_ID'),os.environ.get('GITHUB_RUN_ATTEMPT'))
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('xb') as f: f.write(_canonical_json(record)); f.flush(); os.fsync(f.fileno())
print(a.output)
