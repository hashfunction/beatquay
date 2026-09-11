# Copyright (c) 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic original arrangement data. No upstream music/preset inputs."""
import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

NAMES = ("BeatQuay-Drum-Grid.mpt", "BeatQuay-Bassline-Sketch.mpt")
TEMPLATES = Path(__file__).resolve().parents[1] / "data/projects/templates"


def element(parent, tag, **attributes):
    return ET.SubElement(parent, tag, {key: str(value) for key, value in attributes.items()})


def project(bpm):
    root = ET.Element("lmms-project", version="31", type="songtemplate", creator="BeatQuay source generator")
    root.append(ET.Comment("Original note and synth parameter data for Trieflow LLC; CC0-1.0. See BEATQUAY-PROVENANCE.md."))
    element(root, "head", bpm=bpm, mastervol=70, masterpitch=0, timesig_numerator=4, timesig_denominator=4)
    container = element(element(root, "songtemplate"), "trackcontainer")
    return root, container


def track(container, name, volume, synth, parameters):
    result = element(container, "track", type=0, name=name, muted=0, solo=0)
    settings = element(result, "instrumenttrack", vol=volume, pan=0, pitch=0, pitchrange=1,
                       basenote=69, firstkey=0, lastkey=127, mixch=0, usemasterpitch=1)
    element(element(settings, "instrument", name=synth), synth, **parameters)
    return result


def clip(track_element, bar, name, notes):
    result = element(track_element, "midiclip", type=1, name=name, pos=bar * 192, len=192, steps=16,
                     muted=0, autoresize=0, off=0)
    for position, key, length, velocity in notes:
        element(result, "note", pos=position, key=key, len=length, vol=velocity, pan=0, type=0)


def serialize(root):
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def arrangements():
    root, container = project(112)
    voices = (
        ("Low pulse", 50, 150, 48, 210, 0, 0.12,
         ((0, 72, 96), (0, 84, 144), (0, 48, 96, 156), (0, 72, 120, 168))),
        ("Backbeat", 28, 260, 110, 125, 0.6, 0.08,
         ((48, 144), (48, 144), (48, 144), (48, 132, 156))),
        ("Short ticks", 16, 900, 620, 42, 0.35, 0.02, ((0, 24, 48, 72, 96, 120, 144, 168),) * 4),
    )
    for name, volume, start, end, decay, noise, click, bars in voices:
        settings = dict(version=1, startfreq=start, endfreq=end, decay=decay, dist=0.1, distend=0.1,
                        gain=1, env=0.18, noise=noise, click=click, slope=0.08, startnote=0, endnote=0)
        voice = track(container, name, volume, "kicker", settings)
        for bar, positions in enumerate(bars):
            clip(voice, bar, f"{name} {bar + 1}", [(pos, 60, 6, 84 if pos % 48 == 0 else 62) for pos in positions])
    drum = serialize(root)
    root, container = project(108)
    settings = {}
    for index, (volume, shape, coarse) in enumerate(((70, 1, 0), (30, 0, -12), (0, 0, 0))):
        settings.update({f"vol{index}": volume, f"pan{index}": 0, f"coarse{index}": coarse,
                         f"finel{index}": 0, f"finer{index}": 0, f"phoffset{index}": 0,
                         f"stphdetun{index}": 0, f"wavetype{index}": shape,
                         f"modalgo{index + 1}": 2, f"useWaveTable{index + 1}": 1})
    bass = track(container, "Triangle and sub bass", 32, "tripleoscillator", settings)
    for bar, key in enumerate((36, 36, 32, 32, 34, 34, 31, 36)):
        intervals = (0, 12, 7, 3, 0) if bar == 7 else (0, 7, 0, 10, 12)
        notes = [(pos, key + interval, length, velocity) for pos, interval, length, velocity in
                 zip((0, 36, 72, 120, 144), intervals, (30, 18, 30, 18, 36), (82, 66, 76, 62, 72))]
        clip(bass, bar, f"Bass phrase {bar + 1}", notes)
    return dict(zip(NAMES, (drum, serialize(root))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Compare source bytes without modifying them")
    mode.add_argument("--output-dir", type=Path, help="Create only absent files in a development output directory")
    args = parser.parse_args()
    target = TEMPLATES if args.check else args.output_dir
    if not args.check: target.mkdir(parents=True, exist_ok=True)
    for name, contents in arrangements().items():
        path = target / name
        if args.check:
            if path.read_bytes() != contents: raise SystemExit("Generated starter differs: " + name)
        else:
            with path.open("xb") as output: output.write(contents)
        print(name, hashlib.sha256(contents).hexdigest())


if __name__ == "__main__": main()
