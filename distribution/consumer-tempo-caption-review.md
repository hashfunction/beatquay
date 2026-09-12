# BeatSprig tempo caption observation repair

Prepared against source `3f0395be7401b1efb6da9ac5aebdbfd1adb71609`, public source
`5f44e893f3c20db59e14b05b21a6df6e2f1af9fc`, and actual Windows
[run 34687132408](https://github.com/hashfunction/beatquay/actions/runs/34687132408).

## Actual failure and source cause

The corrected CaptionMenu route worked. PID 724 opened the original Drum Grid,
maximized Song-Editor, opened the actual tempo popup, proved `Copy value (112)`,
and dismissed that popup through the guarded native Escape. At
`2026-09-12T10:17:18.5422120Z`, it sent one native wheel event with delta 120 at
the exact owned tempo widget center (502,117). The harness then waited for
`Untitled* - BeatSprig 1.0.1 - [Song-Editor]` before attempting the next value read.

The complete final 172-control observation instead has the visible, enabled,
owned main title `BeatSprig 1.0.1 - [Song-Editor]`, with the original MainWindow
provider identity and tempo control. The process did not vanish and the popup
predicate was not the failing condition. No read of 113 occurred, so the failed
record does **not** prove that the wheel changed the model.

This caption is consistent with the actual source path:

- `LcdSpinBox::wheelEvent` accepts the event, changes the model by one step and
  emits `manualChange`.
- `AutomatableModel::setValue` adds a journal checkpoint, changes the model and
  emits `dataChanged`. Adding a checkpoint does not set Song's modified flag.
- Song connects tempo data changes to `Song::setTempo`, which updates audio
  timing and emits `tempoChanged`; this path does not call `Song::setModified`.
  SongEditor does not connect the tempo widget's `manualChange` to that slot.
- `MainWindow::resetWindowTitle` produces the stable product title for a project
  with no filename and an unset modified flag. Its modified-title branch is
  therefore not a valid prerequisite for observing this tempo edit.

The downloaded metadata ZIP is 522,130 bytes, SHA-256
`36550224f370bc03df5c3d4ce3b69178acc73b5211f2f4ecfd16f9b30e2aea82`.
The consumer receipt is 322,702 bytes, SHA-256
`f8b3fe3c7c9ced693139616510e4c0742ff4b731370947307941b6aabe41d58a`.
`cmake/msix/fixtures/tempo-caption-34687132408.json` preserves its exact final
observation and last wheel receipt with that provenance. The available genuine
startup screenshot was viewed; there is no later tempo screenshot and none was
fabricated. The package hash is
`b32edc71bf97acf6a8216c6e0fa35b1bf9f9196601d3a01c0dbc454f672b2fc0`;
the executable hash is
`1fc578316c9860c140e0f3a9a69b0b44ed345ff48039bb04aeac024dbc87e824`.

## Narrow qualification change

The two unsaved-project waits during/after the tempo edit now require the exact
observed and source-defined `BeatSprig 1.0.1` title. The existing proved MDI
maximization state still supplies the exact ` - [Song-Editor]` suffix. No broad
title alternatives, shortened timeouts, synthetic model changes or product
behavior changes were introduced.

Every wheel remains bounded and individually guarded by retained process,
package, executable, foreground, exact UIA hit and native point ownership.
The actual CaptionMenu class/ancestry, disabled Tempo caption and unique exact
`Copy value (N)` checks are unchanged. The route must prove 112 before input,
then 113, 114, 115 and 116 after exactly four detents, with no retry after a
failed proof. Save, new/reopen, independent saved-project tempo/note/instrument
checks, WAV export and independent audio-file checks remain mandatory. Normal
close, uninstall, profile attribution and marker-owned cleanup remain unchanged.

## Verification and limits

The new actual-observation replay first failed against the old production
sequencer with the same `Untitled*` timeout. It now executes the real unchanged
window selector and reaches every required value-observation boundary. Fixture
native-input/value seams test sequencing; they are not Windows success receipts.
Six mutations reject another project title, the unobserved dirty title, hidden,
disabled, truncated and duplicate windows. Existing 24 menu refusals, native
ownership/geometry failures and six stop boundaries still pass.

Validation passed:

- `pwsh -NoLogo -NoProfile -File cmake/msix/test_consumer_tempo.ps1`.
- `test_consumer_workflow.ps1`, `test_window_evidence.ps1` and
  `test_msix_evidence.ps1`, each in a separate PowerShell process.
- All 32 `python3 -m unittest discover -s cmake/msix -p 'test_*.py' -v` tests,
  including independent project/WAV verification and package/import/source gates.
- Exact captured fixture comparison with the original receipt; PowerShell parse
  and `git diff --check`.

Local PowerShell is the existing FileQuay `.tools/powershell-7.6.6/pwsh`.
`TMPDIR=/private/tmp`, its directory on PATH, and `BEATQUAY_TEST_PWSH` pointing to
that executable supply the existing test environment. Logs are
`/private/tmp/beatsprig-caption-{red,green,msix-python}.log` and
`/private/tmp/beatsprig-caption-test_*.ps1.log`; original native evidence is under
`/private/tmp/beatsprig-34687132408-review` and the failed log remains retained.

The actual Windows run remains failed: consumer/normal-close/uninstall acceptance
flags are false, failure cleanup exited -1, no residual package was recorded,
and cleanup/evidence errors were empty. Owned working-directory cleanup was
verified. This candidate requires independent review and a fresh exact-source
Windows run to prove tempo 113 onward, save/render/reopen and normal cleanup.
No native rebuild, public push, dispatch, Store action, website or parent status
change is claimed by these local fixture checks.
