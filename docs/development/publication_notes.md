# Publication snapshots

Published October2,2026. See `publication_manifest.json` for full commit identities.

- A2 diagnostics are preserved at commit `f08ab08`.
- Geometry/resolution experiments are preserved at commit `20682b2`.

The completion records identify the file contents at execution time. Verify their
paths in those historical commits when a current document has evolved. For example,
the A2 completion record binds its README; the later README adds completed geometry
results. This preserves the old document rather than rewriting its completion hash.
All source/doc/output hashes were checked against Git objects at the two commits.

`git show f08ab08:README.md` retrieves the historical A2 README. For a complete
snapshot, use a separate checkout of the corresponding commit rather than resetting
an active working tree. Raw inputs and large arrays remain local and ignored, so
checks that require them need the original dataset/weight setup described in README.

Fields saying local/uncommitted in original receipts and registry describe their
execution-time status. Publication commit identities are recorded separately rather
than editing historical experiment evidence. Stage3's attachment is a proposal;
no Stage3 fitting or anomaly evaluation is part of these commits.
