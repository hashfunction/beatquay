# BeatQuay installed musical consumer workflow candidate

Base source: `14d84a148bfe43476a3bbe8a0d4aa35b175b85d5`.
Baseline public run `hashfunction/beatquay` / `34671756671` passed startup,
first-run setup, exact disposable installation and CLI/native render checks. It
did not establish actual installed UI project creation, reopen or export.
Its 495,454-byte metadata artifact was read at
`/private/tmp/beatquay-34671756671-review`; no application binary was downloaded.

## Approved implementation

- Normal File > New from template uses the exact packaged original CC0
  `BeatQuay-Drum-Grid.mpt`. All original musical data, provenance and license
  files remain untouched. Three synth tracks contain four bars and 55 notes.
- The actual Tempo dialog changes 112 to 116 BPM. UI Save writes `Evening
  Pulse.mmp`; New clears the working project; UI Open reopens it; UI Save As
  writes `Evening Pulse Reopened.mmp` from the reopened in-memory model.
- Normal Ctrl+E, actual destination/format controls and Start produce a WAV.
  Acceptance requires the owned `Export completed` dialog's exact output path
  and byte count, the independent file checker, normal Stop/Play-ready editor,
  unchanged saved projects and the repeated exact module inventory including
  the packaged Kicker DLL. No CLI render or app-internal test entry point drives
  or substitutes for these consumer UI actions.
- Read-only Python checks preserve all authored notes, clip positions, synth
  parameters, tempo and track attributes; compare complete serialized
  head/track/mixer state across the two UI saves; bind template and output
  hashes; and inspect actual stereo PCM16/44100-Hz WAV frames. Expected duration
  is 10.3448276 seconds (four bars plus the normal extra tail bar, error strictly
  below 0.25 seconds). Every musical bar needs audible varying AC content;
  silence, DC, truncation, wrong duration and clipping are rejected. Quiet end
  padding remains valid. XML is bounded to 2 MiB and WAV to 4 MiB.
- UIA observations and input selectors are bounded, PID-bound and reread before
  actual native clicks or provider value changes. An unavailable/NotSupported
  control type makes the snapshot incomplete, never successful. Each wait has
  a fixed deadline (normally 15–30 seconds; export completion 90 seconds).
- Native captures retain PNG pixels unchanged, alongside source/package/exe/PID,
  window, desktop/DPI and hash provenance. The existing CutQuay MIT native mode
  helper is copied under a distinct namespace: supported 32-bpp modes only,
  CDS_TEST, dynamic flags 0, no registry/DPI/emulation changes, mandatory exact
  original-mode restoration. The actual main window is resized to 1472×940;
  the real Song-Editor Maximize button arranges its content. Capture files are
  marked `marketing_branding_review_required=true` per the later naming request.
- An absent-before-activation profile acquires ownership only after the normal
  first-run UI, exact working path, file creation interval and bounded XML checks.
  Subsequent writes can only add the exact opened/saved projects or seven
  source-traced editor exit preferences. Unexplained changes preserve the last
  attributable hash and fail. Normal close is verified before the final profile
  observation; cleanup requires proven retained-process termination and unchanged
  last observed bytes. Existing marker/tree/package/cert/unsigned-source gates
  remain in force. Failed consumer execution still runs owned cleanup/display
  restoration, and cannot confer final workflow acceptance.
- The package source inventory now includes the actual consumer/display/file
  helpers and their invoked installer/first-run/WAV-inspection dependencies.
  Mutation regression proves changed helper bytes fail before package creation.
  The metadata artifact adds only the two small actual saved `.mmp` projects;
  no MSIX, executable, DLL, WAV or certificate is uploaded.

## Local verification

- 66 Python tests passed across package/container (14), actual PowerShell PE
  import collector (6), consumer files/profile (11), authored starter files (3),
  starter stage/render (19), and candidate WAV inspection (13).
- All 11 PowerShell fixtures in `qualify-msix.ps1` passed in isolated processes:
  actual orchestration/failure retention; Appx preflight; final evidence;
  registration ownership; retained process observation; window evidence;
  normal first-run and marker cleanup; Defender policy; temporary ownership;
  consumer input/export-result/profile boundaries; native display structures,
  safe flags, test-before-apply, normal restore and partial-apply recovery.
- Red/green cases included absent verifier/helper, mandatory workflow omitted
  from core ordering, nonzero DC masquerading as audio, and unbound consumer
  helper mutation. Negative profile checks invoke the production observer and
  external Python verifier, preserving its prior owned hash on rejection.
- All PowerShell files parsed and `git diff --check` passed. The local runner
  supplied PowerShell 7.6.6 on PATH and `TMPDIR=/private/tmp`; initial existing
  tests failed only without that runtime or on macOS's `/var` symlink. Both
  environmental cases passed with those explicit settings, without weakening
  production path checks. Full final log: `/private/tmp/beat-consumer-final-tests.log`;
  the final added source-binding package suite was also rerun (14 passed).

## Explicit limits / handoff

This candidate has not run on Windows. Its actual UIA names/HelpText, dialog
transitions, profile exit serialization, installed export, window layout and
result screenshots remain native pending. Portable synthetic project/WAV
fixtures are verifier tests and are not consumer evidence or marketing assets.
The previously successful startup run does not qualify this new consumer flow.
No C++ product/runtime behavior, fixed package identity, current title contract,
Store submission, site or parent status was changed; no push or workflow dispatch
was performed. Root independent review and a fresh exact Windows run are required.
Final marketing capture branding stays on hold until the rename is confirmed.
