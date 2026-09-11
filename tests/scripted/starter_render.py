# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Qualify exact installed original starters through the genuine application CLI."""
import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET

NAMES = ("BeatQuay-Drum-Grid.mpt", "BeatQuay-Bassline-Sketch.mpt", "BEATQUAY-PROVENANCE.md", "CC0-1.0.txt")
PREFIX = "data/projects/templates/"
DIAGNOSTIC_BYTES = 64 * 1024

def retained_output(data):
    data = data or b""
    truncated = len(data) > DIAGNOSTIC_BYTES
    selected = (data[:DIAGNOSTIC_BYTES // 2] + b"\n[output truncated]\n" + data[-DIAGNOSTIC_BYTES // 2:]) if truncated else data
    return {"captured_bytes": len(data), "truncated": truncated, "text": selected.decode("utf-8", errors="replace")}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def regular(path, boundary):
    path, boundary = Path(path).absolute(), Path(boundary).absolute()
    if not path.is_relative_to(boundary): raise ValueError("Input escaped its root")
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked/reparse input: " + str(component))
        if component == boundary: break
    if not path.is_file(): raise ValueError("Input is not a regular file: " + str(path))
    return path

def verify_installed_inputs(source, stage):
    source, stage = Path(source), Path(stage)
    lock = json.loads(regular(source / "distribution/starter-inputs.json", source).read_text())
    generator = regular(source / "distribution/generate_starters.py", source)
    if lock["generator"] != "distribution/generate_starters.py" or sha256(generator) != lock["generator_sha256"]:
        raise ValueError("Generator source hash differs from the retained inventory")
    entries = lock["files"]
    expected = {PREFIX + name for name in NAMES}
    if len(entries) != len(expected) or {entry["path"] for entry in entries} != expected:
        raise ValueError("Starter inventory does not name the exact approved files")
    actual = {p.relative_to(stage).as_posix() for p in (stage / "data/projects").rglob("*") if p.is_file() or p.is_symlink()}
    if actual != expected: raise ValueError("Installed project file set differs from the approved starters")
    records = []
    for entry in entries:
        original = regular(source / entry["path"], source)
        installed = regular(stage / entry["path"], stage)
        if sha256(original) != entry["sha256"] or sha256(installed) != entry["sha256"]:
            raise ValueError("Starter source/stage bytes differ: " + entry["path"])
        records.append(dict(entry, installed_path=str(installed), source_path=str(original)))
    return records

def inspect_starter_wave(path, bars, tempo):
    path = Path(path)
    with wave.open(str(path), "rb") as stream:
        channels, rate, frames = stream.getnchannels(), stream.getframerate(), stream.getnframes()
        if channels != 2 or rate != 44100 or stream.getsampwidth() != 2:
            raise ValueError("Starter render is not requested stereo PCM16 44100 Hz")
        duration = frames / rate
        if abs(duration - (bars + 1) * 240 / tempo) >= 0.25:
            raise ValueError("Starter render has the wrong arrangement duration")
        samples = array.array("h", stream.readframes(frames))
        if sys.byteorder != "little": samples.byteswap()
        if len(samples) != frames * channels or not samples:
            raise ValueError("Starter PCM frames are truncated or empty")
        peak = max(abs(value) for value in samples)
        rms = math.sqrt(sum(value * value for value in samples) / len(samples))
        if peak < 100 or rms <= 10: raise ValueError("Starter render is silent or too quiet")
        if peak >= 32767: raise ValueError("Starter render clips PCM16")
    return {"frames": frames, "channels": channels, "sample_rate": rate, "duration_seconds": duration,
            "peak_pcm16": peak, "rms_pcm16": rms, "bytes": path.stat().st_size, "sha256": sha256(path)}

def run(source, stage, work, evidence, report):
    report["inputs"] = verify_installed_inputs(source, stage)
    executable = regular(stage / ("lmms.exe" if os.name == "nt" else "lmms"), stage)
    report["executable"] = {"path": str(executable), "sha256": sha256(executable)}
    work.mkdir(parents=True, exist_ok=False)
    config = ET.Element("lmms")
    ET.SubElement(config, "paths", workingdir=str(work / "user"))
    config_path = work / "starter 音符 config.xml"
    with config_path.open("xb") as output: output.write(ET.tostring(config, encoding="utf-8"))
    environment = dict(os.environ, LMMS_DATA_DIR=str(stage / "data"), LMMS_PLUGIN_DIR=str(stage / "plugins"), QT_PLUGIN_PATH=str(stage))
    environment.pop("LMMS_EXCLUDE_PLUGINS", None)
    if os.name == "nt":
        system = Path(os.environ["SystemRoot"])
        environment["PATH"] = os.pathsep.join(map(str, (stage, system / "System32", system)))
    report["renders"] = []
    for name, bars, tempo in ((NAMES[0], 4, 112), (NAMES[1], 8, 108)):
        template = regular(stage / PREFIX / name, stage)
        before = sha256(template)
        output = work / (name + " 音符.wav")
        arguments = [str(executable), "render", str(template), "-f", "wav", "-s", "44100", "-o", str(output), "-c", str(config_path)]
        record = {"template": name, "input_sha256": before, "output_path": str(output),
                  "exit_code": None, "timed_out": False}
        report["renders"].append(record)
        stdout, stderr = b"", b""
        try:
            result = subprocess.run(arguments, cwd=stage, env=environment, capture_output=True, timeout=180)
            stdout, stderr = result.stdout, result.stderr
            record["exit_code"] = result.returncode
            if result.returncode != 0:
                record["error"] = f"Native starter render failed: {name} (exit {result.returncode})"
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            record.update(timed_out=True, timeout_seconds=error.timeout,
                          error=f"Native starter render timed out: {name} after {error.timeout} seconds")
        except OSError as error:
            record["error"] = f"Native starter launch failed: {name}: {error}"
        # Record the process outcome and bounded diagnostics before any artifact
        # publication. An occupied/unwritable log must not replace that outcome.
        record.update(stdout=retained_output(stdout), stderr=retained_output(stderr))
        try:
            record["original_unchanged"] = sha256(template) == before
            if not record["original_unchanged"]:
                record["input_verification_error"] = "Native rendering changed the installed template"
        except OSError as error:
            record["original_unchanged"] = False
            record["input_verification_error"] = f"Cannot verify installed template after rendering: {error}"
        try:
            with (evidence / (name + ".render.log")).open("xb") as log:
                log.write(stdout + b"\n" + stderr)
        except OSError as error:
            record["logging_error"] = f"Starter render log publication failed: {error}"
        failures = [record[key] for key in ("error", "input_verification_error", "logging_error") if key in record]
        if failures: raise ValueError("; ".join(failures))
        record.update(inspect_starter_wave(output, bars, tempo))
    verify_installed_inputs(source, stage)
    if sha256(executable) != report["executable"]["sha256"]: raise ValueError("Executable changed during qualification")
    report["native_installed_starter_renders_passed"] = True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("source", "stage", "work", "evidence"): parser.add_argument("--" + argument, required=True, type=Path)
    args = parser.parse_args()
    report = {"native_installed_starter_renders_passed": False, "gui_menu_verified": False,
              "physical_audio_verified": False, "installed_msix_verified": False, "source_license_closure": False}
    args.evidence.mkdir(parents=True, exist_ok=True)
    try:
        run(args.source.absolute(), args.stage.absolute(), args.work.absolute(), args.evidence.absolute(), report)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, wave.Error, EOFError) as error:
        report["error"] = str(error)
    try:
        with (args.evidence / "starter-render.json").open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2); output.write("\n")
    except OSError as error:
        # The two fixed attempts contain bounded process output, so diagnostics
        # still reach the caller when neither exclusive artifact can be written.
        fallback = json.dumps({"qualification_error": report.get("error", "none"), "renders": report.get("renders", [])})
        raise SystemExit("Starter evidence publication failed: " + str(error) + "; qualification error: " + fallback)
    raise SystemExit(0 if report["native_installed_starter_renders_passed"] else 1)

if __name__ == "__main__": main()
