# Current BeatSprig identity and compatibility

The customer product is **BeatSprig 1.0.1**, with Windows host `beatsprig.exe` and canonical [product](https://beatsprig.trieflow.com), [privacy](https://beatsprig.trieflow.com/privacy), and [support](https://beatsprig.trieflow.com/support) routes. Existing `.beatquayrc.xml`, Documents `/BeatQuay/`, and portable `/beatquay-workspace/` paths remain unchanged. The Store identity remains `1659hashfunction.BeatQuay` with ApplicationId `BeatQuay`. The actual disposable qualifier retains its separate CI identity and upgrades its version to `1.0.1.0`. The synth modules and native template-test host are rebuilt against `beatsprig.exe`; stale `lmms.exe` imports fail package validation. See [rename review](beatsprig-rename-review.md) for exact current scope and pending Windows gates.

The following is the preserved historical implementation and validation record. Its prior product names, executable basenames, source versions and pass claims apply only to the cited pre-rename candidates.

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
config paths, and fresh subprocess fixtures/application folders. They check actual
Qt Documents and home selection without opening the installed user's default
file. Installed-mode IO explicitly selects an owned config; portable/development
IO uses the real default in the copied application folder. All loader mkdir and
explicit config operations remain inside the disposable fixture.

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

## Windows run 34639261103: fixture ownership, diagnostics and source encoding

The actual Windows run at `0e7857bd8b4c95b5f7453e3a0b10c3c12a15deff`
passed 20 of 22 native CTest suites. Its retained Qt text report shows installed
ConfigManager isolation passing, while portable and development fail with empty
stderr. That evidence does **not** identify their child return codes or establish
a product-path defect. Exact [Qt 6.11.2 Windows source](https://raw.githubusercontent.com/qt/qtbase/v6.11.2/src/corelib/io/qfilesystemengine_win.cpp)
shows `QFileSystemEngine::homePath()` first obtains the process token's profile
using `GetUserProfileDirectory`; environment variables are only fallbacks when
that directory is unavailable. Thus setting HOME/USERPROFILE did not guarantee
isolation. The old fixture could create shared-home files, and its second/third
child could collide with the first child's `chosen-config.xml`. This collision is
source-supported and locally reproduced; the original native exit 23 remains
unobserved and must not be asserted as that run's definitive failure code.

The repaired fixture records requested and actual Qt homes separately, validates
the owned fixture home beside its copied application, and never opens or creates
files in the platform home. A small const read-only `configFilePath()` accessor
allows all three modes to compare the actual selected default with the expected
path. Installed mode then explicitly selects its per-fixture config for real
load/save; portable/development retain actual default IO in the copied app.
Neither ConfigManager's selection/load/save behavior nor native dependencies,
titles, upstream preservation or explicit-config expectations change. No hidden
test mode is added to the product. The absence of default-file IO in installed
mode is deliberate and is not represented as native home redirection.

The test child now writes each failing operation, numeric return code and relevant
owned path/expected value directly to flushed C stderr. Its main boundary always
records mode and completion code; the parent assertion includes the observed
exit code/status and both captured streams even when the child cannot report.
These messages concern only the test's generated data; they do not serialize
configuration contents. A lasting regression copies and launches the actual
native test executable with a fresh home/app folder, creates a real sentinel-path
collision, requires exit 21 plus the specific error/path in stderr, and verifies
the preexisting bytes survive. Before the repair that process exited 21 with
empty stderr, failing the new regression. A missing owned-home parameter now
fails closed before fixture IO. Three further real-process cases put preexisting
files in a separate Qt platform home and require unchanged bytes and no created
workspace there. Before repair all three created a workspace outside their
requested fixture home; installed exited 21 and portable/development exited 23.
All three pass after repair.

The separate runtime test failed on native Windows before CMake execution:
default CP1252 decoding of the UTF-8 root CMakeLists rejected byte `0x9d` at
position 9042. The test now reads and writes CMake text explicitly as UTF-8.
A retained test seam forces unspecified source-read encodings to actual CP1252
on every host, while honoring explicit encodings. It reproduced the same error
before the repair; all eight real configure/generate/install combinations now
pass. Only redistributable discovery remains synthetic, as described above.

Local rerun commands are the existing three standalone Qt suites and
`python -m unittest discover -s tests/scripted -p test_release_runtime.py -v`.
With actual Qt 6.11.2/Apple Clang 21, all three suites pass (16 Qt cases including
setup/cleanup); both resource tests and all eight runtime install subcases pass.
RED/GREEN logs are `/private/tmp/beatquay-identity-diagnostics-{red,green}.log`
and `/private/tmp/beatquay-identity-platform-home-{red,green}.log`, plus
`/private/tmp/beatquay-runtime-{cp1252-red,utf8-green}.log`. Python compilation,
Black and diff checks also pass. This is local diagnostic/encoding verification;
a fresh exact-source Windows run is still required to establish the repaired
fixture's native result and disclose any remaining failure. No native success
is claimed for this repair.
