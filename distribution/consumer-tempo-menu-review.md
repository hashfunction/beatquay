# BeatSprig native tempo popup observation repair

Prepared 2026-09-12 against source `a9b685c5a6dce5f25318b444ffd49577fe4fae09` and public source `165d115b2ab6370dd1b86d9963ad0b27914e41f4`.

## Exact Windows failure

[Run 34684975836](https://github.com/hashfunction/beatquay/actions/runs/34684975836) was not a vcpkg/bootstrap failure. The step named “Verify immutable inputs and bootstrap vcpkg” invokes the entire candidate pipeline. The actual log and metadata establish successful compilation, native tests, starter renders, repeated lifecycle tests, exact package/source binding, disposable MSIX installation and owned startup. The ordinary consumer failed later at `edit_tempo_116`: `Exact complete owned consumer window did not appear: Tempo`.

The genuine `qualification-window.png` was viewed first; it is the initial editor screenshot, not a tempo-menu screenshot or a final marketing asset. The later consumer receipt contains actual complete menu evidence. PID 4796 opened the original Drum Grid and maximized Song-Editor, then sent one proved context click at (502,117) at 09:24:40.0101652 UTC. Its last observation contains a visible/enabled `lmms::gui::CaptionMenu` root with role **Window**, title/name **BeatSprig**, and automation ID `QApplication.lmms::gui::CaptionMenu`. Its eight controls include a unique disabled `Tempo` caption and enabled `Copy value (112)` action, both MenuItem/QAction descendants. The probe instead expected a root with role Menu and title Tempo, based on the preceding explicitly hypothetical provider fixture. The real native context click succeeded; selection of its actual accessible window failed.

`cmake/msix/fixtures/tempo-menu-34684975836.json` preserves the exact eight-node menu snapshot and receipt SHA256 `51a0861cbea41f6635978b7a6549e80b9ffffe061dabbb4d53e4cda111a7b358`. It was compared directly with the downloaded receipt. Package SHA256 was `2d16bb21fa6f9f88376050ace120f4abca83c6bc58e0099874a1954e387365da`, executable SHA256 `18d91e5494a605bd6e700e6edb082955759aa5a20d26a3ad1eb4218ec0b85c9e`; 106 loaded modules were recorded. No wheel input, tempo 116, save, reopen or UI export was reached. Normal close and uninstall acceptance flags remained false; owned failure cleanup exited -1, recorded no residual package and no cleanup/evidence errors. These are failed-run facts, not consumer acceptance.

## Repair and preserved behavior

The observer now waits for the exact actual BeatSprig popup title, then requires the observed Window role, CaptionMenu class and automation ancestry. The disabled Tempo caption and the exact enabled `Copy value (N)` action remain unique and owned; their actual QAction ancestry is checked as well. An unrelated window with the same title cannot authorize the tempo route.

After the existing guarded Escape, dismissal requires the actual visible CaptionMenu to disappear from a complete owned inventory. Checking the old title Tempo would have falsely accepted the still-visible actual popup immediately. An altered title cannot hide a remaining CaptionMenu; a truncated or unavailable inventory cannot grant dismissal.

This changes only qualification observation and its regression fixture. It preserves BeatSprig 1.0.1 / beatsprig.exe, host-plugin import requirements, original CC0 template/source attributions, actual four-detent wheel route and proof of every value 112 through 116, exact pointer-hit/native ownership checks, saved/reopened project contents, independent WAV checks, full UI export, packaged modules, normal close, profile attribution, uninstall and owned cleanup. No product, binary, package, dependency or workflow acceptance gate was replaced.

## Verification

The captured menu fixture first failed against the old production assertion with `Unexpected tempo context menu`. It now passes. The production-boundary fixture covers the actual popup selector, 24 menu mutations (role/title/name/class/ancestry/PID, hidden/disabled/unavailable roots and actions, missing/duplicate caption or value, wrong value), same-title foreign provider refusal and complete/visible/hidden/renamed/incomplete dismissal cases. Existing exact live tempo geometry, native pointer guard, input order and four-detent stop-boundary checks remain passing.

- 32 MSIX/consumer Python tests pass, including actual PE-import collection across cultures, renamed host/plugin imports, saved project persistence, altered notes/tempo/instrument refusal and WAV silence/partial-song checks.
- 47 scripted source/runtime/template/identity/render/license tests pass.
- All 13 isolated PowerShell fixtures pass, including the actual native input helper, process/registration/module ownership, API-set fixtures, display restoration and consumer profile/cleanup boundaries.
- All 21 PowerShell scripts parse; `git diff --check` passes. The exact captured fixture matches its source JSON and bound SHA256.

Local PowerShell: `/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`. Set `TMPDIR=/private/tmp`; put its directory on PATH for `test_pe_import_collection.py`, and set `BEATQUAY_TEST_PWSH` to that executable for source-checkout tests. The first broad local attempts lacked this runtime setting; both complete suites passed after correcting the test environment, with no source workaround.

Logs are `/private/tmp/beatsprig-tempo-menu-{red,green,msix-python,scripted-python,powershell}.log`; actual artifacts are under `/private/tmp/beatsprig-34684975836-review`, with the failed native log at `/private/tmp/beatsprig-34684975836-failed.log`.

Independent review and a fresh exact-source Windows consumer run are required. No new native success, final screenshot, physical audio, release approval, Store action, public push, dispatch, website or parent status change is claimed.
