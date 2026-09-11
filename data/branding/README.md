# BeatQuay original product mark

Copyright 2026 Trieflow LLC. SPDX-License-Identifier: GPL-2.0-or-later.

The Q/equalizer geometric mark is original code-authored artwork. Its navy
`#101b27`, lavender `#e5a4fa` and light `#edf4f4` palette matches the approved
BeatQuay product site. It contains no upstream logo, external artwork or fonts.
Upstream LMMS theme assets and their attribution remain separate.

`python data/branding/generate.py --check` verifies exact SVG/PNG/ICO bytes.
The Python-standard-library generator uses fixed four-by-four supersampling and
uncompressed DEFLATE blocks, without timestamps or renderer-version inputs.
Running without `--check` creates only absent files and refuses to overwrite.
The ICO contains 16, 32, 48, 64, 128 and 256-pixel PNG images.

The PNG is embedded in the application resource, used by the main window,
About/recovery/splash UI, and installed for Windows tiles. The resource compiler
uses the ICO for both application/project icons. `lmms.exe` remains the internal
host basename required by the synth DLL ABI; it is not the public product name.
