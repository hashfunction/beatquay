# Renderer lifecycle prerequisite for Task 4

This is a bounded implementation in the isolated modernization candidate, after
Task 3 `7f0e7a26915af7d135f5d7b8cba05e5fe80e9711`. It does not add the preflight
adapter or check dialog, starters, branding or packaging. The original v1.2.2
checkout remains unchanged and full modernization acceptance remains false.

## Behavior and ownership

`RenderManager::completed(const RenderResult&)` publishes one terminal value:
`Succeeded`, `Failed` or `Cancelled`, with the actual path, status, encoder
finalization state and error for every attempted output. A failed batch keeps
successful output records and continues attempting the remaining tracks, as the
old batch loop did. Cancellation stops the queue; unattempted tracks are not
reported as rendered. An empty track batch fails with a reason. A failed encoder
startup no longer follows an indistinguishable successful finish path.

The worker stops song export and audio processing. On the owner thread,
`ProjectRenderer::finalize()` joins the worker, explicitly finishes the encoder
and closes the output once. Cancellation then attempts the existing partial-file
removal, recording whether it succeeded. A failed removal is retained in the
cancelled output result for the forthcoming UI to explain. The manager restores
original track mutes and the stored audio device before publishing completion.
Queued/duplicate completion and repeated start/cancel calls cannot start another
render or publish another terminal result. Manager destruction joins and cleans
up an active worker without emitting a terminal signal during destruction.

The encoder belongs to `ProjectRenderer` until it is installed as the audio
device, and then belongs to `AudioEngine`. Finalization closes encoding/file
resources but does not delete an installed device; the engine deletes it during
the next device switch or restoration. Every derived encoder destructor can
safely request finalization again. Thread-shared progress/cancellation flags are
atomic. Completion listeners may delete the manager; the independent result value
and guarded legacy signal avoid accessing that deleted owner.

The legacy `finished` signal remains after ordinary success or failure, preserving
existing listeners; it is still not emitted on cancellation. **It is not a success
signal.** The existing export dialog still consumes it; adapting that dialog to
the typed result belongs to the next Task 4 step. The CLI now consumes the typed
result and queues the appropriate process exit, including startup failure before
the event loop starts. The CLI manager is owned by the application and no longer
relies on a leaked manager/device for output closure.

## Encoder and file boundary

The new production `AudioFileOutput` owns the real `QFile` and records short or
failed writes. Its finalization invokes the encoder while the descriptor is open,
then flushes/closes the file and preserves any earlier failure. Repeating it does
not flush the encoder twice. Removal is refused before finalization and for a
destination that was never opened by this object. This preserves the existing
chosen-path cancellation contract; it does not add an atomic replacement or
filesystem identity guarantee, and does not authorize overwriting a destination.
Chooser/overwrite preflight remains a Task 4 adapter responsibility.

All four existing encoders implement explicit finalization:

- WAV/FLAC check short frame writes and `sf_close`, and clear the closed handle.
- FLAC uses the already-open descriptor, as WAV does, preserving Unicode paths;
  it rejects a null encoder and applies compression only after a successful open.
- Ogg tracks partial initialization, handles failed output opens and encoder
  operations, flushes its trailer once and only clears initialized state.
- MP3 handles negative encode/flush results without an assertion-only failure,
  guards failed initialization and closes its encoder once.

`AudioFileDevice` reports headless open errors to stderr and returns initialization
failure instead of terminating the process from its constructor. The manager can
therefore publish the failed output and restore state. GUI open-error reporting
otherwise retains its existing behavior. No new dependency or codec is added.

## Evidence

Native regression checkpoint `a172503677a590a51cb9313a7ca97f7a680c3387` first added
three tests against the unchanged renderer: readable output/restored device inside
finish notification, cancellation cleanup while the manager remains alive, and
multi-track destinations/mutes/device restoration. Windows run `34596612563`
initially failed while unpacking Qt tools (`Bad7zFile`), before compilation;
that infrastructure failure is **not native regression RED evidence**. The
coordinator queued a retry of the same snapshot. Its result and the repaired
commit's full Windows qualification must be recorded separately.

Local TDD on macOS with **Qt 6.11.2 EXACT**:

- The new file-output target initially failed because its production source did
  not exist. With a compiling but non-finalizing implementation, **6 cases failed,
  2 fixture results passed** (`build-evidence/audio-file-output-red.txt`).
- The production implementation passes **9 Qt results**, including the added
  failed-removal case, with no failures/skips. These tests use real temporary
  Unicode files, descriptor closure, encoder footer writes, failed open/write,
  retained failure, an unrelated file and an unopened existing destination
  (`audio-file-output-green.txt`).
