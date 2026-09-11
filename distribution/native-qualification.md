# BeatQuay candidate native qualification

Status on 2026-09-11: **candidate only; not accepted for product features**.
The original `apps/beatquay/source` remains clean at v1.2.2
`94363be152f526edba4e884264d891f1361cf54b`. This isolated candidate began at
`518a7e8ef525a276ba9702df87c613ea0ff25c47`. The original commit is already an
ancestor of the candidate; no history rewrite is required for eventual adoption.

## Actual Windows evidence

Run [34587223881](https://github.com/hashfunction/beatquay/actions/runs/34587223881)
built source tree `6b9731c9f0fcd2b7278ceb15ff3064ac86094cac` (local source
`573a2f0cd2866e370ce9be7eb250b983deede250`, public snapshot
`78d1bedf5ec54853a419d80d2a8ad4f3d536fbfd`). Exact tree equivalence was verified.
Its toolchain was Qt **6.11.2**, MSVC **19.44.35228 x64**, CMake **3.31.6**,
Ninja **1.13.2**, Windows SDK **10.0.26100.0**, and Python **3.12.10**.
The locked vcpkg commit is `9e593bb18ea69cc5095e012465dcd675a822ed0d`.
All 20 recursive submodule commits/tree hashes matched `candidate-inputs.json`.
The current Qt pin replaces the plan's older Qt 6.8 assumption.

The run compiled the core objects and linked all eight existing Qt test
executables. It failed compiling the application at `main.cpp:449` and `:465`:
C2220/C4834, ignored `QFile::open` results under `/WX`. CTest, staging and runtime
smoke did not run. Earlier core open-error fixes are not suppressed warnings.
The complete diagnostics are retained locally at
`apps/beatquay/Release/artifacts/windows-34587223881-failed.log` and
`Release/artifacts/run-34587223881-agent/` (relative to the app).

Commit `9677685a` checks both CLI codec opens, reports the affected input and
returns failure before producing output. A real local Qt 6.11.2 compiler probe
failed first for the discarded nodiscard result. The exact CLI source blocks,
compiled in an isolated QtCore harness, then failed two missing-file assertions
and passed all three regression cases after repair, including a Unicode
compress/dump round-trip with original bytes preserved. This harness is not the
full Windows executable. `CommandLineCodecTest` now runs those same cases against
the actual built application in CTest with an offscreen Qt platform.

`RelativePathsTest` depended on a removed factory audio asset. A QtCore path
probe confirmed that its real `data:/samples/drums/kick01.ogg` lookup fails in the
candidate. The test now owns temporary, explicitly non-audio ASCII/Unicode path
fixtures and restores its prior Qt search paths. Production path conversion is
unchanged, and the full native QtTest remains to be run.

## Staged render smoke preparation

After CTest and installation to a fresh stage, `qualify-candidate.ps1` records
its complete file inventory and runs `tests/scripted/candidate_render.py`.
The script generates one original bar of four notes using the native
TripleOscillator and the v1.2.2 XML schema. It renders both XML and Qt-compressed
forms from Unicode filenames, with explicit fresh WAV destinations and a private
configuration. No sample, preset or demo content is used. These are qualification
fixtures, not the approved product starter arrangements.

Each rendered output must be stereo 44100 Hz PCM16, have complete frames and a
reasonable duration, and contain an audible signal; nonempty silence fails.
Both original project hashes must remain unchanged. Child processes have a
180-second timeout. On Windows, render subprocess PATH contains only the stage
and Windows system directories, so Qt/vcpkg build directories cannot satisfy
missing staged DLLs through PATH. This is still a provisioned CI machine, not a
clean consumer installation or proof that all Windows prerequisites are bundled.

Generated project/audio files stay under the ignored `.cache/native-render-smoke`
directory. Only logs, hashes and measured metadata go to the publicly uploaded
`build-evidence` directory. The fixture notes and XML generator were authored for
this test by Trieflow LLC on 2026-09-11; test code is GPL-2.0-or-later. No third-party
music is embedded. The three local WAV-inspector tests fail before implementation
and pass afterward (audible PCM, nonempty silence, empty file). The actual staged
native render has **not run** at this handoff.

Local ignored evidence is in this candidate's `build-evidence/`:
`qt-open-probe-red.log`, `qt-open-probe-green-build.log`, `cli-probe-red.log`,
`cli-probe-green.log`, `path-fixture-red.log`, `path-fixture-green.log`,
`render-inspection-red.log`, `render-inspection-green.log`, and
`qualifier-powershell-parse.log`. PowerShell parsing uses real 7.6.6 on macOS;
it does not execute Windows build/install operations.

## Acceptance and advancing the original checkout

The next Windows run must build the actual app, pass every CTest, inspect the
installed stage and pass both actual native renders. A successful native baseline
run will still leave representative v1.2.2 project save/reopen semantics,
automation/mixer compatibility, project-format backward compatibility, UI/DPI,
physical audio/MIDI, cancellation, device reconnect and long-render gates open.
The smoke does not claim those behaviors, MSIX installation, WACK or license
clearance. Remaining themes/icons, native plug-ins/codecs, Qt modules, transitive
vcpkg packages and corresponding source need the final commercial/GPL audit.
The removed music content must stay excluded until individually cleared.

After the coordinator reviews and accepts the candidate for the next stage,
verify both checkouts are clean, preserve the original tag, fetch the exact
accepted commit from this local candidate, and fast-forward `codex/beatquay` with
`git merge --ff-only <accepted-commit>`. Recheck all 20 submodules and record the
accepted commit/tree and original ancestry in the modernization record. Do not
advance the original checkout or label the full modernization accepted solely
because compilation passes. No original source checkout was changed by this task.
