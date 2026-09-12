# BeatSprig disposable runner shell preparation

Run **34699319354**, attempt 1, source **dc8145e166b3dee5c6ce68f7f375acc8310c5dfa**,
completed the native build, tests, stage, package installation and actual consumer
workflow. Its post-workflow module check then rejected
`C:\Program Files\Common Files\TortoiseOverlays\TortoiseOverlays.dll` in retained
PID 8040, whose exact full package identity was
`Trieflow.BeatQuay.Qualification_1.0.1.0_x64__a74jba1vjrwc6`.
The original module was 142,024 bytes, SHA256
`65c22cb11e8415f31f25a0273abe7c68ffa0a39bcd7d74c2e2ac9d9b59231f5c`.
The original refusal, `Defender module is outside its platform root.`, was the
last available policy branch's message; the path and byte identity establish
TortoiseOverlays. No Defender origin was accepted or inferred.

The consumer receipt independently accepted 116 BPM, three tracks, four bars,
55 notes, exact project save/reopen, and an actual 1,824,856-byte stereo PCM16
44,100 Hz WAV. Overall installation, normal close and uninstall were **not**
qualified. Original receipts remain unchanged. This source change does not claim
that either complete lifecycle or a Store export has passed on Windows.

## Primary provenance

- The [immutable GitHub runner image](https://github.com/actions/runner-images/blob/win22/20260907.297/images/windows/Windows2022-Readme.md)
  was Windows 2022 image `20260907.297.1`. Its
  [TortoiseSVN installer script](https://github.com/actions/runner-images/blob/win22/20260907.297/images/windows/scripts/build/Install-TortoiseSvn.ps1)
  (Git blob `48f04463cc5f35da9d1d625c4bd081fd26ac23ed`) installs the Chocolatey
  `tortoisesvn` package. Subversion CLI 1.14.5 is not the MSI product version.
- The original [TortoiseSVN 1.14.9 installer](https://downloads.sourceforge.net/project/tortoisesvn/1.14.9/Application/TortoiseSVN-1.14.9.29743-x64-svn-1.14.5.msi)
  is 31,268,864 bytes, SHA256
  `244f3d754212ff65d057a1a02f99dd59f8b4c7ea4e4dd33eae8fb9b52895eec2`.
  Its read-only MSI Property table gives product code
  `{23095FB3-EE67-4F2C-9827-7BE50F389442}`, product name
  `TortoiseSVN 1.14.9.29743 (64 bit)` and MSI version `1.14.29743`.
  The package version is `1.14.9.29743`. The installer was **not executed**
  during this audit.
- Independent CAB extraction of the two individual overlay members produced the
  exact rejected x64 hash above and the x86 hash
  `45a6942bec99b4975b70ec2209037de1b45b3c8e1ff47edff4b9c275f55f8976`
  (106,184 bytes). Both File-table versions are `1.1.5.29440`. The MSI Registry
  table supplies the nine overlay CLSIDs, exact two-leading-space shell names,
  in-process server paths, Approved entries and SVN provider mappings in each
  registry view. These 72 values are retained in `runner-shell-inputs.json`.
  Unrelated icon preferences are not runtime DLL registrations. Any additional
  provider client, alias, unexpected value, subtree or DLL path fails inspection.
- The app already uses Qt's non-native file dialog and suppresses custom folder
  icons. The exact [Qt Windows platform source](https://github.com/qt/qtbase/blob/ef55f427f2c8b410d34f8a7681020a3000cf6866/src/plugins/platforms/windows/qwindowstheme.cpp)
  still requests `SHGFI_ADDOVERLAYS` for file icons; the
  [Windows API contract](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shgetfileinfow)
  supports loading registered shell overlays. No product dialog or icon behavior
  is changed to avoid this evidence.

## Implementation and limits

Only the exact GitHub-hosted repository/image/Windows 64-bit context may start
preparation. Read-only registry enumeration covers both machine/user hives and
both architecture views. Original DLL ancestors must be free of reparse points;
bytes and timestamps are checked while hashing. Two complete original snapshots
must match before the one allowed machine mutation:

```text
C:\Windows\System32\msiexec.exe /x {23095FB3-EE67-4F2C-9827-7BE50F389442} /qn /norestart REBOOT=ReallySuppress
```

Registry-provided commands are never executed. The system MSI executable's
original path/size/hash, argument list, retained PID, wait result and original
exit are recorded. Exit 0 is required; 3010 and pending-delete files are failures.
No force-kill, registration deletion, broad cleanup or reboot is attempted.
Original preparation metadata is reserved exclusively before uninstall and
preserved on failure. Both package input receipts bind its exact bytes.

Each fixed-identity lifecycle checks the preparation and actual current absence
before trust/install mutations and again before broker initialization. Original
module policies, consumer actions, timeouts, file/audio oracles, both complete
normal-close/uninstall/owned-cleanup lifecycles and source-publication export
gates remain required. The unsigned exporter independently checks the original
MSI receipt, exact source/run/attempt/pin, original bytes/registry, full absence,
and both time-ordered fresh observations for each identity.

This is a bounded preparation candidate. The original runner package registry
has not yet been observed directly: the next Windows run must prove that it
matches these original-installer pins and can be removed cleanly. An unexpected
version, path, shared component or residue produces metadata and stops; there is
no fallback mutation or relaxed module acceptance.

## Validation and next dispatch

The new production sequence tests first failed because the preparation boundary
was missing. Both real installer closure cases first failed because broker
initialization could occur without the required shell check. Independent Python
export cases first accepted omitted fresh-launch observations, then refused them
after the new verifier was connected. Generated success fixtures are policy
tests only and never replace the original failed Windows receipt.

Focused commands from this source directory:

```text
pwsh -NoLogo -NoProfile -File cmake/msix/test_runner_shell.ps1
pwsh -NoLogo -NoProfile -File cmake/msix/test_store_identity.ps1
pwsh -NoLogo -NoProfile -File cmake/msix/test_module_rejection.ps1
pwsh -NoLogo -NoProfile -File cmake/msix/test_store_export_dispatch.ps1
python3 cmake/msix/test_store_workflow_evidence.py -v
python3 cmake/msix/test_msix_qualification.py -v
python3 cmake/msix/test_export_store_package.py -v
```

Local results: all **45 Python cases** passed (22 package, 11 lifecycle/export
evidence, 12 unsigned exporter). All **19 PowerShell fixture scripts** passed,
including six actual preflight/Appx boundaries, eight actual installed-verifier/
broker boundaries, the runner preparation/readback refusals, unchanged module
rejections, original consumer controls/tempo/export, and both-mode dispatch.
`git diff --check` passed. The MSI uninstall and actual Windows registry reads
remain pending the new native run.

On macOS the PowerShell file fixtures use `TMPDIR=/private/tmp` to preserve the
existing rejection of symlinked temporary ancestors. No installer runs locally.
After independent review, create a clean public snapshot of this exact candidate,
push it, and explicitly dispatch `windows-candidate.yml` at that public ref.
If opting into unsigned export, pass `export_store_package=true` and
`reviewed_public_source=<the reviewed public snapshot commit>`. The exporter
requires that commit to equal the run's actual checkout and anonymous public Git
tree; a private source commit or a previous successful source is invalid. Its
only two final outputs remain the unsigned `BeatSprig_1.0.1.0_x64.msix` and its
`.export.json` receipt. No native run is dispatched by this change.
