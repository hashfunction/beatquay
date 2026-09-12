# BeatSprig Windows marketing capture

This manual workflow installs an ephemeral signed copy of a previously reviewed,
unsigned Store MSIX. It does not rebuild BeatSprig or establish release,
installation qualification, Store acceptance, or hardware audio claims.

`binding.json` pins the reviewed successful Windows Store export from run
34709154092, public source 74e0e44c041bfe4e1a316b48ffbf1db6c83baee2.
Root independently reverified its original unsigned container, exact qualified
source inputs and both whole installed lifecycles and file oracles. The bound
artifact IDs and original byte counts/hashes remain mandatory. This binding
permits capture; a fresh capture and visual review remain required.

The preflight rechecks the original unsigned OPC payload and fixed identity,
current SDK bytes, qualified source and helper hashes, complete original native
and package metadata, both whole installed lifecycles, retained project and PNG
bytes, and the original complete WAV verification records. Original WAVs were
removed during their qualified lifecycle; preflight does not claim to reread them.
It also performs fresh anonymous application/source publication verification.
Capture source/run/attempt remain distinct from original package qualification.

The qualified consumer helpers create the original CC0 Evening Pulse project:
three tracks, four bars, 55 notes, 116 BPM, save, reopen, UI WAV export, independent
file verification, and stopped unchanged project. Only capture-state storage is
changed to an exclusively owned `C:\BeatSprig Demo`; signing remains in its own
unique runner temporary directory. No input code or UI selectors are rewritten.
The original screen function's source hash, file context, AST and retained
ScriptBlock are checked before invocation and again afterward. Read-only native
PID, window, foreground, display, DPI and frame observations surround its single
unchanged screenshot call.

The original display helper enumerates real supported modes, tests and applies
one without registry or DPI changes, then restores the original mode. Exact
module checks, fixed-image Tortoise preparation, broker process ownership,
normal close, uninstall, profile, working-directory and certificate cleanup
remain mandatory. Unknown existing state is preserved. Cleanup removes only an
unchanged sealed demo/signing tree. On an earlier failure, unsealed outputs are
preserved and reported; only an unchanged marker-only tree can be removed.

After the complete capture and cleanup pass the independent verifier, the
workflow publishes these byte-identical aliases of the original PNGs:

- `01-arrangement.png`
- `02-export-settings.png`
- `03-export-completed.png`

`capture-provenance.json` binds aliases to original names and bytes, package,
original export, capture source/run and complete capture receipt. There is no
resizing, cropping, overlay, pixel editing or synthetic UI. The separate metadata
artifact retains capture observations even on failure; it uploads no MSIX,
certificate, private key, source archive, audio or project binary.

The fixed runner is the same approved `windows-2022` image used for qualification.
An unknown image or missing/mismatched SDK fails closed. Capture runs in a new
`pwsh -NoProfile -File` process, matching the qualified helper's scope and closure
semantics. Fresh Windows execution and visual review remain required.