- The unchanged Task 3 checker suite still passes all **33 Qt results**.
- Exact-Qt header and generated MOC compilation passes for the renderer manager
  and renderer, including the new typed signal (`renderer-lifecycle-headers.txt`
  and `renderer-lifecycle-moc.txt`). This is not a full native application build.

The expanded **RenderManagerLifecycleTest** uses actual `Engine::init(true)`,
`SampleTrack`, `RenderManager`, native encoders, temporary files and libsndfile
decoding. It checks the initial regressions plus typed statuses, invalid/sentinel
formats, inaccessible directory destinations, duplicate completion/cancellation,
partial batch failure, empty batches, multitrack cancellation, owner destruction,
deletion from a completion listener, and every available encoder through Unicode
paths. Its sample tracks intentionally contain no external resources; decodable
silence is sufficient for lifecycle tests, while the unchanged authored native
smoke separately requires non-silent music. Codec rows follow real availability;
the exact Windows result must report which rows ran. These expanded native tests
have **not been run on macOS**, which lacks the full pinned audio build.

Local commands:

```sh
cmake -S tests/audio-file-output -B .cache/audio-file-output -G Ninja -DCMAKE_PREFIX_PATH=/opt/homebrew
cmake --build .cache/audio-file-output
ctest --test-dir .cache/audio-file-output --output-on-failure
cmake --build .cache/project-export-check
ctest --test-dir .cache/project-export-check --output-on-failure
```

The root-owned Windows qualifier requires no new flags or workflow edits. CMake
now includes **12 CTest suites**: the nine baseline suites, ProjectExportCheckTest,
AudioFileOutputTest and RenderManagerLifecycleTest. Targeted native checks:

```powershell
cmake --build build --target RenderManagerLifecycleTest AudioFileOutputTest ProjectExportCheckTest
ctest --test-dir build -R '^(RenderManagerLifecycleTest|AudioFileOutputTest|ProjectExportCheckTest)$' --output-on-failure
ctest --test-dir build -R '^RenderManagerLifecycleTest$' --repeat until-fail:10 --output-on-failure
```

Required before treating this repair as natively verified: compile the full
application with the pinned Windows toolchain, pass all 12 suites and repeated
lifecycle tests, and rerun both real authored MMP/MMPZ Unicode-path renders.
The earlier Windows baseline pass does not validate these changes. Also verify
the actual CLI exits nonzero on output-open failure and exits after successful
finalization. Full GUI/dialog cancellation, physical devices/MIDI, project
round-trip compatibility, clean installation and source/license gates remain
open. No Windows success, Store readiness or full Task 4 completion is claimed.

## Windows diagnostic and qualification follow-up

Exact downloaded logs and metadata from runs `34596612563` attempt 2 (test-only
`a1725036`, public snapshot `5ad6aa2f6ad6df27a6cd31fee160e20ffee4606d`) and
`34597834544` (repair `833d9413`, public snapshot
`54593e9531273fbe5c30a9642cf40d248e622f67`) establish that both full application
builds completed. The test-only run passed 10/11 suites; the repair passed 11/12.
Only `RenderManagerLifecycleTest` failed in each run. This supersedes the earlier
Qt extraction failure and the earlier lack of a native compile result.

Neither downloaded `LastTest.log` nor CTest JUnit report contains the Qt assertion
results. The test-only lifecycle output is empty; the repair records only the two
intentional inaccessible-destination stderr messages. Those messages alone do
not identify a failing assertion. No renderer change is justified by guessing
which case failed. Logs are retained in the app's adjacent `Release/artifacts/`
as `windows-34596612563-attempt2-failed.log` and
`windows-34597834544-failed.log`; full metadata is under the matching
`run-<id>-diagnosis/BeatQuay-Windows-candidate-metadata` directories.

Diagnostic commit `df6c02e9f90d5d0e2391bdc4039124864a066ec0` makes every native
QtTest write explicit JUnit XML and text reports, and preserves them under
`build-evidence/qt-tests` even when CTest fails. The exact logger arguments were
run on local Qt 6.11.2 and produced all nine file-output test records. The
coordinator's Windows diagnostic run `34600483516` uses exact public snapshot
`8ce5a808a5023dbed7e0385f4482fe7d8af42630`. Its assertion results are pending at
this qualification-coverage checkpoint; the lifecycle suite is not yet GREEN.

The qualifier now requires ten successive executions of the actual native
`RenderManagerLifecycleTest` through `ctest --repeat until-fail:10`, with
`--no-tests=error`, a retained repeat log and JUnit report. The same CTest command
shape was exercised locally against `AudioFileOutputTest` ten times to verify
the options; that is not a Windows lifecycle pass. Only after the real Windows
command returns success may `result.json` report ten passed lifecycle repetitions.

