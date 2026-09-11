# BeatQuay qualification MSIX

These MIT helpers build and install a temporary CI-only identity from the exact Windows native stage. They preserve the retained pipeline notices, bind original BeatQuay source/artwork/starters, copied Qt and vcpkg notices, same-run render results and every PE import. The full stage is copied byte-for-byte, then package-owned manifest, tiles and notices are added.

`distribution/qualify-candidate.ps1` is the supported entry point on a disposable Windows runner. It compiles/tests/renders the native app, records PE imports and notices, creates `build-evidence/package-input.json`, then invokes `cmake/msix/qualify-msix.ps1`. The latter runs portable/PowerShell regressions, uses Windows SDK 10.0.26100.0 MakeAppx, independently verifies the OPC container and SDK unpack, test-signs a private copy, installs it through the package broker, observes exact package/PID/path/hash/module identity, completes the real `BeatQuay - Settings` first-run dialog through its scoped `OK` control, requires the visible `BeatQuay 1.0.0` editor and screenshot, closes normally, and removes only the exact owned registration and ephemeral certificate.

The PE collector resolves nonpackaged Windows API-set imports through the actual
OS: `IsApiSetImplemented`, then `LoadLibraryExW` with
`LOAD_LIBRARY_SEARCH_SYSTEM32`, followed by `GetModuleFileNameW`. It records the
returned regular System32 host's size, SHA-256 and valid Microsoft Authenticode
signer, rechecks the bytes, and releases the loader handle. Microsoft documents
[API sets as loader-resolved contracts](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets),
so they need not have same-named files in System32. Contract naming alone never
qualifies an import. Ordinary DLLs still require a packaged or physical system
file; ambiguous packaged names still fail.

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
