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
helpers. Installation preflight rehashes ten directly used helpers, and the
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

The workflow uploads JSON, text, XML, logs, owned UI screenshots and the two
retained project XML files from each consumer lifecycle. The
unsigned and test-signed MSIX, unpacked package, EXEs, DLLs, and ephemeral
certificate stay under the disposable runner's temporary paths. This first
Store-mode implementation adds no release exporter or binary artifact. License clearance, complete corresponding source,
physical audio, WACK, public release, and Store submission remain false until
separately completed and recorded.

A local policy-test pass does not establish Windows execution. Native package,
broker activation, real first-run settings interaction, loaded-module checks,
normal close, uninstall, and certificate cleanup require a fresh Windows run
against the exact source commit.