The staged native smoke now also renders the authored MMP fixture to an existing
directory at the exact Unicode `.wav` destination. The test requires exit code
**1**, the actual typed terminal-handler diagnostic and exact output-path line,
unchanged source bytes, and unchanged directory contents. It rejects exit 0,
crash codes, the old constructor-only exit, an unrelated/prefix-matching output
path and changed files. A 60-second timeout detects a lost pre-event-loop exit or
an unexpected interactive error. The actual invocation and stderr/stdout go to
`render-output-error.log`; `render-smoke.json` records the observed status and
preservation hashes. Generated projects/audio remain private. This specifically
checks output-open failure; it does not claim an induced native disk-full or
encoder-finalization failure.

Local TDD for the new failure inspector: eight missing-function errors before
implementation; two subsequent failing regressions for unexpected directory
contents and path-prefix confusion; final **13 Python tests pass**, including
the three existing real-WAV inspection tests. Evidence is in
`build-evidence/render-error-*.log`. The qualifier passes a real PowerShell 7.6.6
AST parse on macOS; no Windows operations were run locally.

The independent review's Task 4 gates remain explicit: pathname-based cancellation
can delete a substituted regular file, and the legacy GUI still accepts the
untyped `finished` signal for failures. Ownership-safe staging/publication and
replacement-survival regressions, explicit overwrite consent, source/resource
preservation and typed GUI error handling must be implemented in Task 4. Passing
this bounded lifecycle qualification cannot waive those gates.

## Case-level diagnosis and bounded repair

Windows diagnostic run `34600483516` completed the full build and retained the
individual results: **18 lifecycle results passed, one failed, zero skipped**.
The report is adjacent at
`Release/artifacts/run-34600483516-diagnosis/BeatQuay-Windows-candidate-metadata/build-evidence/qt-tests/RenderManagerLifecycleTest.qt-test.txt`;
the exact failed-run log is `Release/artifacts/windows-34600483516-failed.log`.
Actual device restoration/finalization, cancellation, invalid format/startup,
empty batch, owner destruction, owner deletion from completion and each available
WAV/FLAC/Ogg/MP3 decoder check passed on Windows. This supplies native evidence
for those cases at the diagnostic commit, not for subsequent source changes.

The only failure was a **test expectation defect** in
`partialBatchFailureRetainsSuccessAndRestoresMutes`. The existing renderer pops
the back of the two-track queue and numbers that output `2_same.wav`; it then
attempts `1_same.wav`. The fixture blocked `1_same.wav` with a directory but
incorrectly expected the first result to be Failed. Windows correctly reported
the first result as Succeeded and the batch as Failed. The repair preserves the
renderer order and verifies every result's exact numbered path, status, encoder
finalization and error. It now tests both failure-after-success and
success-after-failure, confirms the valid output decodes, and confirms the
blocked directory, mutes and device survive. This strengthens the batch test;
no assertion is skipped and no renderer behavior is changed to satisfy it.

The same native report exposed a separate inherited **source defect**: every
track export warned that `FILENAME_FILTER` was an invalid QRegularExpression,
so removal of forbidden filename characters did nothing. The shared constant
in `Track.h` now uses valid PCRE2 `\x{...}` character-range escapes, preserving
its intended ASCII control/punctuation set and Unicode text. Its two existing
consumers (track export and instrument preset filename suggestion) are unchanged.
This is not a general Windows filename/ownership/publication safety policy.

`TrackFilenameFilterTest` includes the actual production `Track.h`, without a
copied pattern or fake track implementation. With exact local Qt 6.11.2 and
warnings as errors, the old constant produced **44 failures / 88 passes**;
the fixed constant passes **132 results**, zero failures/skips. The cases check
pattern validity, all 128 ASCII characters, composed/decomposed Unicode, an emoji,
mixed forbidden characters and empty text. Logs are
`build-evidence/track-filename-filter-{red,green}.txt`. A native lifecycle case
now also renders a track name containing forbidden characters plus Unicode and
requires the exact filtered output path and a decodable WAV.

The existing standalone project-export-check CMake directory now runs both
`ProjectExportCheckTest` and `TrackFilenameFilterTest`; Qt Gui is required for the
real Track header's QColor type, but no window or GUI application is created.
The production pure checker still links only Qt Core. Both focused suites pass
locally (33 and 132 Qt results). The file-output suite still passes 9 results,
and the staged smoke/error inspector still passes 13 Python tests.

The next root snapshot must run the combined changes, including coverage commit
`940124e30243a5848c6f646456c2e1f4cdfb5fae`: full native build, **13 CTest suites**
(new target `TrackFilenameFilterTest`), ten repeated lifecycle runs, both authored
non-silent Unicode MMP/MMPZ renders and the actual typed CLI output-open failure
exit. These combined Windows GREEN results are pending. The Task 4 ownership-safe
cleanup/publication and legacy GUI failure-handling gates above remain open.
