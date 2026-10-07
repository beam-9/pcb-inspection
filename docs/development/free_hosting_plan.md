# Free portfolio hosting plan

Prepared 2026-10-07; no deployment has been made.

## Recommended first deployment

Vercel's [Hobby plan](https://vercel.com/docs/plans/hobby) supports free personal projects within its limits. Use the static saved-evidence portfolio for this educational project. It shares the local workbench, journey, model card and purpose/tools/methods pages, but identifies all six benchmark results as recorded evidence. Upload controls are disabled. No live inference or manufacturing capability is implied.

In Vercel, import the repository and set **Root Directory to `web`**. Enable **Include source files outside of the Root Directory in the Build Step**, because the verified content and scientific evidence live in sibling directories; see the [official monorepo instructions](https://vercel.com/docs/monorepos/monorepo-faq). The included `web/vercel.json` selects `npm run build:public`, output `public-dist`, SPA route rewrites and security headers. The build uses the npm lock and Node; Python and ignored scientific caches are unnecessary. It verifies copied evidence hashes and the frozen-model receipt before producing the site.

Reproduce and preview from the repository root:

```sh
npm --prefix web ci
npm --prefix web run build:public
.venv/bin/python scripts/preview_public_site.py --port 8766
```

Open http://127.0.0.1:8766. Keep the clearly labelled saved-evidence mode when publishing. Never convert recorded runtime into a claim about cloud latency. Source PDFs remain external links; public VisA evidence is attributed on the site.

## Live inference is a separate deployment experiment

Vercel can support Python and now offers a [5 GB Large Functions beta](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size). That does not establish that this implementation will fit or run reliably. Its [function limits](https://vercel.com/docs/functions/limitations) currently include 2 GB memory / 1 vCPU on Hobby, a 4.5 MB request/response payload limit and up to 300 seconds with Fluid compute. The local app accepts uploads up to 12 MiB and measured scientific runtime has substantial memory use; those contracts need deliberate redesign and measurement before deploying live inference.

A future live service must verify Linux dependencies, model/bank availability and redistribution permissions, cold-start latency, peak memory, concurrent workload, image payloads, costs and data handling. The current standard-library server is intentionally loopback-only; a production service requires a suitable deployment entry point. Do not claim free live uploads before testing eligibility and usage limits in the chosen account.

Account publication and final URL selection follow the user's review of the completed site. The current work prepares deployment files without creating a remote project.
