# Exact unsigned Store export review

This source candidate adds an opt-in exporter after the already reviewed fixed
qualification and Store installation lifecycles. It does not establish a new
Windows success, upload a public binary, or submit to the Store. Current Windows
run 34699319354 remains on its reviewed public source; this candidate was neither
pushed nor dispatched.

## Export boundary

`cmake/msix/export_store_package.py` requires Windows, the exact GitHub repository,
an explicit workflow-dispatch opt-in, the reviewed 40-character public commit,
and positive string run/attempt identifiers. It proves the clean local Git
commit/tree against the anonymous public commit API. Both original private
unsigned packages and their installer-consumed records are retained separately.
The exporter reconstructs their records through the existing native-stage,
source, PE import, runtime-owner, notice, original Microsoft DLL, manifest, ZIP
and SDK unpack checks. It rereads the exact MakeAppx and sibling SignTool bytes.

`store_workflow_evidence.py` requires both complete original installed/consumer
receipts, all seven completed operations and eight completed cleanup operations,
normal exits 0, exact package/process/helper bindings, original display
restoration and sequential lifecycle times. It verifies the actual startup and
post-workflow module inventories, 13 ordered consumer stages, four tempo wheel
detents, original file-picker receipts, export settings and completion details.
The two retained projects are independently rechecked against the current starter
source, and all three raw screenshots are rehashed and checked against their
observations. The recorded WAV must retain the full typed PCM16, dimensions,
duration, byte/hash, peak/RMS and four-bar musical energy evidence. The audio was
inspected before owned cleanup; `waveRereadAfterCleanup` explicitly remains false.

The only additions to consumer/lifecycle production code are observations:
completed callback names are appended only after each callback returns; UTC
lifecycle start, already checked loop-toggle values and already checked 16-bit
sample width are recorded. Existing UI input, PID/window/foreground ownership,
file inspection, normal-close, uninstall and cleanup acceptance are unchanged.

`source_publication.py` anonymously streams and rehashes the published 17 native
source archives plus four original notice/guide/manifest assets. All 259 original
notice members are bound to the current source and Store payload. Historical
preparation flags remain unchanged. The new export receipt records only source
delivery verified for the exact current minimal native stage, with the current
public application commit and the original native publication commit distinct.
There is no blanket license, WACK, upgrade, hardware audio or Store-acceptance
claim.

Before and after output, local source/package/SDK/original-DLL/lifecycle checks
run again. The exclusive `build-evidence/store-export` directory contains exactly:

- `BeatSprig_1.0.1.0_x64.msix`
- `BeatSprig_1.0.1.0_x64.export.json`

The JSON embeds the Store package record and original input/tool/evidence hashes,
both lifecycle summaries and public source verification. Output cleanup refuses
changed, replaced, linked or unexpected files and preserves the original error.
The workflow's exact two-file artifact is success-only and requires
`export_store_package=true`; its default is false. The reviewed public source
input passes through environment data, not interpolated shell code.

## Evidence and verification

All 63 focused Python tests pass: 22 package tests, 16 actual consumer-file tests,
4 publication tests, 9 installed-workflow evidence tests and 12 exporter tests.
All 18 PowerShell fixture scripts invoked by the qualifier pass, including eight
new cases executing the actual production dispatch tail and assertions that
throwing callbacks never enter completed-operation lists. The macOS local
PowerShell fixtures use `TMPDIR=/private/tmp`; the ordinary `/var` temp alias is
correctly rejected by the existing reparse guard and that guard was unchanged.

```sh
python3 cmake/msix/test_msix_qualification.py -v
python3 cmake/msix/test_consumer_files.py -v
python3 cmake/msix/test_source_publication.py -v
python3 cmake/msix/test_store_workflow_evidence.py -v
python3 cmake/msix/test_export_store_package.py -v
TMPDIR=/private/tmp /Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File cmake/msix/test_store_export_dispatch.ps1
```

Meaningful refusals include missing/false/typed receipt fields, changed run or
attempt, incomplete/incorrect cleanup order, missing normal close, rejected
module origins, changed helpers/projects/screens, wrong PCM width, replayed wheel
magnitude, wrong file-field PID, stale screenshot handles/times, modified private
package records, original redist/SDK bytes, signed containers, dirty Git source,
wrong public commit/tree, unavailable/corrupt source assets, duplicate JSON keys,
reparse ancestors, preexisting/foreign/replaced output, and partial-copy failure.
The ancestor-reparse and replaced-directory write cases were reproduced red
before their respective refusal checks and then passed.

The real production downloader also performed a fresh anonymous TLS-verified
readback: current public commit `dc8145e166b3dee5c6ce68f7f375acc8310c5dfa`, tree
`51a6c5eff4a2d5a613c28c20ea7e239cd204d568`, all 17 source archives totaling
108,354,372 bytes, four supporting assets and 259 original notices. On this Mac,
Python's default CA setup lacked its issuer bundle; setting
`SSL_CERT_FILE=/etc/ssl/cert.pem` selected the trusted system bundle without
turning off TLS verification. The live check exposed GitHub's HTTP 415 for the
archive Accept header on the commit API; the API now uses its JSON media type,
covered by the real request-packet fixture. No archives were duplicated locally.
The independent source-only readback receipt is retained outside candidate source
at `/private/tmp/beatsprig-exporter-public-source-readback.json`, SHA256
`cc4590e280dd2979b944504a48be764c687f0bc641b52311dbe0f690b392eb0d`.

The compressed consumer fixtures preserve exact original bytes from FAILED run
34696012333. Their manifest explicitly records consumer acceptance true but
installation qualification false (the post-workflow module rejection prevented
normal-close qualification). Completed-state policy fixtures are generated only
inside temporary test directories and are never historical success evidence.
The separate original public-source receipt fixture is byte-identical to its
published asset. No private environment log, profile or binary payload was added.

Final Windows execution of this candidate, both complete original lifecycles,
independent root review and explicit export dispatch remain pending. The active
older run cannot qualify this new source through stale receipts.
