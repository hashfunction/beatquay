# BeatSprig consumer inventory refusal observation

Windows run `34704891815`, attempt `1`, public source
`a6a1fdec66cc8f24310f73cf1da6e5c47c7685c2` (local source
`f5529d8e9ffb72565cf23ef5dc2b0578e0f3ee9a`) completed the disposable
qualification lifecycle. The unchanged production `verify_lifecycle` independently
accepted its original eleven retained files, full input/project/WAV/module records,
profile/display cleanup, normal PID 7508 exit 0 and uninstall. The WAV receipt records
1,824,856 bytes, 44.1 kHz stereo PCM16 and 10.344489795918367 seconds; both actual
saved projects have SHA256
`98df100120e09fbf245e003e0d5a8a4b12197681054bf0edd7c0a4b422c1f347`.

The assigned Store process (PID 744, main HWND 2883910) reached
`reopened_project_verified` at `2026-09-12T16:50:42.1320692Z`. Its last recorded
input was Ctrl+E, with current action `export_project_wav`. The subsequent control
enumeration threw `Foreign control in owned consumer window`, before any export
filename ValuePattern input. No export-settings/completion/WAV evidence exists for
this lifecycle. Failure cleanup reports no errors or residual registration; normal
close and normal uninstall verification are false.

The prior implementation discarded the rejected control and partial enumeration
before updating `last_observation`. Every control in the retained earlier trees is
PID 744. The last real screen shows the original saved arrangement, not the failure
instant. This evidence does not establish the rejected control's actual PID, provider
or HWND, and does not justify treating it as a broker or transient provider failure.

Original receipt bindings (files remain unchanged outside this repository):

| Original file under build-evidence | Bytes | SHA256 |
| --- | ---: | --- |
| msix-install/installation-qualification.json | 1108702 | 898f2991a7ee40d56db2eecf420af6887a5e9e13a8c564283293437f4b2078dd |
| msix-install/consumer-workflow/consumer-workflow.json | 1001269 | 3a2db9bc67120d95b7b2c2fe55af5bb9402c113c2157600482c10190b42f34f5 |
| msix-store-install/installation-qualification.json | 969299 | 5dd14e06bb57f9ba3ef9f0e2d621feb3752c95919b86e5e58b3d138203209475 |
| msix-store-install/consumer-workflow/consumer-workflow.json | 869520 | 80dd6373cc7aed5b592c4ec2673f6bd92ea36747a645629513a395667ca37ee1 |

The new observation attaches exactly the rejected snapshot, root snapshot and
control index/count to the same exception at the existing immediate wrong-PID
refusal. The caller retains these under `inventory_refusal`, along with expected
PID, current action, original script stack, and the index/count of its owned desktop
enumeration. For a nested window, that index identifies the containing desktop
enumeration entry; the retained root snapshot identifies the actual queried subtree.
No partial tree is exposed as a complete observation.

Each snapshot retains only ten scalar properties and six named text fields. Text is
limited to 1,024 characters per field (2,048 for Value); the stack is capped at 4,096,
action at 256, and each secondary error at 2,048. Exactly two snapshots and one
native observation are retained, with explicit text/stack truncation flags. Native
observation rechecks the retained process's existing ownership predicate, then reads
only current/retained main handles and numeric main/foreground HWND, PID and thread
IDs. It does not enumerate another process or change focus. Native/read/serialization
errors are secondary; the original refusal message and stack remain authoritative.

The existing ownership, incomplete-tree, bound, input, timeout, audio, lifecycle and
cleanup predicates are unchanged. No retry, screenshot or new successful-run field
is added. Marketing work remains separate and unbound pending a real successful
assigned Store export.

Verification uses the actual production traversal, reader and filename-dialog route
with a test-only provider boundary. The red test first failed because the new reader
and retention did not exist. Ten passing cases cover the exact offending snapshot,
root/index/count/stack, zero and previous-process PID refusal, immediate traversal
stop, no filename input or second desktop enumeration, bounded text, secondary
native/writer failure, unchanged valid reads and unchanged root ownership refusal.
These macOS PowerShell fixtures are not native Windows acceptance. The new fixture
is included in the existing Windows MSIX test sequence. Fresh Windows evidence is
still required to identify the actual rejected provider and qualify the Store flow.

Local verification completed: all 76 `cmake/msix/test_*.py` tests passed in 36.790s;
the new ten-case PowerShell fixture and eight existing dialog/enumeration, consumer,
export-combo, tempo, display, installation and registration suites passed.
The known local PowerShell executable is
`/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`.
The Python suite's first invocation could not find `pwsh` for its PE-collector
fixtures; the complete rerun used that directory on PATH and `TMPDIR=/private/tmp`.
Existing negative profile cases emit their expected Python refusal tracebacks while
the enclosing PowerShell fixture succeeds. `git diff --check` is clean.
