# BeatSprig post-workflow module diagnostic

Run `34696012333`, public source
`8593ff44a149ce9538958ddef790a946363b8e9c`, failed at the post-consumer loaded-module
origin check. The outer GitHub step label is `Verify immutable inputs and
bootstrap vcpkg`, but the original log records successful native compilation,
tests, MSIX pack/unpack, ephemeral signing and installed-tree verification
before this failure. It is not an observed download/bootstrap failure.

The exact primary error at 2026-09-12 13:41:30 UTC is:
`Defender module is outside its platform root.` This is the generic rejection
from the fallback for modules outside the package and SystemRoot. The error
does not establish that the rejected DLL is a Defender DLL. The 106-row startup
module inventory was saved successfully; the post-workflow inventory never
returned, and the old helper did not preserve the offending module path.
The actual new module therefore remains unidentified.

## Actual consumer milestone, with overall failure retained

The original `consumer-workflow.json` has `acceptance=true`, all 13 ordered
stages from the original starter through the stopped unchanged project, observed
tempo values 112 through 116, save/reopen verification of 3 tracks / 55 notes /
4 bars, and three real unedited screenshots. The actual WAV has 1,824,856 bytes,
456,192 frames, stereo 44,100-Hz PCM16, duration 10.344489795918367 seconds,
peak 5,813, RMS 339.48922089775175, and passing AC energy in all four bars.
Its SHA256 is `7443170781fc8776f315159bb1210d0628eda0f88c563ddb29cd34935c4186ea`.

Overall installation qualification remains false. Normal close did not execute;
cleanup terminated the retained process with exit -1. `clean_close_verified`
and `uninstall_verified` remain false. Cleanup and evidence errors are empty,
and the owned profile/working-directory cleanup receipts are true. These
observations do not confer complete lifecycle or Store acceptance.

Private original evidence is retained under
`/private/tmp/beatsprig-34696012333-review/build-evidence/msix-install`:

| Original | Bytes | SHA256 |
| --- | ---: | --- |
| `/private/tmp/beatsprig-34696012333-failed.log` | 1325188 | `6671be8bcebf21acab8bdf0ac5057ba4c183182d55e6b90394e09c2bf0755d3f` |
| `installation-qualification.json` | 1100867 | `cf30942f21b7b55f4e9998c88f41a9fd203853b879a617482b1cedd8e8da26ba` |
| `consumer-workflow/consumer-workflow.json` | 998581 | `c1343cfb9c68fad8513d8a7e20b30f021e0cdffe80f8f9f6421cdf165db677d6` |

No original log, profile or audio payload is added to the source change.

## Narrow next-run change

Only the existing outside-package/SystemRoot fallback rejection is caught.
The diagnostic records the actual enumerated module name/path, retained process
ID, previously observed process and owned package full names, exact install/
SystemRoot/Defender roots, original reason and current consumer stage. It hashes
the original file, checking reparse status and size/write/creation observations
around the hash; failed reads remain null with an explicit observation error.
No DLL content is copied and no additional origin/signature is accepted.

It exclusively writes `loaded-module-rejection.json` and retains the same object
in final `installation-qualification.json`. Existing evidence is preserved on
collision. Hash/evidence failures do not replace the original origin rejection,
which is rethrown. The existing JSON artifact glob already retains this metadata.

`test_module_rejection.ps1` first failed against the old helper because the
original module context was absent. It then passed three real rejection cases:
normal metadata write, occupied evidence path preserved, and controlled hash-read
failure. Only its process-module enumerator and the last case's hash IO are
controlled; the original fallback path predicate and final rejection execute.
The existing Defender suite (3 valid fixtures / 16 refusals), Store identity
fixture (including 4 installed-verifier boundaries), and 10 final-evidence cases
also passed with PowerShell 7.6.6 and `TMPDIR=/private/tmp`.

This diagnostic is isolated from the unsigned-exporter WIP, which is retained in
stash `a18ed07a3a2e4c504c55ce5d5c368aa0004f04a8`. Actual identification requires a
fresh reviewed Windows run. No public push or workflow dispatch was performed.
