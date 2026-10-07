# PCB–AD v1.0 product validation

The local React/Framer Motion/GSAP workbench calls the frozen Python inspector. All six representative Stage 5C scores, decisions, poses and native/common/source maps match within 1e-5. The scientific code, ordered bank, pretrained weights and thresholds remain unchanged.

- 150 Python tests passed. Journey metrics match original CSV/JSON values; source figures are hash-checked. All example preview scores and poses match the smoke manifest.
- API verification passed: real upload, reversed normalization, known missed anomaly retained with benchmark GT, upload GT absent, corrupt bytes/unknown example/invalid JSON/empty input rejected, evidence traversal blocked.
- Playwright exercised real benchmark inference, uploaded reversed board, corrupt-image error and recovery, normal no-flag result, uncertain cue, known miss, Original/Overlay/Heatmap controls and benchmark annotation isolation. Reduced-motion mode and keyboard skip/navigation/history were checked.
- Desktop and 390px mobile routes were verified, including direct navigation to stage details. Representative screenshots are in `output/playwright/`. These browser checks are targeted manual automation, not a claim of exhaustive accessibility certification.
- All 901 files tracked at scientific commit `4abc845929bb0d67a1cf9b6882243adc8106b4ef` remain byte-identical or are retained in original navigation snapshots. Existing scientific artifacts and receipts retain their creation-state meaning.

The app binds loopback and depends on ignored local dataset/cache assets. It is not remotely deployed. New model experiments, a factory robustness study and release commit/tagging remain separate work.

Independent core and extension design reviews concluded **ship**, with no open material issues. DESIGN.md and its parsed token sidecar document the final build. The extension review replaced an earlier attempt that hit usage limits. The verification records and source/build identities are bound in `artifacts/productization/complete.json`.

The final extension adds source-backed Athena inspiration, nine journey rationales, seven methods and eight tool groups. Public static export verifies all six saved results against the frozen receipt and smoke scores/decisions/poses. It disables uploads and labels recorded inference. Both local and public production builds pass; Vercel deployment configuration is prepared, with no remote publication.

## Readable sources and copy revision

The reader replaces direct raw-source links across methods, journey and model pages. It formats Markdown/GFM, CSV, JSON and dependencies, follows indexed links inside the site, and offers original downloads. The source index verifies 232 identities in both builds, including the preserved historical README. Humanizer edits apply to interface prose; original scientific documents remain verbatim.

151 tests passed. Browser checks covered all four methods links, nested Stage 6A links, 36 CSV rows, mobile reader routes, byte-identical downloads, back navigation, unknown sources and error/retry recovery. Markdown script and unsafe-link probes did not execute. Both production builds passed; the independent reader review concluded **ship** with no open material issues.

The previous `complete.json` records the earlier productization state. `reader_revision_complete.json` binds the current reader and writing revision.
