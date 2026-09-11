# Project export checks: Task 3 development handoff

Status on 2026-09-11: the pure Task 3 engine is implemented in the isolated
candidate, based on `b298ce3ddb8877ca12be05af8d2bc1b1a9ef2ff2`. Task 4 adapters,
dialogs and renderer result handling are not implemented by this change.
The original v1.2.2 checkout remains unchanged. Full modernization acceptance
remains false; see `native-qualification.md` for the separate passing baseline
Windows run and remaining product/release gates.

## Contract and scope

`ProjectExportCheck::beforeExport` checks supplied track/timeline/resource facts,
the real `ProjectRenderer::ExportFileFormat`, encoder availability and output
state. It reports typed errors for empty projects, invalid ranges/durations,
unavailable encoders, missing/unreadable resources and unusable destinations.
Confirmed silence and an existing writable regular destination are warnings.
Silence can be intentional; no audio analysis is inferred from a track count.

`afterExport` requires evidence that this render succeeded and its encoder closed,
then checks the supplied output existence, regular-file status, readability and
positive size. An old nonempty file cannot pass while `renderCompleted` is false.
The adapter must obtain facts from the correct render and actual output path:
the pure engine cannot prove provenance, eliminate filesystem races, decode the
audio, establish the requested format or detect nonempty silence. Positive size
alone deliberately does not make those claims. Actual renderer output validation
in Task 4 must go beyond a file-size check and retain the existing independent
native WAV smoke checks.

The engine performs no I/O and mutates neither facts nor the song. It does not
authorize replacement or delete partial output. Issues have explicit stable
numeric codes, severity, the exact Unicode path, translatable text and a recovery
action. Errors precede warnings; code and exact path determine the remaining
order. Repeated identical resource issues collapse to one issue. Filesystem and
song traversal belong to the subsequent adapters.

The real renderer enum remains nested with the same values and ABI. Its header
now forward-declares audio types so the pure engine does not pull in libsamplerate
or encoder dependencies. Existing renderer/UI consumers include `AudioEngine.h`
explicitly. A production compile-time assertion checks the lightweight factory
declaration against `AudioFileDeviceInstantiaton`; no factory type changed.
`RenderManager.h` now declares its own `Track` pointer type and includes `vector`.
A separate local Qt 6.11.2 compiler probe also passes for the renderer manager,
export dialog and checker headers together without the audio engine header
(`build-evidence/project-export-check-headers.txt`).

## RED/GREEN evidence and commands

The standalone CMake target compiles the actual production `.cpp` and the same
QtTest file registered in the normal application CMake suite. It requires Qt
**6.11.2 EXACT**, uses C++20 and treats compiler warnings as errors. It does not
replace the renderer or audio engine with test implementations.

1. Before adding the engine, configuration failed because the production source
   did not exist (`build-evidence/project-export-check-target-red.log`).
2. With typed declarations and empty implementations, compilation succeeded and
   QtTest returned exit 25: **8 passed, 25 failed**, with expected missing issues
   (`project-export-check-behavior-red.txt`).
3. The production implementation passes **33 Qt results** (31 test invocations
   plus initialization/cleanup), **0 failures, 0 skips**; CTest passes its one
   registered standalone suite (`project-export-check-green.txt`).

Run from this candidate checkout:

```sh
cmake -S tests/project-export-check -B .cache/project-export-check -G Ninja -DCMAKE_PREFIX_PATH=/opt/homebrew
cmake --build .cache/project-export-check
ctest --test-dir .cache/project-export-check --output-on-failure
.cache/project-export-check/ProjectExportCheckTest -o build-evidence/project-export-check-green.txt,txt
```

Local evidence uses macOS and Qt 6.11.2; it is not a Windows or complete app build.
The test rows cover all four formats, invalid format/sentinel values, negative
track counts, zero/reversed/negative ranges, NaN/infinite duration, Unicode and
unreadable resources, writable-existing-file warnings, unusable outputs,
incomplete renders with old output, zero/negative size, deterministic ordering,
deduplication and input immutability. No real filesystem state is guessed from
the supplied paths.

For the coordinator's unchanged full Windows qualification, `tests/CMakeLists.txt`
now registers **ProjectExportCheckTest** alongside the nine existing suites
(ten CTest suites total). The production engine is in `lmmsobjs`. The existing
full build and CTest invocation picks up both changes automatically. For a
targeted run in a configured native build:

```powershell
cmake --build build --target ProjectExportCheckTest
ctest --test-dir build -R '^ProjectExportCheckTest$' --output-on-failure
```

No workflow, root qualification script, build flags or dependency pins change.
The full Windows application build, all ten suites and both actual Unicode-path
renders must pass at the new commit; the earlier baseline pass is not evidence
for these new source changes.

## Source-driven Task 4 follow-up

The approved intent is actionable preflight and truthful post-render results.
Inspection of the actual candidate reveals that simply attaching postchecks to
`RenderManager::finished` would not provide that contract:

- `RenderManager::render()` calls `renderNextTrack()` even when the renderer's
  `isReady()` is false; an empty queue then emits `finished` after failed startup.
- The encoder is owned by `AudioEngine`. `RenderManager` restores/deletes that
  device in its destructor; a completion listener must not inspect bytes before
  explicit encoder finalization. Finalization matters to buffered output and
  audio container headers.
- Track export changes mute state and chooses each actual destination through
  `pathForTrack`. Cancellation disconnects the finish chain, waits for the
  renderer and restores mutes. `ExportProjectDialog` currently closes on the
  untyped finish signal and releases the manager in `accept`/`reject`.

Task 4 therefore needs a tested terminal result contract for failed startup,
successful finalized output and cancellation, including each track destination
and mute/device restoration. Add these integration regressions before attaching
checks. Gather preflight facts after existing chooser/overwrite decisions and
before rendering; block errors and explicitly confirm warnings. Preserve project
and export state on failure/cancel, respect the existing partial-output cleanup
contract, and retain the user's overwrite choice. Resource traversal must cover
the actual minimal instruments/sample tracks rather than guess from XML names.
No Task 4 UI behavior was changed in this Task 3 commit.

Still open: Task 4, authored starters, owned branding/MSIX, representative project
round trips, GUI/DPI/cancellation, physical audio/MIDI/device reconnect, long
renders, clean installation/WACK and complete license/corresponding-source
closure. The passing baseline fixtures are qualification music, not shipped
starter arrangements.
