# BeatQuay qualification MSIX

These MIT helpers build and install a temporary CI-only identity from the exact Windows native stage. They preserve the retained pipeline notices, bind original BeatQuay source/artwork/starters, copied Qt and vcpkg notices, same-run render results and every PE import. The full stage is copied byte-for-byte, then package-owned manifest, tiles and notices are added.

`distribution/qualify-candidate.ps1` is the supported entry point on a disposable Windows runner. It compiles/tests/renders the native app, records PE imports and notices, creates `build-evidence/package-input.json`, then invokes `cmake/msix/qualify-msix.ps1`. The latter runs portable/PowerShell regressions, uses Windows SDK 10.0.26100.0 MakeAppx, independently verifies the OPC container and SDK unpack, test-signs a private copy, installs it through the package broker, observes exact package/PID/path/hash/module identity, completes the normal working-directory and Settings prompts, requires the visible `BeatQuay 1.0.0` editor and screenshot, closes normally, and removes only the exact owned registration and ephemeral certificate.

Fresh startup first asks `Working directory` whether to create the exact Qt
Documents `/BeatQuay/` path; `GuiApplication` waits for this answer before it
constructs the Settings dialog. The qualification helper observes the exact
title, complete question/path and one visible enabled `Yes` belonging to the
retained installed process, then requires `BeatQuay - Settings` and its exact
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

Only JSON, text, XML and screenshot evidence is uploaded. MSIX/EXE/DLL/package/certificate outputs stay in the disposable runner. The identity `Trieflow.BeatQuay.Qualification` / `CN=BeatQuay-CI-Qualification` is not a Store identity. Records keep license clearance, corresponding-source completion, public release, WACK, physical audio and Store submission false. A fresh successful Windows run is required before claiming any native packaging or installation result.
