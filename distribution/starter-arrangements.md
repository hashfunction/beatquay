# BeatQuay Task 5 source preparation

Prepared against candidate `1c7ab3af1b4c54673177c87185d323e3b07f1607`. This extends approved Task 5. Implementation began after the coordinator captured Task 4's exact frozen snapshot `9f5fcd57a1a39a35da039e98dc68c4af86bac228`, tree `356cb211f7bd46a44dfa69a1a71b9c294f9eb2bc`. The original v1.2.2 checkout is not an implementation target.

## Source-derived schema and install flow

- `src/core/DataFile.cpp` has 31 upgrade methods and uses integer format version 31 for current documents. Use `lmms-project version="31" type="songtemplate" creator="BeatQuay source generator"` with `head` and `songtemplate` children. Record the schema base commit in provenance; do not claim a GUI save.
- `Song::loadProject` reads the declared content element and its `trackcontainer`; `Song::createNewProjectFromTemplate` loads it and clears the save filename. The native test must call that actual template method and verify that saving cannot overwrite the template by default.
- `Track::loadTrack` reads instrumenttrack settings and restores MIDI clips. `MidiClip::loadSettings` reads tick position/length, regular notes, velocity and panning. `Note` uses current MIDI keys 0..127, with A4 = 69; this avoids the legacy octave-upgrade path. Each one-bar clip has 192 ticks, 16 steps, offset 0, autoresize false and explicit length.
- `KickerInstrument::loadSettings` requires explicit `version="1"` to avoid historical decay/envelope changes. Start/end note tracking is disabled for fixed-frequency percussion. Only synthesized oscillation/noise is used.
- `TripleOscillator::loadSettings` reads explicit oscillator settings. Built-in triangle/sine waveform values are 1/0, signal mix is 2. No user-wave paths or UserDefined waveform value 7 are permitted. All three oscillator parameters are set explicitly, including the silent third oscillator.
- `src/gui/menus/TemplatesMenu.cpp` scans readable `*.mpt` under `factoryProjectsDir()/templates` and uses filenames as labels. No product menu refactor is needed. The candidate deliberately has no `data/projects` directory and no projects install entry: add an explicit `data/projects/CMakeLists.txt` naming only these two files and provenance, then add that directory to `data/CMakeLists.txt`. Do not restore upstream globs, demos, shorties, samples or presets.

## Original arrangements

All numbers below are new editorial choices for this task, not copied from existing demos, presets, songs or samples. Generator output is deterministic XML; synthesized noise means audio is assessed by properties, not a promised stable audio hash.

### Four-bar Drum Grid

112 BPM, 4/4, 55 regular notes in three directly editable instrument tracks, with four one-bar clips per track. Master volume 70. Kicker-only voices:

| Voice | Track volume | Start/end Hz | Decay ms | Noise | Click | Notes within successive 192-tick bars |
| --- | --- | --- | --- | --- | --- | --- |
| Low pulse | 50 | 150/48 | 210 | 0 | 0.12 | 0,72,96 / 0,84,144 / 0,48,96,156 / 0,72,120,168 |
| Backbeat | 28 | 260/110 | 125 | 0.6 | 0.08 | 48,144 / 48,144 / 48,144 / 48,132,156 |
| Short ticks | 16 | 900/620 | 42 | 0.35 | 0.02 | 0,24,48,72,96,120,144,168 in every bar |

All voices use gain 1, mild distortion 0.1, explicit envelope/frequency slopes, fixed-note key 60 and short regular-note lengths. Velocities provide accented main beats and quieter offbeats. Names describe the synthesis rather than asserting acoustic instrument realism.

### Eight-bar Bassline Sketch

108 BPM, 4/4, 40 notes in one TripleOscillator instrument track, eight one-bar clips. Track volume 32, master volume 70. Triangle oscillator at volume 70/coarse 0 plus sine at volume 30/coarse -12, zero stereo/fine offsets and built-in antialiasing enabled; third oscillator volume 0. Roots by bar: MIDI 36,36,32,32,34,34,31,36. Five onsets per bar: 0,36,72,120,144; lengths 30,18,30,18,36. First seven bars use root offsets 0,7,0,10,12; final bar 0,12,7,3,0. Velocities vary within a conservative fixed range. No sound-shaping automation IDs, external files or effects are required.

## Test-first implementation and native gates

