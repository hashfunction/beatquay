# Task 4 export integration contract

Implementation starts from candidate `6b3d482be5a0ca4c7c5c20b51f6aa2e3dcb4c519`, after the coordinator's actual Windows `34605989969` passed the 13 CTest suites, ten lifecycle repetitions, typed CLI output-open failure and both authored renders. This is the approved Task 4 continuation, not acceptance/promotion of the modernization candidate or a Store release.

## Intended output ownership and publication

The GUI selects a destination and encoding settings before gathering current project, resource, timeline, encoder and destination facts. A blocking issue prevents renderer construction. Warnings display affected paths and recovery text; Continue authorizes that exact attempt once. Existing files require explicit replacement consent bound to a snapshot captured before the confirmation appears: normalized path, native file identity, size and SHA-256. A format/path change requires a fresh snapshot and confirmation. Project files and collected resource files (including filesystem aliases) are protected destinations.

GUI rendering uses an exclusive private staging directory beside the destination, retaining native identity for each file it creates. The final destination is not opened/truncated during encoding. Typed successful completion must include successful encoder closure and readable nonempty staged bytes. Each requested multi-track output is derived by the same production filename routine used by the renderer; results must correspond to those expected paths.

A new destination is published with an operating-system no-replace move. For an approved existing file, publication rechecks the snapshot, moves the prior file without replacement to a unique recovery location, and verifies the identity/content actually moved before publishing without replacement. A changed target, late new file, inaccessible destination or publication failure fails that output and preserves the original/recovery and staged render where needed. The user receives exact recovery/output paths. Successful replacement also retains the prior file at its disclosed recovery path; this avoids deleting user bytes during a replacement race and makes the operation recoverable rather than a claimed atomic compare-and-swap.

Cancellation and failed cleanup remove only files whose native identity is still the one created by this attempt. A substituted regular file, directory or link is preserved. No recursive staging-directory cleanup deletes unknown entries. Windows uses owned native handles where the API permits identity-bound cleanup; POSIX uses identity-checked displacement to a unique private location before removal, with conservative preservation on mismatch. No claim is made to defeat a malicious actor with the same user authority, arbitrary ancestor replacement, power loss, or every network filesystem behavior. Any residue/recovery path must survive into the typed result and UI.

The existing CLI syntax, typed status/exit handling, encoder finalization and batch order remain compatible. The unsafe pathname-only partial cleanup is repaired for all renderers, including the CLI. The GUI alone adds interactive preflight/replacement consent; no command-line interactive dialog is introduced.

## Planned tests and evidence

1. Real temporary-file RED/GREEN tests: cancelled output substituted by a same-size regular file, untouched resource/project sentinels, new output no-replace, approved replacement/recovery, changed identity/content after confirmation, late publication conflicts, link/directory refusal and residue preservation.
2. Actual checker/controller integration with renderer-construction callback: errors start zero renderers; Warning Continue starts exactly once; Cancel starts zero; failed/zero-byte completion cannot report success; valid output reports exact path/size; multi-track mappings and partial failures remain explicit.
3. Actual model adapter regressions in the full native suite for current song/pattern tracks, resource references and export settings. Local exact Qt 6.11.2 core tests and header/MOC compilation; no Mac GUI automation.
4. Preserve existing checker, filename, file-output, native lifecycle/CLI tests. Root runs the full Windows build, updated suite count, ten lifecycle repetitions and authored render smoke after independent review. Real native chooser/UI/cancellation tests remain Windows qualification gates and are not replaced by local fake-renderer tests.

This document records the intended contract before implementation. Final implementation, exact local RED/GREEN evidence, residual limitations and commit handoff will be appended as work completes.

## First implementation checkpoint: partial-file identity

The real-file cancellation regressions ran RED against the original AudioFileOutput: two failures (different bytes and identical bytes with a new native identity), nine existing results passing. Capturing the descriptor identity when opening and using ownership-aware removal makes all eleven results pass on macOS Qt 6.11.2. Windows removal opens a DELETE/attribute handle with rename/delete sharing excluded, rechecks native FileIdInfo and marks deletion through that handle. macOS uses native exclusive rename into a new cleanup directory, compares identity after displacement, and removes only the captured file. Failed ownership checks preserve the substitute; failed restoration/removal exposes the exact recovery path through the typed render output. Empty-only rmdir never recursively removes unknown directory contents. The common production source list includes the new helper. Native Windows compilation/API behavior still requires the next root qualification; this local checkpoint does not satisfy GUI publication or Task 4 completion.

Local logs: `build-evidence/task4-cancel-identity-red.txt` and `task4-cancel-identity-green.txt`.

## Second implementation checkpoint: publication primitive

`ExportOutputPublication` captures existing destination identity/size/SHA before consent and stages beside that path. Its initial missing source caused configuration RED; a compiling inert scaffold then produced nine meaningful behavioral failures (three fixture/control results passed). Native no-replace publication, identity/content revalidation, recoverable original displacement and conservative cleanup now pass all fifteen local Qt results. An additional resource-symlink regression first failed (13 passing, one failing), then passed after canonical resource identity was included; a real filesystem hard-link case also passes. Windows uses a real hard link in that case and explicitly skips only the POSIX symbolic-link-specific case because QFile::link creates Windows shortcuts.

The primitive retains staged renders after publication failure and previous files after successful replacement. Tests cover a late new target, a different file racing displacement, a new target after displacement, changed contents in the same inode, equal contents in a substituted inode, zero bytes, and preservation of unknown staging entries. It is registered in both standalone exact-Qt and the native full-suite CMake. Native Windows execution and integration with the renderer/GUI are still pending at this checkpoint. Logs: `task4-publication-{red,behavior-red,green}.txt` and `task4-publication-resource-alias-red.txt` under build-evidence.

