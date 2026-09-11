# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Private native smoke fixture; report metadata, never publish generated audio."""
import argparse
import array
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
import zlib


def inspect_wave(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Rendered output is missing or empty")
    with wave.open(str(path), "rb") as stream:
        frames = stream.getnframes()
        rate = stream.getframerate()
        channels = stream.getnchannels()
        if stream.getsampwidth() != 2 or channels != 2 or rate != 44100:
            raise ValueError("Rendered output is not the requested stereo 44100 Hz PCM16")
        if not 1 <= frames / rate <= 20:
            raise ValueError("Rendered fixture has an unexpected duration")
        samples = array.array("h", stream.readframes(frames))
        if sys.byteorder != "little": samples.byteswap()
        if len(samples) != frames * channels:
            raise ValueError("Rendered output has truncated PCM frames")
        peak = max(abs(sample) for sample in samples)
        if peak < 100:
            raise ValueError("Rendered fixture is silent or unexpectedly quiet")
    return {"frames": frames, "sample_rate": rate, "channels": channels,
            "duration_seconds": frames / rate, "peak_pcm16": peak,
            "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def inspect_render_error(result, source, original_sha256, destination, sentinel):
    if result.returncode != 1:
        raise ValueError("Render error must exit with EXIT_FAILURE (1), not success, a crash or a timeout")
    diagnostic = result.stderr.decode("utf-8", errors="replace").replace("\\", "/")
    if "Render failed or cancelled:" not in diagnostic:
        raise ValueError("Render error did not reach the typed terminal result handler")
    expected_path_prefix = str(destination).replace("\\", "/") + ": "
    if not any(line.startswith(expected_path_prefix) for line in diagnostic.splitlines()):
        raise ValueError("Render error did not identify the requested destination")
    if hashlib.sha256(source.read_bytes()).hexdigest() != original_sha256:
        raise ValueError("Render error changed the original project")
    keep = destination / "keep.txt"
    if (not destination.is_dir() or not keep.is_file() or keep.read_bytes() != sentinel
            or sorted(item.name for item in destination.iterdir()) != ["keep.txt"]):
        raise ValueError("Render error changed the blocked destination")
    return {"exit_code": result.returncode, "typed_terminal_result_observed": True,
            "input_sha256": original_sha256, "original_unchanged": True,
            "blocked_destination_unchanged": True}


def fixture_bytes():
    # Original test notes: one bar, four equal-length notes, one native oscillator.
    project = ET.Element("lmms-project", version="1.0", creator="LMMS", creatorversion="1.2.2", type="song")
    ET.SubElement(project, "head", bpm="120", mastervol="50", masterpitch="0", timesig_numerator="4", timesig_denominator="4")
    container = ET.SubElement(ET.SubElement(project, "song"), "trackcontainer")
    track = ET.SubElement(container, "track", type="0", name="Original qualification notes", muted="0", solo="0")
    instrument = ET.SubElement(ET.SubElement(track, "instrumenttrack", vol="60", pan="0", basenote="57", fxch="0", usemasterpitch="1"), "instrument", name="tripleoscillator")
    ET.SubElement(instrument, "tripleoscillator", vol0="100", vol1="0", vol2="0", wavetype0="0", coarse0="0", useWaveTable1="0")
    pattern = ET.SubElement(track, "pattern", type="1", pos="0", len="192", steps="16", name="Original qualification notes")
    for position, key in ((0, 57), (48, 60), (96, 64), (144, 60)):
        ET.SubElement(pattern, "note", pos=str(position), key=str(key), len="36", vol="80", pan="0")
    return ET.tostring(project, encoding="utf-8", xml_declaration=True)


def run(executable, stage, work, evidence):
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=True)
    config = ET.Element("lmms")
    ET.SubElement(config, "paths", workingdir=str(work / "user"))
    config_path = work / "qualification 音符 é-config.xml"
    config_path.write_bytes(ET.tostring(config, encoding="utf-8"))
    environment = dict(os.environ, LMMS_DATA_DIR=str(stage / "data"), QT_PLUGIN_PATH=str(stage))
    if os.name == "nt":
        system_root = Path(os.environ["SystemRoot"])
        environment["PATH"] = os.pathsep.join(map(str, (stage, system_root / "System32", system_root)))
    original = fixture_bytes()
    records = []
    for extension, contents in (("mmp", original), ("mmpz", struct.pack(">I", len(original)) + zlib.compress(original))):
        source = work / ("音符 é." + extension)
        output = work / ("render 音符 é-" + extension + ".wav")
        source.write_bytes(contents)
        source_hash = hashlib.sha256(contents).hexdigest()
        result = subprocess.run([str(executable), "render", str(source), "-f", "wav", "-s", "44100", "-o", str(output), "-c", str(config_path)],
                                cwd=stage, env=environment, capture_output=True, timeout=180)
        (evidence / ("render-" + extension + ".log")).write_bytes(result.stdout + b"\n" + result.stderr)
        if result.returncode != 0:
            raise ValueError("Native " + extension + " render failed with exit " + str(result.returncode))
        if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
            raise ValueError("Rendering changed the original " + extension + " project")
        records.append(dict(inspect_wave(output), input_format=extension, input_sha256=source_hash, original_unchanged=True))
    # A directory at the exact output filename fails regardless of runner write
    # privileges. Require the typed terminal path, not the old constructor exit.
    source = work / "音符 é.mmp"
    blocked = work / "blocked 音符 é.wav"
    blocked.mkdir()
    sentinel = b"Original directory contents; render must preserve these bytes."
    (blocked / "keep.txt").write_bytes(sentinel)
    error_result = subprocess.run([str(executable), "render", str(source), "-f", "wav", "-s", "44100", "-o", str(blocked), "-c", str(config_path)],
                                  cwd=stage, env=environment, capture_output=True, timeout=60)
    (evidence / "render-output-error.log").write_bytes(error_result.stdout + b"\n" + error_result.stderr)
    error_record = inspect_render_error(error_result, source, hashlib.sha256(original).hexdigest(), blocked, sentinel)
    return {"native_render_smoke_passed": True, "native_render_error_exit_passed": True,
            "fixture": "Original one-bar qualification notes; not a shipped starter", "renders": records,
            "render_error": error_record,
            "project_round_trip_verified": False, "physical_audio_verified": False,
            "installed_package_verified": False, "license_clearance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = run(args.executable.resolve(), args.stage.resolve(), args.work.resolve(), args.evidence.resolve())
    except (OSError, ValueError, subprocess.TimeoutExpired, wave.Error, EOFError) as error:
        report = {"native_render_smoke_passed": False, "error": str(error)}
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / "render-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["native_render_smoke_passed"] else 1)
