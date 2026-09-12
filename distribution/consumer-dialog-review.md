# BeatSprig owned dialog discovery

Windows run34688758325 successfully observed actual tempo112,113,114,115 and116
after the four normal wheel detents. It then sent Ctrl+S once. The saved final
212-control UIA tree contains an enabled, visible `Save Project` Window with
class `lmms::gui::VersionedSaveDialog`, below the main accessible window. The
filename is an empty `QLineEdit`, automation ID
`QApplication.QFileDialog.fileNameEdit`. The Save button is correctly disabled
until a filename is supplied. The original desktop-child-only wait missed this
open dialog; it never reached filename input.

The fixture `cmake/msix/fixtures/save-project-34688758325.json` preserves the
actual main root and40 QFileDialog controls with the original receipt hash.
No screenshot or accepted workflow is fabricated from that replay data.

Exact-title window waits now opt into bounded discovery of nested accessible
windows from the already owned process tree. Every selected subtree is queried
again from its real UIA element, rather than inferred from automation-ID prefixes.
Native UIA identity deduplicates before every root or nested emission, and
ambiguous distinct same-title windows still fail. All observed subtree controls
must remain in the retained process. Native handles are now recorded for future
diagnosis; the existing input guard still refuses a zero dialog handle.

Global input selectors and screenshot checks retain their desktop-only inventory.
This matters because the real tree also contains MDI Mixer, Controller Rack and
Song-Editor windows. Promoting those globally would duplicate inputs and break
capture checks. Independent review found that issue in the draft; the final
implementation confines expansion to explicit title waits.

Filename selection uses the actual full ID and QLineEdit class. Immediately
before ValuePattern access and SetValue, the live ID, class and help must match
the retained selector, in addition to the existing role, name, PID, visibility,
enabled state and foreground checks. Independent review reproduced the former
selector-drift gap; the final regression proves refusal before pattern access.

Validation: the actual-provider replay and nine ownership/selector mutations,
ten production enumeration/wait/global-selector graph replays, and four live
value-setter cases pass locally. Enumeration tests include both duplicate
desktop/nested orders, distinct wrappers of one element, genuine ambiguity,
incomplete parents and owner loss before subtree queries. Existing tempo,
workflow/profile and display suites pass. The new tests run in the Windows
qualification orchestrator. These local tests are not installed Windows
qualification: Save, reopen, audio export and normal close require a fresh run.
