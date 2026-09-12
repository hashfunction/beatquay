# BeatSprig qualification MSIX pipeline

`distribution/qualify-candidate.ps1` is the Windows CI entry point. After the
clean pinned native build, tests, install, and render checks succeed, it:

1. collects the exact staged PE imports with `cmake/msix/collect-pe-imports.ps1`;
2. creates the source, stage, notice, dependency, and render input receipt with
   `cmake/msix/prepare_inventory.py`;
3. invokes `cmake/msix/qualify-msix.ps1`, which packages and independently
   verifies each fixed-identity MSIX before `cmake/msix/qualify-msix-install.ps1`
   exercises the package broker and fresh first-run UI. It runs the disposable
   identity first and the assigned Store identity second. Each complete lifecycle
   must finish before the next starts, including normal exit, exact uninstall,
   unsigned-input preservation and all owned cleanup checks.

Before bootstrap, the entry point removes only the original TortoiseSVN MSI
from the approved GitHub-hosted `win22` image `20260907.297.1`. This runner
preparation checks the original MSI product identity, both original overlay DLL
hashes and 90 installer-defined registry values in both registry views. It
records original inputs twice, the exact system MSI command and original exit,
then requires all relevant registrations and DLL files absent. Unknown images,
versions, paths, shared overlay clients, mutations, read errors, reboot-required
exits and remaining inputs fail. This helper is for that disposable CI image;
it is not run on customer machines. See `runner-shell-review.md` for provenance.
The application loaded-module origin policy remains unchanged.

The original `runner-shell-preparation.json` is bound into both package records.
Each installation rehashes it and rereads the registry/DLL absence during
preflight and immediately before fresh broker activation. Export independently
checks the original preparation, exact native uninstall result, and both
observations from each lifecycle. A previous run's preparation cannot qualify
the current source/run/attempt.

Qt binary SDK archives do not contain a reliable prefix-level `LICENSES`
directory. `distribution/collect_qt_notices.py` therefore validates and copies
the source-pinned Qt 6.11.2 notice bundle for the exact `qtbase`, `qtsvg`, and
build-only `qttools` modules selected in `candidate-inputs.json`. Its manifest
binds Qt's authoritative tag objects, commits, Git blobs, byte sizes and SHA-256
digests. It explicitly leaves complete corresponding-source closure false.

The CLI default remains `--identity-mode qualification`, using the CI-only
identity `Trieflow.BeatQuay.Qualification`. The only other mode is `store`, using
`1659hashfunction.BeatQuay`, publisher
`CN=B6A2631A-FD32-45CC-AE12-82466975F528`, version `1.0.1.0`, architecture `x64`,
publisher display name `hashfunction`, and the assigned family
`1659hashfunction.BeatQuay_r3hxytd7jt6c4`. Both modes retain the manifest
`Application.Id` value `BeatQuay`, compatible settings/data paths and customer
`beatsprig.exe` host name. The manifest application ID is separate from the
Microsoft account application ID. Arbitrary or cross-mode identities fail
manifest, ZIP, unpacked, installed-tree and package-record validation.

All three instrument modules are rebuilt
against that host import name and their imports are checked explicitly. It
contains the complete native stage, the exact three approved instrument DLLs,
the two original starter arrangements and their provenance/license files,
BeatSprig source notices, and the same-run Qt/vcpkg notices. Known debug CRT
files, unexpected plugin/project files, unresolved PE imports, source changes,
and incomplete or substituted evidence fail the run.

Both installations perform the existing starter opening, visible tempo edit
from 112 to 116, project save/reopen, real WAV export, and independent project
and audio-file checks. The second uses a fresh absent profile and working
directory, after the first has removed only its owned files. The current
consumer input, ownership, timeout and acceptance predicates are shared.

The native input, package, installed and consumer records bind the current
workflow run and attempt as exact positive-decimal strings and the exact source
commit. The source input inventory covers the package, verification and consumer
helpers. Installation preflight rehashes twelve directly used helper/input files, and the
consumer step rechecks those bytes before and after execution. Their observed
hash/size map is recorded with installation and consumer results. Actual UIA
main-window handles are recorded in startup, consumer and screenshot metadata.

The package record says `storeIdentityStaged` only when the fixed Store manifest
was staged; `installationQualificationPassed` remains false there. The installed
receipt says `installed_identity_verified` only after its separate installed-tree
verification returns, and `store_identity_used` requires that observation in
Store mode. Selecting Store mode or merely observing an Appx registration never
confers installation, consumer or release acceptance.

The separate metadata paths are `build-evidence/msix-package-record.json` and
`build-evidence/msix-install` for the disposable identity, and
`build-evidence/msix-store-package-record.json` and
`build-evidence/msix-store-install` for Store mode. The corresponding unsigned
filenames are `BeatSprig.Qualification_1.0.1.0_x64.msix` and
`BeatSprig_1.0.1.0_x64.msix`, in separate exclusive runner-temporary outputs.

The ordinary workflow uploads JSON, text, XML, logs, owned UI screenshots and
the two retained project XML files from each consumer lifecycle. An unsigned
Store export requires a separate explicit `workflow_dispatch` opt-in:
`export_store_package=true` and `reviewed_public_source` equal to the exact
independently reviewed public commit. The default is false. Both original full
installed lifecycles still run before export; their package/install/consumer
records retain their original meaning and bytes.

`cmake/msix/export_store_package.py` reconstructs both original package records
from the same-run native stage, source, PE/source-owner mapping and original
Microsoft SDK/redist DLLs. It checks the exact current Git commit/tree against
the anonymous public Git API, rehashes the two original unsigned packages and
SDK tools, verifies both installed receipts and all cleanup operations, rereads
the retained project files and raw screenshots, and checks the recorded typed
WAV metrics. The WAV was independently inspected while the app was running and
then removed by owned cleanup; the exporter explicitly does not claim to reread
that deleted audio file.

The separate publication pin identifies the previously published 17 source
archives and their original notice/build-guide assets. Export anonymously
streams every public asset and verifies its exact size and hashes, then binds
all 259 original notice members to both current source and Store payload. The
historical source-preparation and package-record flags remain unchanged; the
export receipt records only the newly verified delivery of source for the exact
current minimal native stage. An unmapped runtime, changed original Microsoft
DLL, unavailable source URL, signed output, wrong run/attempt or incomplete
lifecycle is refused.

The exclusive `build-evidence/store-export` directory contains exactly
`BeatSprig_1.0.1.0_x64.msix` and `BeatSprig_1.0.1.0_x64.export.json`. The latter
embeds the Store package record, original package/evidence hashes, both full
lifecycle summaries and public source proof. Local package/source/evidence
checks run again before and after copying. Cleanup removes only unchanged files
created by this exporter; changed or unexpected output is retained and the
original failure is raised. A success-only, explicitly opted-in artifact step
names those two exact files. Test-signed packages, unpacked payloads and ephemeral
certificates are not exported. This tool performs no binary release upload or
Store submission and makes no WACK, upgrade, device playback or recording claim.

A local policy-test pass does not establish Windows execution. Native package,
broker activation, real first-run settings interaction, loaded-module checks,
normal close, uninstall, and certificate cleanup require a fresh Windows run
against the exact source commit.