## Final source integration and local verification

The GUI uses `ProjectExportFactsCollector` to inspect the current song/pattern-store tracks, selected timeline/loop settings, actual encoder availability and the existing `DataFile` resource-reference schema. It serializes to an in-memory document; it does not save the project. The current minimal candidate includes AudioFileProcessor, Kicker and TripleOscillator. This collector is not qualification for adding other resource-bearing plug-ins. Duration is an estimate at the current tempo, and the silence warning recognizes track mutes/master volume; neither preflight nor nonempty-file postflight proves perceptual audibility or integrates future tempo automation.

`ProjectExportSession` is the actual GUI decision boundary: errors prevent renderer construction, Continue consumes one attempt, and both resources and exact destination snapshots are rechecked after the warning dialog. `RenderManager::outputPaths` and rendering share the same track selection, numbering and filename routine. The GUI listens only to typed `completed`, checks every expected result and its readable nonempty output, reports exact byte counts and retained paths, and restores the previous song export settings after every terminal result. The legacy `finished` signal remains for compatibility but no longer drives GUI success. A failed export leaves the dialog available to retry with a new session/confirmation.

Format selection uses each combo item's actual enum data, and initialization reads the final filename suffix (so a dotted basename such as `mix.v2.flac` retains FLAC). Final format/path changes precede snapshot capture and require fresh replacement confirmation. The final one-line suffix correction also passed a separate actual-dialog syntax check, retained in `build-evidence/task4-dialog-final-syntax.txt`.

Authorized GUI outputs use `OutputSettings::requireNewFile` through the actual `AudioFileDevice`/`AudioFileOutput` chain. The encoder creates its stage with `QIODevice::NewOnly`; its captured open-descriptor identity is passed into publication even when initialization subsequently fails. This prevents a file already at the stage name from being truncated. The constructor's nested error message box was removed because it processed GUI events before ownership was established; typed completion now supplies the visible failure. CLI syntax and its ordinary output-open policy remain unchanged.

Additional behavioral RED/GREEN evidence:

- Session scaffold: 3 Qt results passed and 8 failed before implementing the decision/postflight boundary. The first missing-resource-after-warning assertion failed with 11 passing results; reopening current resources before renderer construction fixed it.
- Exclusive stage creation: the real-file assertion failed with 11 passing results while the existing file was truncated; `NewOnly` makes all 12 pass.
- Successful publication with an unknown entry in the private stage: the disclosure assertion failed with 15 passing results. The final result now preserves the entry and reports the retained directory; all 16 pass.

Final local verification, Qt **6.11.2**, macOS ARM64:

| Actual check | Result | Retained local evidence |
| --- | --- | --- |
| `AudioFileOutputTest` | 12 passed, 0 failed | `build-evidence/task4-file-output-final.txt` |
| `ExportOutputPublicationTest` | 16 passed, 0 failed | `build-evidence/task4-publication-final.txt` |
| `ExportProjectCheckIntegrationTest` (actual session, real temporary files, renderer callback) | 12 passed, 0 failed | `build-evidence/task4-session-final.txt` |
| `ProjectExportCheckTest` / `TrackFilenameFilterTest` | 33 / 132 passed, 0 failed | `build-evidence/task4-checker-filename-final.txt` |
| Python `test_candidate_render.py` | 13 passed | `build-evidence/task4-python-final.txt` |
| Actual adapters/manager/renderer/collector, new dialog, new native tests, generated MOC | C++20 `-fsyntax-only -Wall -Wextra -Werror`, exit 0 | `build-evidence/task4-adapter-syntax.txt` (empty successful compiler output), `task4-syntax-inputs.json` |

The syntax check used actual production translation units plus exact extracted modified `MainWindow::exportProject` and `DataFile::resourceReferences` methods with their production headers. A minimal Apple ARM64 config was generated from the real config template; this is **not a linked application build**. Missing local development headers were obtained from the existing vcpkg baseline `9e593bb18ea69cc5095e012465dcd675a822ed0d`: [libsamplerate 0.2.2 port](https://github.com/microsoft/vcpkg/blob/9e593bb18ea69cc5095e012465dcd675a822ed0d/ports/libsamplerate/portfile.cmake) and [libsndfile 1.2.2 port](https://github.com/microsoft/vcpkg/blob/9e593bb18ea69cc5095e012465dcd675a822ed0d/ports/libsndfile/portfile.cmake). Downloaded archive SHA-512 values were checked against those exact ports; URLs, hashes and syntax-only purpose are retained in the evidence JSON. No product dependency pin changed.

The full native CMake list now contains **16 CTest suites**. New full-engine cases exercise an actual sample/resource model without saving or changing input bytes, exclusive renderer creation, an actual WAV rendered through approved replacement, and cancellation while preserving the existing output. Those cases are authored and syntax checked, **not executed locally**. The coordinator must run the full Windows build/all 16 suites, ten lifecycle repetitions and actual CLI render/preservation checks. The publication symlink-specific test explicitly skips on Windows because `QFile::link` makes a shortcut; the separate real `CreateHardLinkW` alias test is enabled there.

Independent review, native Windows file-identity/no-replace behavior, actual chooser/overwrite/cancel dialogs, Unicode/inaccessible destinations, device/MIDI/DPI work, modernized project round trips, resource/source/license closure and installed-package qualification remain open. These source changes do not promote the modernization candidate, mark Task 4's real-Windows gate complete, or authorize publication.
