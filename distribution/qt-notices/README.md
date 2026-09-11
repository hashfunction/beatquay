# Qt notice source

The `6.11.2` bundle contains verbatim `LICENSES` directories and `REUSE.toml`
metadata from the exact Qt modules selected by the Windows qualification
workflow. They were retrieved from Qt's authoritative Git host at these
annotated release tags:

| Module | Qualification role | Tag object | Commit |
| --- | --- | --- | --- |
| `qtbase` | staged runtime libraries and platform plug-in | `7a59d906fb765eb85759d4d3cae45d3f295f6359` | `ef55f427f2c8b410d34f8a7681020a3000cf6866` |
| `qtsvg` | staged runtime library and SVG plug-ins | `7f649404bccad7c8364ef08d72c60b836d3f753a` | `17ca512f903f935282ebeca496aac5d11ba4199a` |
| `qttools` | build-only tools installed by the pinned workflow | `51b5e8e200b6af3e12e8d54fadb035fe3030d1b5` | `8026c0462f19e9549501718152523ea223a19fd3` |

The repositories are `https://code.qt.io/qt/<module>.git`, and each source ref
is `v6.11.2`. `manifest.json` binds every retained file to its byte length,
SHA-256 digest and Git blob ID. `collect_qt_notices.py` validates the complete
inventory before creating a qualification notice directory; it refuses version,
module, content, path and output collisions.

This notice bundle replaces an invalid assumption that the binary Qt SDK prefix
contains a `LICENSES` directory. It does not claim that BeatQuay's complete
corresponding-source or license-clearance work is finished. The candidate lock
and qualification/MSIX receipts keep those fields false.
