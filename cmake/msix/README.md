# BeatSprig qualification MSIX

These MIT helpers build and install a temporary CI-only identity from the exact Windows native stage. They preserve the retained pipeline notices, bind original BeatSprig source/artwork/starters, copied Qt and vcpkg notices, same-run render results and every PE import. The full stage is copied byte-for-byte, then package-owned manifest, tiles and notices are added.

`distribution/qualify-candidate.ps1` is the supported entry point on a disposable Windows runner. It compiles/tests/renders the native app, records PE imports and notices, creates `build-evidence/package-input.json`, then invokes `cmake/msix/qualify-msix.ps1`. The latter runs portable/PowerShell regressions, uses Windows SDK 10.0.26100.0 MakeAppx, independently verifies the OPC container and SDK unpack, test-signs a private copy, installs it through the package broker, observes exact package/PID/path/hash/module identity, completes the normal working-directory and Settings prompts, requires the visible `BeatSprig 1.0.1` editor, completes the musical project/save/reopen/UI export and screenshot flow described below, closes normally, and removes only the exact owned registration and ephemeral certificate.

Fresh startup first asks `Working directory` whether to create the exact Qt
Documents `/BeatQuay/` path; `GuiApplication` waits for this answer before it
constructs the Settings dialog. The qualification helper observes the exact
title, complete question/path and one visible enabled `Yes` belonging to the
retained installed process, then requires `BeatSprig - Settings` and its exact
`OK`. It rereads each live UIA provider before invocation, tolerates only the
ordinary transition/splash, and retains bounded per-phase observations in the
final receipt even when a later step fails. Each wait remains limited to 30
seconds. Unexpected titles, content, ownership or actions fail without input.

The working folder must be absent in preflight and immediately before `Yes`.
Once Settings proves startup advanced, an exclusive marker binds the observed
empty folder tree to this source, installed package and process. Cleanup requires
proven termination of the retained process, an unchanged marker/tree and no
reparse paths or unexpected files; it deletes only empty directories and its own
marker. Changed, unowned or uncertain state is preserved and fails qualification.
`test_first_run_flow.ps1` exercises the actual orchestration, marker/filesystem
operations and final cleanup/reporting closure with only Windows UIA/process IO
substituted. These fixtures do not establish actual Windows GUI acceptance.

The PE collector resolves nonpackaged Windows API-set imports through the actual
OS: `IsApiSetImplemented`, then `LoadLibraryExW` with
`LOAD_LIBRARY_SEARCH_SYSTEM32`, followed by `GetModuleFileNameW`. It records the
returned regular System32 host's size, SHA-256 and valid Microsoft Authenticode
signer, rechecks the bytes, and releases the loader handle. Microsoft documents
[API sets as loader-resolved contracts](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets),
so they need not have same-named files in System32. Contract naming alone never
qualifies an import. Ordinary DLLs still require a packaged or physical system
file; ambiguous packaged names still fail.

Imported module names use ordinally sorted lowercase ASCII keys in both
PowerShell collection and Python validation, retaining the first original
spelling and deduplicating by key. This keeps suffixed MSVC runtime names and
punctuation independent of the runner's culture. `OrdinalIgnoreCase` alone is
insufficient: it places `libA.dll` before `lib_.dll`, unlike lowercase ASCII
ordering. Before collection, `test_pe_import_collection.py` passes actual PowerShell-produced
fixture evidence into the Python validator under two cultures, covering the
runtime names observed in run `34656962792` and duplicate/missing/ambiguous cases.

`pe-imports.json` includes `systemDirectory`, exact `apiSetResolutions` coverage
and retained `resolutionErrors`. The package validator rejects missing,
duplicate, extraneous or invalid contract/host records and any unresolved import.
The source inventory binds the collector and resolver helpers. Before collection,
`test_api_set_resolution.ps1` runs real collector/provenance fixtures and, on
Windows, resolves the four contracts observed in failed run `34653112133` plus
an unavailable-contract negative control. Local fixtures cannot establish native
resolution, a Windows version compatibility floor, exported-function availability
or installed MSIX success; the exact candidate still needs Windows qualification.

Only JSON, text, XML, the two actual small `.mmp` projects and screenshot evidence is uploaded. MSIX/EXE/DLL/package/certificate outputs stay in the disposable runner. The identity `Trieflow.BeatQuay.Qualification` / `CN=BeatQuay-CI-Qualification` is not a Store identity. Records keep license clearance, corresponding-source completion, public release, WACK, physical audio and Store submission false. A fresh successful Windows run is required before claiming any native packaging or installation result.


The installed consumer gate now uses the normal File menu to create a new project
from the packaged original CC0 Drum Grid, proves the actual Tempo context-menu value 112, sends exactly four guarded normal
wheel detents with fresh menu readback 113–116, saves `Evening Pulse.mmp`, creates a new empty project, reopens the saved
file, and saves its in-memory state as `Evening Pulse Reopened.mmp`. It then uses
the real WAV destination/settings/Start UI and requires the exact `Export
completed` dialog with the resulting path and byte count. No app test API,
configuration injection, synthetic screen, or CLI rendering substitutes for a UI
action. The read-only file checker reuses the tested CLI renderer's WAV inspection:
stereo PCM16 at 44100 Hz, four musical bars plus the normal one-bar tail
(10.3448276 seconds at 116 BPM, tolerance strictly below 0.25 seconds), audible AC
content in every musical bar, complete frames, and no PCM clipping. The two saved
projects must match all 55 authored notes, all three synth tracks and parameters,
and each other’s complete serialized head/track/mixer state. Exact file hashes
must remain unchanged through export. Kicker and every loaded runtime module are
reverified against the package record after the consumer workflow.

The native screenshots record the owned PID, current source, exact package and
executable hashes, actual desktop/window/DPI and unedited PNG hashes. The retained
CutQuay MIT display helper enumerates supported modes, uses CDS_TEST and a dynamic
nonpersistent mode change, then restores the original mode in mandatory cleanup.
The app is resized through the native window manager and a normal Song-Editor
title-bar double-click. Exact live SubWindow/content ancestry, geometry and a UIA
hit on that same retained element authorize each click; the editor must then fill
its observed MDI area within 30 seconds. Only that completed proof enables Qt’s
exact ` - [Song-Editor]` main-title suffix. The tempo editor uses the observed full
main-toolbar LcdSpinBox identity; actual 112 BPM readback still precedes the edit. Screenshots currently require final product-branding review;
no capture from this source candidate is yet Windows-qualified or public.

The absent-before-activation profile can acquire cleanup ownership only after the
normal first-run UI, exact working directory, creation interval and bounded XML
have been verified. Later writes may only add the exact opened/saved projects or
the seven source-traced editor preferences written on normal shutdown. Other
changes retain the last owned hash and fail closed. Attribution runs immediately
after proven template opening and, on workflow failure, before mandatory process
termination through the same live-owner/XML checks. Attribution failure is recorded
separately without replacing the primary UI error. Cleanup checks the original
creation time again and requires the original
process’s observed termination and an unchanged last verified profile hash.
Existing marker/working-directory, package, module, certificate and normal-close
requirements remain mandatory. Physical speaker playback, WACK, Store identity,
upgrade and public-release claims remain false.
