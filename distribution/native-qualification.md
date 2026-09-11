# BeatQuay candidate native qualification

Status on 2026-09-11: **candidate qualified for isolated feature development;
full modernization and release acceptance remain pending**.
The original `apps/beatquay/source` remains clean at v1.2.2
`94363be152f526edba4e884264d891f1361cf54b`. This isolated candidate began at
`518a7e8ef525a276ba9702df87c613ea0ff25c47`. The original commit is already an
ancestor of the candidate; no history rewrite is required for eventual adoption.

## Actual Windows evidence

Run [34591912855](https://github.com/hashfunction/beatquay/actions/runs/34591912855)
at source `b298ce3ddb8877ca12be05af8d2bc1b1a9ef2ff2` / public snapshot
`0d11f3e50122171e3d6a9101372adf93651ec6c6` built the actual application, passed
all nine native CTest suites, installed the candidate stage, and passed both
authored MMP/MMPZ renders through Unicode paths. Both outputs were identical
non-silent stereo PCM16 WAVs: 44100 Hz, 176384 frames, 705624 bytes, peak 7864,
SHA256 `5be09d25f4c6b85e0ed6e5842e6bda6a3584347384678ce8e4ff8d313bda0482`.
Both inputs retained their original bytes. The coordinator-downloaded
`Release/artifacts/run-34591912855/BeatQuay-Windows-candidate-metadata/build-evidence/`
contains `result.json` and `render-smoke.json`; `modernization_accepted`,
`source_license_closure` and `physical_audio_verified` remain false. This result
permits the isolated development checkpoint in the approved plan; it does not
qualify subsequent feature commits until they run on Windows too.

Earlier RED evidence:

Run [34589415265](https://github.com/hashfunction/beatquay/actions/runs/34589415265)
used candidate `76184f7e5725cd65aa366af7f81f374a406b9627` and completed all
323 build steps, including the actual application and minimal instruments, with
Qt **6.11.2** and MSVC **19.44.35228 x64**. All eight existing native CTest suites
passed, including the authored `RelativePathsTest` fixtures. The ninth suite,
`CommandLineCodecTest`, passed its two missing-file cases but failed its Unicode
round-trip during input open: `音符-é.mmp` became `??-�.mmp`. CTest correctly
returned failure. Installation and staged rendering did not run. The diagnostic
log is retained at `apps/beatquay/Release/artifacts/windows-34589415265-failed.log`.
This supersedes the application compile failure in run `34587223881`, repaired
by the checked codec opens in `9677685a`.

The locked vcpkg commit remains `9e593bb18ea69cc5095e012465dcd675a822ed0d` and
the 20 recursive submodule commits/tree hashes remain pinned in
`candidate-inputs.json`. The current Qt pin replaces the plan's Qt 6.8 assumption.

## Unicode command-line repair

The failing Windows test is the RED evidence. After application construction,
`main.cpp` was rebuilding every value from narrow `argv`, whose encoding had
already lost the requested filename. The parser now reads one immutable
`QCoreApplication::arguments()` list after Qt processes its options, and uses
that list consistently for values and bounds. This covers upgrade/bundle inputs
and outputs, codecs, render input/output, import, profile, config and positional
project paths. The optional import `-e` lookahead is bounded because a QStringList
has no terminating null element.

Qt's exact [6.11.2 core implementation](https://github.com/qt/qtbase/blob/v6.11.2/src/corelib/kernel/qcoreapplication.cpp)
recovers native Windows arguments with `CommandLineToArgvW` and filters options
consumed by the derived application. Supplying modified arguments can disable
that recovery. The redundant `--geometry` pointer rewrite is therefore removed.
Qt's [6.11.2 GUI parser](https://github.com/qt/qtbase/blob/v6.11.2/src/gui/kernel/qguiapplication.cpp)
already handles both dash spellings. The early fullscreen detection is retained;
the legacy `geometry` alias remains XCB-specific, while Qt's `qwindowgeometry`
is platform-independent. This repair does not broaden that existing alias.

The original Unicode assertion remains strict. The actual application CTest now
contains eight cases, adding paths with Unicode/spaces/apostrophes, Qt-consumed
platform/geometry/style options before and after the file, omitted/empty codec
arguments and an import path as the final argument. The compressed bytes are
also decoded independently with Python zlib after checking the four-byte length.
Every round-trip checks that both original files retain their bytes.

Local validation uses Qt **6.11.2 EXACT** in an ignored, offscreen harness compiled
from the production codec/import/file-check blocks. All eight cases pass with
`-Wall -Wextra -Werror` and `QT_FORCE_ASSERTS`; no window is created. Removing the
import bounds guard from the generated harness makes its final-argument test fail
with Qt assertions enabled; restoring the guard passes. The normal release-Qt
probe did not diagnose that out-of-bounds mutation, so its absence of a crash is
not used as evidence. The original Windows Unicode defect does not reproduce on
this UTF-8 macOS host. These local block-level checks are **not a complete app
build or a Windows GREEN result**. The separate Windows GREEN result is now
recorded above from run `34591912855`.

Local commands (from this candidate checkout):

```sh
python3 .cache/qt-cli-arguments/extract.py
cmake -S .cache/qt-cli-arguments -B .cache/qt-cli-arguments/build -G Ninja -DCMAKE_PREFIX_PATH=/opt/homebrew
cmake --build .cache/qt-cli-arguments/build
python3 tests/scripted/cli-codec-test.py --executable .cache/qt-cli-arguments/build/CliArgumentsProbe
python3 tests/scripted/test_candidate_render.py
```

The last command's three WAV-inspector cases also pass. Evidence is retained in
`build-evidence/cli-arguments-*.log` and `cli-import-mutation-*.log`. For Windows,
use the unchanged `distribution/qualify-candidate.ps1`; its CTest registration
runs the same eight CLI cases against `$<TARGET_FILE:lmms>`. No workflow or
compiler-flag change is required for this repair.

## Staged render smoke preparation

After CTest and installation to a fresh stage, `qualify-candidate.ps1` records
its complete file inventory and runs `tests/scripted/candidate_render.py`.
The script generates one original bar of four notes using the native
TripleOscillator and the v1.2.2 XML schema. It renders both XML and Qt-compressed
forms from filenames containing Unicode and spaces, with explicit fresh WAV
destinations and a private configuration using Unicode/spaces as well. No sample, preset or demo content is used. These are qualification
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
and pass afterward (audible PCM, nonempty silence, empty file). Both actual staged
native renders subsequently passed in run `34591912855`, as recorded above.

Local ignored evidence is in this candidate's `build-evidence/`:
`qt-open-probe-red.log`, `qt-open-probe-green-build.log`, `cli-probe-red.log`,
`cli-probe-green.log`, `path-fixture-red.log`, `path-fixture-green.log`,
`render-inspection-red.log`, `render-inspection-green.log`, and
`qualifier-powershell-parse.log`. PowerShell parsing uses real 7.6.6 on macOS;
it does not execute Windows build/install operations.

## Acceptance and advancing the original checkout

Every subsequent Windows feature qualification must build the actual app, pass
every CTest, inspect the installed stage and pass both actual native renders.
The successful native baseline run still leaves representative v1.2.2 project save/reopen semantics,
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