1. Before generation, write a Python semantic/allowlist check and tests: the two exact template names must exist, type/version/header/ranges must be valid, bar/track/note counts match, every note is within its clip, and there are no sample/resource/plug-in paths, user-wave values, effects, external MIDI routes, unexpected instruments or other shipped project files. Observe missing-assets RED. Real altered fixtures must reject added source paths, external instrument/effect names, invalid note/bar ranges and substituted stage bytes. Run the real explicit CMake install fragment into a temporary stage and compare the actual installed tree/bytes, rather than checking text in CMake.
2. Implement deterministic generator and generated `.mpt` files. `--check` regenerates in memory and compares exact bytes without modifying product files. The generator uses exclusive writes or an explicit development-only output directory; verification must never rewrite a fixture to make it pass. Record generator, source schema and arrangement hashes in provenance.
3. Add `BeatQuayTemplateTest` to the full native CMake list. Call actual `Engine::init(true)` and `Song::createNewProjectFromTemplate` on both source fixtures; require no `Song::hasErrors`, exact instrument names, expected notes/positions/lengths/velocities, tempo/bar count and empty project save filename. Compare an independent semantic snapshot before/after actual `Song::saveProjectFile` to an owned Unicode `.mmp` and `Song::loadProject`. Verify template/source bytes unchanged. Use current `ProjectExportFactsCollector` and `ProjectExportCheck::beforeExport` to require no error for WAV.
4. Test actual production `RenderManager` with each loaded original arrangement and a new owned temporary output; await typed completion with a bounded timeout. Decode stereo PCM16 44.1 kHz, require positive frames near the actual four/eight-bar duration plus configured tail, nontrivial peak and reasonable level, no load errors and no changed original template. Verify save/reload preserves the same semantic composition and can still render. Do not settle for a nonzero file if it is silent or undecodable.
5. Add a source-read-only native CLI smoke helper that receives the actual installed stage and exact templates. Compare installed template/provenance bytes with the source inventory, render both through Unicode destinations using the actual stage executable in isolated config/PATH, inspect audible PCM and preserve input hashes. Retain logs, exact source/stage/output hashes and truthful result metadata only. Root integrates/dispatches its Windows qualifier; no helper may claim a native pass without actually executing the renderer successfully.
6. Keep native CTest/plugin-loading and installed-stage CLI distinct: CTest proves model/save/load APIs; the installed stage proves deployment and synth availability. Menu interaction, native GUI save, physical playback, device/DPI/MIDI behavior and final installed MSIX checks stay explicitly pending until observed.

## Provenance and implementation checkpoint

These two starter arrangements are generated from original note, velocity, timing and synthesizer parameter choices authored by Codex for Trieflow LLC under the user's approved BeatQuay task on September 11, 2026. They were not copied from LMMS demos, presets, sample packs or third-party compositions. They contain no sampled audio, user waveforms, external instrument/effect references or device bindings. They were authored from the exact candidate source schema, not saved through an accepted application GUI. `BEATQUAY-PROVENANCE.md` records exact arrangement/generator/schema/synth source hashes; `starter-inputs.json` binds both source and installed templates/notices plus the generator hash. The arrangement data are dedicated under CC0-1.0 to the extent rights exist; the upstream synthesizers/application retain their GPL notices. Native loading/rendering and menu qualification remain pending.

The first asset/install tests produced three intended failures because the original arrangements and their install rule were absent. After generation and explicit install implementation, the tests pass. The stage/audio verifier's inert scaffold produced eleven behavioral failures plus one missing-result-key error in the positive control; its implementation now passes the real file/audio corruption controls. The generator uses exclusive creation and `--check` is read-only. Local tests invoke the actual CMake install file in an isolated configure/install directory and compare the exact installed file set and bytes. No upstream music directories were restored.

### Native test host and limits

