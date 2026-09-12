# BeatSprig qualification MSIX pipeline

`distribution/qualify-candidate.ps1` is the Windows CI entry point. After the
clean pinned native build, tests, install, and render checks succeed, it:

1. collects the exact staged PE imports with `cmake/msix/collect-pe-imports.ps1`;
2. creates the source, stage, notice, dependency, and render input receipt with
   `cmake/msix/prepare_inventory.py`;
3. invokes `cmake/msix/qualify-msix.ps1`, which packages and independently
   verifies the MSIX before `cmake/msix/qualify-msix-install.ps1` exercises the
   package broker and fresh first-run UI.

Qt binary SDK archives do not contain a reliable prefix-level `LICENSES`
directory. `distribution/collect_qt_notices.py` therefore validates and copies
the source-pinned Qt 6.11.2 notice bundle for the exact `qtbase`, `qtsvg`, and
build-only `qttools` modules selected in `candidate-inputs.json`. Its manifest
binds Qt's authoritative tag objects, commits, Git blobs, byte sizes and SHA-256
digests. It explicitly leaves complete corresponding-source closure false.

The package uses the CI-only identity `Trieflow.BeatQuay.Qualification` and the
customer `beatsprig.exe` host name. All three instrument modules are rebuilt
against that host import name and their imports are checked explicitly. It
contains the complete native stage, the exact three approved instrument DLLs,
the two original starter arrangements and their provenance/license files,
BeatSprig source notices, and the same-run Qt/vcpkg notices. Known debug CRT
files, unexpected plugin/project files, unresolved PE imports, source changes,
and incomplete or substituted evidence fail the run.

The workflow uploads JSON, text, XML, logs, and the owned UI screenshot. The
unsigned and test-signed MSIX, unpacked package, EXEs, DLLs, and ephemeral
certificate stay under the disposable runner's temporary paths. No Store
identity is inferred. License clearance, complete corresponding source,
physical audio, WACK, public release, and Store submission remain false until
separately completed and recorded.

A local policy-test pass does not establish Windows execution. Native package,
broker activation, real first-run settings interaction, loaded-module checks,
normal close, uninstall, and certificate cleanup require a fresh Windows run
against the exact source commit.
