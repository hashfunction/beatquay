# BeatQuay identity, default paths and release runtime

This is section 1 of the approved BeatQuay release-stage plan. Product display
identity is **BeatQuay 1.0.0**, published by **Trieflow LLC**. Canonical routes are
https://beatquay.trieflow.com, `/privacy`, and `/support`. The CMake identity
module generates the shared C++ constants and Windows numeric/string version
resources. `LMMS_VERSION`, XML element names, project/config schema versions,
upstream authors/copyrights and the `lmms.exe` synth-host ABI remain unchanged.

The ordinary empty editor has the exact unlocalized title `BeatQuay 1.0.0`.
Named projects retain their basename; modified projects retain `*`; recovery
sessions retain the recovery warning. Settings uses `BeatQuay - Settings` and
recovery uses `BeatQuay - Project recovery`. The genuine first-run working-folder
question remains interactive. About exposes canonical product/privacy/support
links and explicitly attributes LMMS, with the upstream authors and license tabs
preserved. CLI version output includes product title, publisher and canonical URL.

Default paths are intentionally separate, without automatic migration:

| Mode | Settings file | Working folder |
| --- | --- | --- |
| Installed | Qt home directory `/.beatquayrc.xml` | Qt Documents directory `/BeatQuay/` |
| Portable marker present | Application directory `/.beatquayrc.xml` | Application directory `/beatquay-workspace/` |
| Development CMake cache | Build directory `/.beatquayrc.xml` | Installed BeatQuay default, or portable BeatQuay folder if selected |

An explicit `--config` path is still honored, including its chosen working
folder. Existing project filenames, templates, plugin-resource lookup, explicit
`LMMS_DATA_DIR`/theme inputs and serialization are preserved. The tests use real
ConfigManager load/save operations with upstream sentinel XML, selected explicit
config paths, and fresh subprocess homes/application folders. They check actual
Qt Documents selection but redirect loader mkdir behavior into the disposable
home before loading, so even a preexisting developer Documents folder is safe.

The new original geometric SVG/PNG/ICO mark uses the approved site palette and
has a deterministic Python-standard-library generator. No upstream logo is
relabeled. See `data/branding/README.md`; `--check` verifies exact source bytes.
The main/splash/About/recovery resource is embedded; Windows resource and tile
paths use the same original artwork. The unmodified upstream README is retained
separately from the product README. Existing generic theme icons and attribution
remain installed. CPack's public name, publisher, version and install folder are
BeatQuay-specific; this is not an NSIS qualification claim.

MSVC runtime discovery now separates release and debug lists. Release runtime
files remain available to every configuration (Debug can load release-built
third-party DLLs). Debug runtime install rules are restricted to `Debug` only;
a single-config release build does not even request debug-runtime discovery.
The actual CMake configure/generate/install fixture covers Debug, Release,
RelWithDebInfo and MinSizeRel with both Ninja and Ninja Multi-Config. Its only
substitution is redistributable discovery, using unmistakable synthetic files;
it does not claim Windows runtime/source licensing clearance. The package worker
must independently reject debug CRTs and unresolved PE imports in the real stage.

## Local checks and their limits

The real default-loader tests were RED in all three modes because they read the
upstream sentinel; they now pass without changing upstream bytes and still load
and save an explicitly chosen config. The exact production title method was
RED (`Untitled - LMMS 1.3.0-alpha`) and now passes empty/named/modified/recovery
states. That method fixture uses a GUI-free Song/window boundary, not a displayed
application. The embedded PNG and actual Qt application identity are also tested.
Windows resource configuration was RED with upstream identity/version; the
configured resource now has BeatQuay metadata while retaining `lmms.exe` and
upstream copyright. All six non-Debug CMake install cases were RED with a debug
runtime; all eight configuration/generator cases are now GREEN.

Commands (Qt 6.11.2, CMake/Ninja and a real `samplerate.h` are prerequisites):

```sh
cmake -S tests/product-identity -B .cache/product-identity -G Ninja \
  -DBEATQUAY_SAMPLERATE_INCLUDE_DIR=/path/to/actual/libsamplerate/include
cmake --build .cache/product-identity --parallel 2
ctest --test-dir .cache/product-identity --output-on-failure
python -m unittest discover -s tests/scripted -p test_product_identity.py -v
python -m unittest discover -s tests/scripted -p test_release_runtime.py -v
python data/branding/generate.py --check
python -m unittest discover -s tests/scripted -p 'test_starter*.py' -v
python -m unittest discover -s tests/scripted -p test_candidate_render.py -v
```

The standalone target compiles actual ConfigManager/PathUtil/ProjectVersion. Its
headless-only support supplies the absent GUI/null-Engine boundary; the native
CTest versions link the real application objects, without those substitutions.
The native test registry adds the two actual config/branding Qt suites plus
runtime/resource/asset Python checks (five additional suites). The separate local
title method fixture does not claim real native window acceptance.

All three local Qt suites pass (12 Qt cases including setup/cleanup), two
resource/install Python tests and eight runtime-install subcases pass; the 22
starter and 13 candidate-render Python regressions and asset/generator checks
pass. Actual modified C++ files were syntax-checked against Qt 6.11.2 with the
previously verified minimal Apple dependency headers. Five pass `-Wall -Werror`;
MainWindow requires an explicit POSIX `unistd.h` prerequisite and suppression
of existing unrelated Qt deprecation warnings for this isolated Apple syntax
check. No production warning settings or native dependencies were changed.
The standalone build is approximately 5 MiB, not a second full product build.
Logs remain under `/private/tmp/beat-identity-*`, `/private/tmp/beat-brand-*`,
`/private/tmp/beat-title-red.log`, `/private/tmp/beat-resource-red.log`, and
`/private/tmp/beat-runtime-*`.

Fresh exact-source Windows compilation, all native suites, real staged runtime
inventory/import checks, first-run GUI/title/icon acceptance and installed MSIX
qualification remain required. Physical audio/device behavior, source/license
closure and Store submission remain separate. No public push, workflow,
qualifier, MSIX pipeline, source/deployment status or account change is included.
