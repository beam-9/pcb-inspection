# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
React with Framer Motion inspection interactions, GSAP/ScrollTrigger journey scrolling and a local Python/PyTorch inference backend, confirmed by the user. Hosting is a later deployment decision.

## Users
Portfolio reviewers, interviewers and the project owner exploring a research PCB inspection demo. Audience and interview goals come from the supplied handoff.

## Product Purpose
Inspect an uploaded PCB using the frozen v1.0 detector, and make the complete engineering decisions and stopping rule understandable through an interactive journey.

## Positioning
A source-backed staged engineering story: geometry, reference memory, fresh-category transfer, pose failure and deliberate stopping after unresolved exposed-data errors. The demo preserves exact model behavior rather than presenting inflated confidence.

## Operating Context
Local desktop browser backed by a loopback Python process. Real VisA PCB2 benchmark examples and optional uploads. Uploads stay in memory; no account, storage or certified pass/fail workflow is required.

## Capabilities and Constraints
Exact Stage5C D2+orientation inference; strict frozen score thresholds; pixel response map; canonical/reversed/uncertain handling; original/overlay/heatmap views. GT appears only for annotated benchmarks. The recipe bank and weights are ignored local files. Explicit PCB1/PCB2 phase boundaries, uncertain/error/mobile states and source references are required.

## Brand Commitments
Model name PCB-AD-v1.0. Research and portfolio language. Use real project images; call visual output anomaly response, never calibrated probability or certified manufacturing decision.

## Evidence on Hand
`artifacts/model_v1/`, `artifacts/stage5c/`, `artifacts/stage6a/`, original VisA assets, all stage reports and hash-bound structured journey content. No industrial performance, arbitrary-category guarantees or testimonials exist.

## Product Principles
- Preserve the detector's scientific identity.
- Show failures alongside successful detections.
- Explain why each stage followed the previous evidence.
- Keep uncertainty and dataset boundaries visible.

## Accessibility & Inclusion
Keyboard-operable controls, contrast, readable image states, reduced-motion support, responsive journey and mobile inspection tabs are required by the supplied proposal.

## Purpose and public preview

Explain the independent project's human-review purpose and inspiration from Seagate's historical 2019 Athena case study, with a first-party source and a clear boundary: public VisA PCB data, no Seagate data or internal technology. Document methods, tools, role and rationale, nine controlled journey decisions, and future experiments with evidence needs and success criteria.

The Vercel-ready static portfolio uses explicitly recorded frozen-model benchmark results, disabled uploads and recorded runtimes. Live upload inference belongs to the local Python build; cloud inference requires separate feasibility work. No remote deployment has occurred.
