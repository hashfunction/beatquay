#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original geometric Q/equalizer mark; deterministic SVG, PNG and Windows ICO.

No fonts, external artwork, rendering library or network input. Stored DEFLATE
blocks avoid byte changes between zlib versions. Geometry and supersampling are
fixed here; --check never modifies a file.
"""
import argparse
import binascii
from pathlib import Path
import struct
import zlib

BACKGROUND = (16, 27, 39)
ACCENT = (229, 164, 250)
FOREGROUND = (237, 244, 244)
SIZES = (16, 32, 48, 64, 128, 256)
SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <!-- Original mark, Copyright 2026 Trieflow LLC, GPL-2.0-or-later. -->
  <rect width="256" height="256" rx="52" fill="#101b27"/>
  <circle cx="128" cy="120" r="72" fill="none" stroke="#e5a4fa" stroke-width="20"/>
  <path d="M169 158L219 208L205 222L155 172Z" fill="#e5a4fa"/>
  <g fill="#edf4f4">
    <rect x="92" y="112" width="12" height="36" rx="6"/>
    <rect x="122" y="86" width="12" height="62" rx="6"/>
    <rect x="152" y="102" width="12" height="46" rx="6"/>
  </g>
</svg>
"""


def rounded(x, y, left, top, width, height, radius):
    if not (left <= x <= left + width and top <= y <= top + height):
        return False
    cx = min(max(x, left + radius), left + width - radius)
    cy = min(max(y, top + radius), top + height - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def pixel(x, y):
    if not rounded(x, y, 0, 0, 256, 256, 52):
        return (0, 0, 0, 0)
    rgb = BACKGROUND
    distance = (x - 128) ** 2 + (y - 120) ** 2
    # Tail's rotated rectangle: x-y in [-17,11], x+y in [327,427].
    if 62**2 <= distance <= 82**2 or (-17 <= x - y <= 11 and 327 <= x + y <= 427):
        rgb = ACCENT
    for left, top, height in ((92, 112, 36), (122, 86, 62), (152, 102, 46)):
        if rounded(x, y, left, top, 12, height, 6):
            rgb = FOREGROUND
    return (*rgb, 255)


def chunk(kind, payload):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", binascii.crc32(kind + payload))
    )


def stored_zlib(data):
    blocks = []
    for offset in range(0, len(data), 65535):
        part = data[offset : offset + 65535]
        blocks.append(
            bytes([int(offset + len(part) == len(data))])
            + struct.pack("<HH", len(part), len(part) ^ 65535)
            + part
        )
    return b"\x78\x01" + b"".join(blocks) + struct.pack(">I", zlib.adler32(data))


def png(size):
    raw = bytearray()
    for row in range(size):
        raw.append(0)
        for column in range(size):
            samples = [
                pixel(
                    (column + (sx + 0.5) / 4) * 256 / size,
                    (row + (sy + 0.5) / 4) * 256 / size,
                )
                for sy in range(4)
                for sx in range(4)
            ]
            alpha_sum = sum(p[3] for p in samples)
            rgb = [
                sum(p[c] * p[3] for p in samples) // alpha_sum if alpha_sum else 0
                for c in range(3)
            ]
            raw.extend((*rgb, (alpha_sum + 8) // 16))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", stored_zlib(raw))
        + chunk(b"IEND", b"")
    )


def assets():
    images = [(size, png(size)) for size in SIZES]
    offset = 6 + 16 * len(images)
    entries = []
    for size, image in images:
        entries.append(
            struct.pack(
                "<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(image), offset
            )
        )
        offset += len(image)
    return {
        "beatquay.svg": SVG.encode(),
        "beatquay-256.png": images[-1][1],
        "beatquay.ico": struct.pack("<HHH", 0, 1, len(images))
        + b"".join(entries)
        + b"".join(image for _, image in images),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    for name, data in assets().items():
        path = root / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit(f"Generated asset differs: {name}")
        else:
            # Creation only; explicit removal is needed to replace authored bytes.
            with path.open("xb") as stream:
                stream.write(data)
        print(f"{name}: {len(data)} bytes")


if __name__ == "__main__":
    main()
