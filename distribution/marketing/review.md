# Capture-only implementation review

Scope: only new `distribution/marketing/*` and the standalone manual marketing
workflow. Existing product, native consumer, installer, source-delivery and Store
export code are unchanged by this candidate. Parent's separate upstream-notice
repair `623bb692` remains the base. Binding remains null; no package is newly
qualified or marketing screenshot produced by these local checks.

The pipeline retains the exact original consumer function and delegates its
three original screenshots unchanged. Extra observations only refuse unstable,
foreign, hidden or out-of-bounds frames. The capture run has its own provenance;
original package evidence is not rewritten to look like this later run. Normal
input, actual musical project/WAV oracle, loaded-module policy, close and owned
cleanup are reused. Final publication independently replays the qualified
consumer verifier over fresh capture metadata and real retained project/PNG
bytes, then copies exactly three PNGs plus their provenance receipt.

Targeted local verification on macOS:

- 20 Python marketing cases passed in 5.977 seconds: null binding, exact typed
  run/export joins, real ZIP path/size/member refusal, whole original lifecycle
  replay, real package/SDK mutation refusal, exclusive/sealed cleanup, final
  consumer/frame/oracle/pixel mutations, and identical PNG publication.
- Three production PowerShell boundary fixtures passed in separate processes:
  original file/AST/ScriptBlock delegation and no replay; readable owned main
  and modal frame with 15 negative mutations; actual operation closures,
  immediate preflight refusal, retained-process cleanup refusal and preservation
  of unknown files. All new PowerShell files parsed successfully.
- Manual-only YAML parsed; isolated PowerShell File execution, child failure
  propagation and four exact success-only publication files checked.

The ownership implementation was tested red before creation, then green. The
final verifier refused generated path/oracle/input/stage/frame mutations and
changed raw PNG bytes. Generated completed-state fixtures derive from existing
policy fixtures and are explicitly not native success evidence. Running the
closure fixture as a nested script exposed scope isolation; the workflow now
starts a new PowerShell File process, as the original qualification runner does.

Native Windows capture, fixed-image/SDK availability and final visual review are
pending a reviewed successful Store export. No image editing, native run,
publication or Store change was performed here. Parent independent review is
required before pushing and binding the workflow.

## Original notice retention repair (run 34711210269)

The capture failed during preparation, before installation or screenshots. Its first error was `FileNotFoundError` for `metadata/build-evidence/notices/native/COMBINED-LICENSE.md`. Original run 34709154092 uploaded metadata through JSON/TXT/XML/log/PNG patterns; those patterns omitted 75 notice files (47 native and 28 Qt), including Markdown, source headers and extensionless licenses. The original package builder copies the entire notice tree to `licenses/dependencies/`, so all 75 remain in the retained unsigned Store package.

The capture verifier now joins a missing notice's exact byte/hash record to both its original package payload and the original exported Store payload. The existing full `verify_msix` traversal must still read and hash the complete unchanged Store container before verification can succeed. Existing metadata copies are read normally and may not fall back after a mismatch. Missing non-notice evidence still fails. No files are reconstructed or written by this verification; the original whole-record, source, SDK, unsigned-package and installed lifecycle gates remain unchanged.

Independent original-file verification matched the 21,177,783-byte Store MSIX SHA256 `d3bb0672b37266baa26c2bc3f791a05a3e31fe82c4786ea7421ac247298ba643`, then read each of the 75 omitted notice members and matched its bytes/SHA256 against both original package records. The source-backed package fixture reproduced the same missing COMBINED-LICENSE error before the repair. Afterward all five focused tests passed, including omitted-notice success, present-notice tampering, missing non-notice evidence, changed actual Store notice payload, stale records and signed-container refusal:

```sh
python3 -m unittest discover -s distribution/marketing -p test_original_packages.py
```

This is a capture-only repair. Microsoft subsequently rejected the old manifest display name; a separate manifest correction and fresh normal qualification/export must establish a new package binding before another capture run. This commit does not change that binding or claim native screenshots succeeded.