`BeatQuayTemplateTest` embeds the actual `lmmsobjs` core, exports its symbols and lives in a separate `build/tests/template-host/lmms.exe`. The normal Windows synth DLLs import `lmms.exe`; using the usual differently named QtTest executable could import another copy of the core with different Engine globals. [CMake's export documentation](https://cmake.org/cmake/help/latest/prop_tgt/ENABLE_EXPORTS.html) describes this executable import-library model. The test host keeps the expected module basename and asserts Windows module identity, exactly one loaded `lmms.exe`, and the actual loaded Kicker/TripleOscillator paths and SHA-256 values against bytes captured before loading. This design relies on the documented [Windows loaded-module lookup](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order); its actual behavior still must pass on Windows. No customer CLI probe flag was added.

The native test compares loaded notes, clip positions/lengths and synth parameters against the authored XML before comparing a save/reload. It calls the actual template API, checks the default save filename is empty, checks project preflight, renders the reloaded song using `RenderManager`, and decodes its PCM for duration, audible level and clipping. It retains paths/hashes and semantic/render observations in Qt's test log. The test host is a separate qualification executable, not the installed consumer application. The source CMake adds this seventeenth suite when both required synth targets are built; the approved minimal candidate includes both.

The genuine installed-stage application must additionally render each installed `.mpt` with this helper after `cmake --install`:

```powershell
python distribution/generate_starters.py --check
python -m unittest discover -s tests/scripted -p 'test_starter*.py' -v
python tests/scripted/starter_render.py --source . --stage stage --work .cache/native-starter-smoke --evidence build-evidence
```

The helper verifies the exact input inventory, source/stage bytes and generator hash before launching the actual stage executable with an isolated config, then checks exit code, each original's unchanged hash and decoded PCM. It rechecks all input bytes and the executable after rendering. Logs and `starter-render.json` are created exclusively; an existing evidence file is preserved and prevents success. Failure reports keep `native_installed_starter_renders_passed=false`; GUI/menu, physical-audio, installed-MSIX and source/license gates are always explicitly false here. Root owns integration and native dispatch.

Local evidence is retained under `build-evidence/task5-*`. The current Qt 6.11.2 MOC and actual native test source pass C++20 syntax checking with `-Wall -Werror`, matching the repository's Clang warning policy. The first syntax attempt also exposed a missing `Instrument.h` include, which was fixed; an extra `-Wextra` outside the repository's policy reports the pre-existing unused `size` parameter in `NotePlayHandle.h`. No warning policy or upstream header was changed. The previously hash-verified minimal Apple syntax configuration/dependency headers from Task 4 were reused; this is not a linked/native test execution.

Final local checks at handoff:

- `python -m unittest discover -s tests/scripted -p 'test_starter*.py' -v`: **18 passed**, including actual temporary CMake configure/install, exact generated bytes, no-overwrite generator behavior, real stage/XML substitutions, input/notice/generator hash checks, extra projects, symlinks, PCM corruption and actual helper CLI failure/evidence preservation. Log: `task5-python-final.txt`.
- Existing `test_candidate_render.py`: **13 passed**. Log: `task5-existing-render-tests.txt`.
- `python distribution/generate_starters.py --check`: both exact original template hashes match the checked-in inventory/provenance.
- Actual native test source/MOC syntax: exit **0**. Log: `task5-native-syntax.txt` (empty successful compiler output). No native RED/GREEN execution is claimed: Windows plugin imports, model loading, round trips and genuine installed-stage rendering are still required.
- `git diff --check`: clean. No workflow, qualifier, account, site, public snapshot, release status or original v1.2.2 source changes were made by this task.

The Windows qualifier now checks the deterministic generator and all 22 starter
fixtures, then renders both exact installed templates through the staged native
CLI. Its final result records starter render success only after these commands
exit zero. The CTest pass includes the actual template API/round-trip/render suite
when the two required synth targets are present. Public metadata preserves the
starter report and render logs; application binaries remain withheld.


### Diagnostic repair after independent Task 5 review

The independent review reproduced lost failure diagnostics at source
`67b47fbda88aec69f0f9ee11b2aeb6386ecffd2d`: a real child timeout discarded
captured stdout/stderr, and an occupied render-log path replaced an observed
exit-7 renderer failure with only a file-publication error. Both cases correctly
failed qualification, but their primary error evidence was unavailable.

Each attempt is now recorded before launch. Exit/timeout, original-file
revalidation and captured output are recorded before exclusive log publication;
logging errors are separate from the primary process outcome. The report retains
at most 64 KiB of each output stream (head and tail, with a truncation flag and
full captured byte count). Full captured streams still go to the exclusive log
when possible. If the final report cannot be created, its bounded attempt
records are included in the caller-visible failure message. Existing log/report
bytes are never replaced. The native timeout remains 180 seconds and all
success, input-preservation and decoded-audio checks remain required.

Three new real-process regressions failed first: timeout output/attempt missing,
exit-7/log collision missing the attempt, and simultaneous log/report collisions
hiding the renderer failure. After repair all pass; a fourth real-process case
checks bounded head/tail fallback for more than 100,000 captured bytes. The
fixtures replace only the application-launch boundary with a real Python child;
they do not count as native synth/render execution. All **22 starter tests**,
the unchanged 13 candidate-render tests, generator `--check`, PowerShell 7.6.6
qualifier parsing and diff checks pass locally. Root supplied the qualifier's
required-suite inventory gate, three starter commands and final success flag;
those root-authored changes are included in the repair handoff commit. The
repair requires separate root review and fresh Windows qualification.
