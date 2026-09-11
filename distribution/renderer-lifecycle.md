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
