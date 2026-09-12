# BeatSprig Store display-name repair

The original Store MSIX from run 34709154092 was read directly. Its Properties and
VisualElements DisplayName were both `BeatSprig 1.0.1`; the VisualElements Description
was `BeatSprig qualification package`. Microsoft rejected the unreserved display name.

`create_manifest` and the independent `validate_manifest` now require `BeatSprig` in
both display-name locations and `BeatSprig music creation` in both descriptions, for
both fixed identity modes. Identity version remains 1.0.1.0. Store identity, publisher,
ApplicationId, executable, capability, package routes, native editor titles, musical
consumer workflow, source/license gates and all ownership/cleanup checks are unchanged.
Original receipts/packages and marketing files were not edited.

Regression: the new direct production manifest tests first reproduced both bad names
and seven accepted stale-field mutations. After the repair all eight independent old
field mutations are rejected. Six focused tests passed in 3.842 seconds: the two new
manifest tests and four existing identity/container/installed/both-SDK-route tests.
`git diff --check` passed. These are local manifest/package fixtures; a fresh Windows
build and both complete installed lifecycles are required for the changed package.
No push, dispatch or Store mutation was performed.
