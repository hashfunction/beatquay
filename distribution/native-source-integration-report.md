# BeatSprig native source and original notice integration

Prepared 2026-09-12 against the source following `c50e0bd0` (the independently reviewed export-combo correction). This candidate changes source/notice collection, runtime origin evidence, package notice inputs and the About license presentation. It does not change audio processing, consumer input, native runtime selection, installation identity, ownership, cleanup or acceptance requirements. No public upload, source-delivery completion, Windows success, Store submission or site change is claimed.

The input assessment remains `Release/native-source-collection/README.md` outside this application checkout. Its original manifest SHA256 is `deceed8df5e92f3824543883a36b242e82a4b4aac2b29955d101c67d790e2e62`. It maps the actual 78 PE files and 581 ordinary stage assets from run 34690526888/public source `6e741892c2a87c1f2759e074b1c144bf8dca3762`. Those historical observations are not rewritten as results for this candidate.

## Original inputs and delivery preparation

The source bundle contains 197 original Qt files: generic license/REUSE files, all 79 attribution JSON files, their original referenced notices and three source condition files. Every byte has its Qt Git blob hash and SHA256. Five upstream attribution files have literal control characters: they are parsed only as data with `strict=False` and copied unchanged. The collector rejects missing references, altered bytes/Git blobs, extra files, escaping paths and symlink parents.

The native notice bundle adds 51 original files for the compiled hiir/ringbuffer inputs, Qt-derived ControlLayout and LADSPA headers, and vcpkg dependencies. Original application GPLv2 text and authors remain untouched. Ringbuffer is compiled into core and permits GPLv3-or-later; the combined executable is conveyed under GPLv3. The package and About include the complete original GPLv3 text and an explanatory combined-work notice, while preserving the application and each component's original grant. Git attributes preserve original notice line endings, including hiir's CRLF text.

`native-source/source-release.json` prepares exactly 17 source archives (108,354,372 bytes): eleven actual vcpkg downloads, the full pinned vcpkg recipe/helper repository, QtBase/QtSvg/QtTools, hiir and ringbuffer. SHA256, SHA512, exact length, immutable revisions and proposed public URLs are explicit. All 17 retained archives were reread successfully from `/private/tmp/beatsprig-corresponding-source/archives`; the readback is `/private/tmp/beatsprig-native-source-integration-archive-readback.json`. Original archives were left intact and no additional large download or extraction was needed.

The manifest SHA256 is `38537badf5e029ed8a934b21e6e2e9c53c8a61e89a6441a124889265c7f2fd5f`; native original-notice manifest SHA256 is `1b7d4f0f3c7e40c6d418b14896918915c3774e18d802ef2cba61ca4938b29994`; Qt notice manifest SHA256 is `aca0be36fe340b7b7be9c31412649a9c85a076606122c7c21c30b16379d2524f`.

The current build collector independently hashes the eleven actual cached downloads against both source digests, binds exact Qt binary inputs and compiled module pins, and requires the same successful native build's source commit. Package verification rereads every native/Qt original and actual vcpkg copyright copy. Every staged PE must map to an application/source owner or an independently verified Microsoft redist original. QtTools remains build-only; its unexpanded Assistant qlitehtml gitlink does not describe a shipped QDoc, Assistant or LLVM runtime. The original Zlib source remains included as a build input even though no separate Zlib DLL is staged.

`native-source/SOURCE.md` supplies current-source build/install instructions and `native-source/UPLOAD-PLAN.md` gives the exact draft/upload/readback/public-verification sequence. The proposed release is `hashfunction/beatquay` / `beatsprig-native-source-1.0.1`. All publication, full corresponding-source and license-clearance flags remain false. The current public application commit and a separately verified public delivery receipt must accompany the final package.

## Microsoft runtime origin evidence

The existing CMake discovery writes `ms-runtime-selection.json` with the exact selected release source paths, discovery module/hash, SDK/redist roots, architecture and configuration. Both existing release and Debug-only installation rules remain unchanged. The Windows collector rereads originals and staged files, records size/SHA256/file and product versions/observed signature metadata, then rereads originals and the selector to detect changes. Files are opened read-only and closed deterministically; reparse points are refused.

Before packaging a separate Python verifier checks the complete staged Microsoft filename set, each exact original in the release x64 VC143 CRT or selected SDK x64 UCRT directory, stage/original byte equality and the actual CMake discovery module hash. Missing, duplicate, debug, wrong-architecture, unrelated-directory, altered and unlisted runtime observations fail closed. Empty version fields or a `NotSigned` observation are retained honestly because an SDK forwarder may lack resources or a catalog may be unavailable. A signature observation is not a fabricated redistribution clearance.

The two exact receipts are included under `licenses/Microsoft` in the package. Official Visual Studio redistribution/license and UCRT deployment terms are referenced in the receipt; these proprietary runtimes are not asserted to have GPL corresponding source. The new actual Windows SDK/redist origin observation is pending the next native build.

## Verification

Executed locally with Python 3.10, CMake/Ninja, Qt 6.11.2 and PowerShell 7.6.6:

| Command from source root | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/scripted -p test_qt_notices.py -v` | 7 passed |
| `python3 -m unittest discover -s tests/scripted -p test_native_source.py -v` | 8 passed |
| `python3 -m unittest discover -s tests/scripted -p test_release_runtime.py -v` | 1 test, all 8 real CMake generator/configuration cases passed |
| `python3 -m unittest discover -s cmake/msix -p test_ms_runtime_origins.py -v` | 5 passed |
| `python3 -m unittest discover -s cmake/msix -p test_msix_qualification.py -v` | 18 passed |
| `python3 tests/scripted/test_license_resource.py -v` | Real Qt resource compile/read/About presentation passed |
| `pwsh -NoLogo -NoProfile -File cmake/msix/test_ms_runtime_collection.ps1` | Actual readonly hash/metadata, closed handle, directory refusal passed |
| `pwsh -NoLogo -NoProfile -File cmake/msix/test_consumer_export_combo.ps1` | 3 actual captured selections, 11 refusal cases, 2 input failures without replay passed |
| `pwsh -NoLogo -NoProfile -File cmake/msix/test_consumer_workflow.ps1` | Existing control/ownership/profile/MDI completion fixtures passed; expected negative-case tracebacks retained |
| `python3 distribution/native_source.py verify-archives --archives /private/tmp/beatsprig-corresponding-source/archives` | All 17 exact SHA256/SHA512/length checks passed |

Regressions were observed failing before repair for omitted original attribution/reference/Git evidence, Git line-ending conversion, missing runtime selection, missing detailed package notices/origins, incorrect source-build binding, absent staged PE owner mapping, missing packaged Microsoft receipts, and the old GPLv2-only About resource. The About test compiles the production CMake resource selection, `embed::getText` function and license-label statement, using real Qt resources and `QTextEdit`; it does not substitute successful UI observations for the consumer workflow.

The full Windows native build, new per-DLL origin observation, installed consumer workflow and final package are pending. Historical native evidence is retained separately. No timeout, menu predicate, tempo/edit/save/render/reopen assertion or cleanup condition was relaxed.

Final index verification reread all 248 inventoried original Qt/native notices using `git show :path` and matched each exact length and SHA256. Original `LICENSE.txt`, `doc/AUTHORS` and `doc/UPSTREAM_README.md` have no diff. All four edited/new PowerShell scripts parsed successfully and `git diff --cached --check` passed. Only the two generated Python cache files owned by this work were removed; the source archives and assessment evidence remain intact.
