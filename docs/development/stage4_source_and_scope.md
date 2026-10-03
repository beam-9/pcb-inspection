# Stage 4 data and scope

Stage 4 uses the same owner-hosted VisA archive and pinned official split revision
as the earlier work. The source record and attribution remain in
[the source research](../source_research.md) and [data card](../data_card.md).
VisA is CC BY 4.0; derivative contact sheets preserve that provenance. No Seagate
or private factory images are used. Pretrained-weight commercial rights remain
unverified; no new weights are downloaded or trained.

PCB2 normals are acquired by exact byte ranges from the archive identity checked
against the original acquisition ETag and size. The prior PCB1 end boundary permits
header-only routing without broad probes. Stage 4 disables payload prefetch and
persists only allowlisted images. Held-out normal files can be acquired and hashed,
but are not decoded, viewed or scored before the final freeze.

The 901 official training normals are split into 720 fitting and 181 calibration
images, grouping exact file SHA-256 duplicates and mirroring the seed-42 PCB1
algorithm. The 100 official held-out normals are reserved. Normal byte audits find
no exact duplicates or exact prior-PCB1 matches. Physical PCB identities and
perceptual duplicate independence remain unknown; aligned layouts do not identify
unique manufactured objects.

Historical PCB1 transport may have incidentally received unpersisted neighboring
payload bytes. No PCB2 image was discovered saved, decoded, viewed or scored before
Stage 4. This uncertainty is disclosed rather than describing the old downloader
as having guaranteed zero PCB2 byte transport. See the
[Stage 4 exposure ledger](stage4_exposure_ledger.md).

The anomaly loader code is frozen but remains uncalled until a final freeze receipt
and exclusive anomaly-access receipt pass identity and chronology checks. After
unseal it selectively acquires the official PCB2 anomaly images, matching source
masks and owner defect annotations; it preserves the original benchmark membership.
Decoding failures, leakage or changed identities stop rather than silently exclude
images or retune. Source masks retain every annotated region, including outside a
predicted crop, in the evaluation denominator.

D1 is primary and D2 secondary. Category-specific normal fitting/calibration tests
an adaptation procedure, not zero-shot reuse of PCB1 references. No PCB2 uniform
control is added, so absolute confirmation cannot establish the causal benefit of
geometry or selection. PCB1 history remains development evidence. Stage 5, review
applications and LLM integration are outside this execution scope.
