# BeatSprig fixed Store identity and evidence bindings

First implementation checkpoint, 2026-09-12. Base local source:
`12d75198f03b0dd96f5fe72be511ac0e26752f9a`. This change has local fixture evidence;
the new Store installation lifecycle has not run on Windows. No binary exporter,
Store submission, source publication update or release clearance is claimed.

## Reviewable behavior

- Preserve `qualification` as the package/install CLI default. Add only the fixed
  `store` contract: `1659hashfunction.BeatQuay`, assigned publisher
  `CN=B6A2631A-FD32-45CC-AE12-82466975F528`, version `1.0.1.0`, `x64`, publisher
  display `hashfunction`, family `1659hashfunction.BeatQuay_r3hxytd7jt6c4`.
  `Application.Id=BeatQuay`, `beatsprig.exe`, existing customer window/display
  naming and compatible profile/data names remain the existing contracts.
- Thread the selected mode through real manifest creation/validation, staging,
  unsigned ZIP and SDK-unpacked checks, independent installed-tree verification,
  package-record reconstruction, temporary-copy signing, exact registration and
  broker AUMID. Arbitrary modes and cross-mode records/manifests are refused.
- Run disposable qualification and then Store qualification from the same native
  stage. Each uses the complete existing first-run, starter/edit/save/reopen/WAV
  workflow, normal-close, uninstall and owned-cleanup sequence. A failed process
  exit from the first qualifier prevents the second. Package outputs use unique
  exclusive runner directories; metadata uses separate `msix-install` and
  `msix-store-install` paths. Only the matching Store consumer `.mmp` metadata
  glob is added to the workflow artifact; no binary/profile/audio glob is added.
- Bind exact positive-decimal workflow run/attempt strings to the native input,
  package, installed, consumer and screenshot records. Source commit validation
  and the clean-checkout boundary remain required. Add the previously omitted
  package/verifier/input-producer helpers to the source hash inventory.
- Independently rehash ten directly used qualification helpers in preflight and
  before/after the real consumer workflow. Record their byte-size/SHA256 map in
  installed and consumer evidence. Add the actual observed UIA main HWND to the
  original startup/consumer/screenshot observations; all UI actions, selectors,
  ownership checks, timeouts and file/audio acceptance predicates are unchanged.
- Keep staged and installed observations distinct. The unsigned package record
  uses `storeIdentityStaged` and still has false installation/public/source-
  clearance flags. The installed receipt sets `installed_identity_verified` only
  after the independent installed-tree verifier returns. `store_identity_used`
  requires that observation in Store mode. Neither selecting Store mode nor
  observing a registration can set these installed fields. Neither field alone
  confers consumer or overall installation acceptance.

## Local verification

Commands run from the nested source checkout with Python 3.10 and the existing
PowerShell 7.6.6 executable at
`microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`:

```sh
python3 cmake/msix/test_msix_qualification.py -v
python3 cmake/msix/test_consumer_files.py -v
```

Results: **22 package tests** and **16 independent consumer-file tests passed**.
The package suite uses real files, ZIP containers and a controlled SDK process
seam to run both production build routes, recheck distinct output filenames,
exact manifest/payload bytes, and absence of package signatures. It tests actual
source/helper mutation and same-run/cross-mode refusals. New numeric `0`/`1`
substitutions for seven boolean record flags first reproduced seven failures;
explicit boolean validation then made all refusal cases pass.

All **16 PowerShell fixture scripts** listed by `qualify-msix.ps1` passed using:

```sh
TMPDIR=/private/tmp <pwsh> -NoLogo -NoProfile -File cmake/msix/<fixture>.ps1
```

The scripts are `test_qualify_msix_install`, `test_store_identity`,
`test_appx_preflight`, `test_msix_evidence`, `test_registration_ownership`,
`test_process_observation`, `test_window_evidence`, `test_first_run_flow`,
`test_defender_module`, `test_temporary_ownership`, `test_consumer_workflow`,
`test_consumer_export_combo`, `test_consumer_tempo`, `test_consumer_dialogs`,
`test_consumer_dialog_enumeration` and `test_consumer_display` (each `.ps1`).
Full local output is `/private/tmp/beatsprig-store-chunk-focused-tests.txt`.

The expanded fixtures exercise both identities in four real preflight outcomes,
40 real registration/uninstall/cleanup cases across native and CLIXML property
types, and ten exclusive final-evidence/package-integrity outcomes. They retain
failed-Add races, foreign registration preservation and exact uninstall checks.
The new binding fixture covers changed/missing helper bytes and strict mode/run
records, lifecycle order/first failure, and four actual activation-closure
receipt boundaries immediately before/after the installed verifier returns;
broker and consumer acceptance remain false in those controlled failure cases.
That fixture was rerun after its four timing cases were added and passed.

The initial full PowerShell command without `TMPDIR` reached the existing
first-run fixture and refused macOS's `/var` symlink. The full suite was rerun
with the real `/private/tmp` directory and passed, with the production reparse
guard unchanged. All 28 PowerShell source files parsed; `git diff --check` passed.

## Next boundary

Root review is required before a new public snapshot/run. Actual MakeAppx,
temporary certificate signing, fixed Store registration, broker launch, both
complete UI/audio workflows and cleanup remain a new exact-source Windows test.
The earlier source-only archive publication and its historical false clearance
fields are untouched. The independent unsigned exporter and public-source/
native-source delivery binding from the approved plan are the next separately
reviewable implementation chunk.
