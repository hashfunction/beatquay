# BeatSprig native XML verifier repair

Base source: `e0672b39` (owned nested Qt dialog discovery). This change only
repairs the read-only Python verifier and its regression fixtures. It does not
change the installed application, UI input, package ownership, export oracle,
profile attribution, cleanup, source qualification, or acceptance conditions.

## Actual Windows evidence

Run `hashfunction/beatquay/34690526888`, public source
`6e741892c2a87c1f2759e074b1c144bf8dca3762`, installed the disposable package
`Trieflow.BeatQuay.Qualification_1.0.1.0_x64__a74jba1vjrwc6` with SHA-256
`4fac4c874e3cfdd18a508157b7a320c936644d7000011e1c26e0328a909759a0`.
Its actual receipt is retained at
`/private/tmp/beatsprig-34690526888-review/build-evidence/msix-install/consumer-workflow/consumer-workflow.json`
(754,226 bytes; SHA-256
`1b9e92fee6ff2ae5421b028d147fd40532a3f6c013fed6eb343ae0b51c2d9c03`).

The receipt records original-template selection, maximized Song Editor, tempo
112 through 116, project saved, and a new empty project before reopen. The last
owned main window is `Evening Pulse Reopened - BeatSprig 1.0.1 - [Song-Editor]`,
PID 8124. The actual screenshot was viewed: three tracks, four bars, 116 BPM,
and the native project-saved notification. At `11:34:42 UTC`, the Python
verifier raises `External/internal XML entities are not accepted` at line 25,
called from `verify_projects` while checking a saved project (line 57).
`acceptance=false`, `file_verification=null`, and `wave_verification=null`.

No saved `.mmp` bytes are retained in this failed artifact: production copies
the two small projects only after the later export checks pass. Therefore the
precise failed project's XML contents are not claimed here. The CDATA trigger
below is an inference supported by the native serializer and a direct Qt
reproduction; it is not a quotation from the missing Windows file.

## Proven verifier defect and bounded correction

The old test rejects a file when `DOCTYPE` appears and `[` appears anywhere in
the bytes. It cannot distinguish an internal DTD subset from ordinary bracket
text, attribute values, comments, or the `<![CDATA[` marker.

The existing native sources establish the serialization route:

- `src/core/DataFile.cpp:128` creates `QDomDocument("lmms-project")`; `write`
  calls `save(stream, 2)` at line 309.
- `src/gui/ProjectNotes.cpp:380` stores `QTextEdit::toHtml()` in a QDom CDATA
  section. The existing `tests/emptyproject.mmp` also contains this structure.
- `src/core/ConfigManager.cpp:635` separately creates
  `QDomDocument("lmms-config-file")` and serializes the `<lmms>` profile.

The retained `cmake/msix/fixtures/native-project-notes-qt6.cpp` executes the
same Qt document, text-edit, CDATA, and save APIs. The actual local Qt 6.11.2
output is `native-project-notes-qt6.xml` (743 bytes, SHA-256
`fa3bbf8eb0a130af46fb31c57e28c5e714437498410032511876d2ad94276ed1`).
It contains the empty document type declaration `<!DOCTYPE lmms-project>` and an HTML
PUBLIC declaration inside CDATA. The old verifier rejects that exact output.
This is a serializer fixture, not synthetic consumer-acceptance evidence.

The replacement uses the standard-library Expat start-doctype, entity, and
external-reference callbacks before the existing ElementTree semantic parse.
[Python's documented callback](https://docs.python.org/3/library/pyexpat.html#xml.parsers.expat.xmlparser.StartDoctypeDeclHandler)
reports the exact declaration name, optional system/public identifiers, and
whether an internal subset exists. Project parsing allows only the source's
empty `lmms-project` declaration; profile parsing allows only its empty
`lmms-config-file` declaration. No declaration remains valid for templates and
existing synthetic fixtures. Any other name, SYSTEM/PUBLIC identifier
(including an empty identifier), internal subset, entity declaration, or
external entity reference fails before ElementTree. Malformed or undeclared
entities also fail. CDATA HTML remains ordinary text. UTF-16 is checked by the
parser as well, closing the old byte scan's encoding bypass.

The original 2-MiB/10,000-element limits, regular-file boundary checks,
55-note/three-track/four-bar authored data, 116 BPM, exact reopened musical
semantics, WAV checks, and restricted profile-difference rules remain intact.

## Verification

Before the correction, the expanded suite failed on the actual Qt fixture,
ordinary brackets, and profile brackets, and accepted 13 prohibited declaration
cases. Evidence: `/private/tmp/beatsprig-xml-red.log`.

After the correction:

- `python3 cmake/msix/test_consumer_files.py -v`: 16 tests pass, including the
  original 11 file/audio/profile cases and five new declaration cases. Eighteen
  prohibited UTF-8/UTF-16 declaration variants must fail before ElementTree.
  Native CDATA is inserted into the full authored arrangement; its positive
  comparison passes, while a reopened BPM mutation still fails.
- `python3 cmake/msix/test_msix_qualification.py -v`: 15 tests pass.
- `TMPDIR=/private/tmp /Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File cmake/msix/test_consumer_workflow.ps1`:
  production consumer/control/ownership/completion/profile checks pass,
  including the existing negative foreign-profile and cleanup cases.
- The retained C++ fixture was compiled with clang++ C++17 and
  `pkg-config --cflags --libs Qt6Xml Qt6Widgets`, run with
  `QT_QPA_PLATFORM=offscreen`, compared byte for byte with the retained XML,
  and parsed successfully by the production verifier. Qt reports 6.11.2,
  matching the failed Windows job's recorded Qt version; the local platform is
  macOS, not Windows.
- `git diff --check` passes. Python verification used 3.10.11; Windows CI runs
  the same existing test entry point on its recorded Python 3.12.10.

Logs are `/private/tmp/beatsprig-xml-green.log`,
`/private/tmp/beatsprig-xml-package-tests.log`, and
`/private/tmp/beatsprig-xml-consumer-ps.log`. A fresh exact Windows run must
establish the saved files, export, normal close, and cleanup before consumer
acceptance. No push, public snapshot, site, Store, or parent status was changed.
