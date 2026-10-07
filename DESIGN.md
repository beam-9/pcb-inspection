---
name: PCB–AD
description: A warm-paper inspection workbench and engineering exhibition.
colors:
  paper: "#f4f1e9"
  ink: "#242c29"
  muted: "#616a63"
  rule: "#c8ccc2"
  rust: "#a13f27"
  sage: "#496659"
  plate: "#222826"
  white: "#fcfaf5"
  action-text: "#ffffff"
  plate-text: "#e7e8e1"
  plate-muted: "#c5cdc4"
  plate-rule: "#56605a"
  selected-view: "#46544b"
  field-stroke: "#899489"
  phase-band: "#e4e9df"
typography:
  display:
    fontFamily: "Instrument Serif, serif"
    fontSize: "clamp(48px, 5.6vw, 84px)"
    fontWeight: 400
    lineHeight: 1.03
    letterSpacing: "-.025em"
  headline:
    fontFamily: "Instrument Serif, serif"
    fontSize: "clamp(35px, 3.5vw, 52px)"
    fontWeight: 400
    lineHeight: 1.03
    letterSpacing: "-.025em"
  title:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "21px"
    fontWeight: 500
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  control:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  control: "3px"
  status-dot: "50%"
spacing:
  compact: "12px"
  inset: "16px"
  standard: "20px"
  rail: "24px"
  section: "32px"
  open: "40px"
  major: "48px"
  generous: "70px"
components:
  button-primary:
    backgroundColor: "{colors.rust}"
    textColor: "{colors.action-text}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "12px 22px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "12px 22px"
  select:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "48px"
  view-selected:
    backgroundColor: "{colors.selected-view}"
    textColor: "{colors.plate-text}"
    rounded: "{rounded.control}"
    padding: "12px"
  journey-stage-active:
    backgroundColor: "{colors.sage}"
    textColor: "{colors.action-text}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
  measurement-rail:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    padding: "25px 24px"
  image-plate:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.plate-text}"
    padding: "20px 24px"
---

# Design System: PCB–AD

## Overview

**Creative North Star: "The Engineering Exhibition Workbench"**

The inspection workbench gives real photographic evidence the largest surface and places explanation beside it. Warm paper, charcoal plates, fine rules and editorial headings make the interface feel like an engineering exhibition catalogue with usable instruments.

The system stays restrained and flat. Rust marks actions and flagged decisions; sage marks the no-flag state without replacing its written explanation. Captions, exact-value rows and clearly separated evidence phases provide the visual structure.

**Key Characteristics:**

- Warm paper with charcoal photographic plates.
- Instrument Serif headings paired with DM Sans controls and reading text.
- Fine ruled measurements and generous editorial spacing.
- Visible evidence, explicit state labels and restrained functional motion.

## Colors

A quiet warm neutral field supports two functional accents and a separate scientific response palette. The frontmatter is the normative color source.

### Primary

- **Rust:** Primary controls, active navigation underline, flagged result headings and journey indices.

### Secondary

- **Sage:** No-flag headings, local-service indicator and checkbox accent. It signals a state, with a written explanation alongside.

### Neutral

- **Warm Paper:** Page canvas and skip-link surface.
- **Ink:** Main text and secondary controls.
- **Muted Ink:** Secondary explanations, labels and captions on paper.
- **Rule:** Fine borders and measurement separators.
- **Charcoal Plate:** Board photographs, response images and inspection controls.
- **Soft White:** Measurement rails, selects and saved figure backgrounds.
- **Action White:** Text on rust buttons.
- **Plate Text / Plate Muted / Plate Rule:** Readable labels, captions and separators on charcoal.
- **Selected View:** Tonal backing behind the active image-view control.
- **Field Stroke:** Upload stroke and processing outline.
- **Phase Band:** Fresh-category boundary background.

### Named Rules

**The Response Is Separate Rule.** The fixed response palette belongs to image data; rust and sage belong to interface actions and decisions. Keep the response legend visible with the map. Its scale, overlay colors and rendering details live in the sidecar.

## Typography

**Display Font:** Instrument Serif, with serif fallback.

**Body Font:** DM Sans, with sans-serif fallback.

**Character:** Large regular serif headings introduce the evidence; compact sans text supports precise controls and measurements. Italic serif phrases add editorial emphasis without a second display family. There is no separate monospace family.

### Hierarchy

- **Display:** Main heading role from the frontmatter. Internal-page titles use the observed narrower clamp (48px to 76px, 5.2vw); the mobile home title is (51px).
- **Headline:** Section headings; rail headings are intentionally smaller (34px), with decision headings (38px).
- **Title:** Compact sans subsection headings. Journey stage titles rise to (27px).
- **Body:** The browser's standard (16px) base, with paragraph line height from the frontmatter. Dense reading sections use (14px to 15px); home introductory copy uses (17px), becoming (16px) on mobile.
- **Control:** Buttons, links and navigation, with text-link weight (500).
- **Label:** Captions and measurement rows, with occasional secondary microcopy (11px). Metric values use tabular numerals in tables and compact stage measurements.

### Named Rules

**The Two Voices Rule.** Serif leads the story; sans carries operations, labels and exact values. Preserve this division on new screens.

## Layout

The shared header, main and footer use a centered maximum width (1440px) with horizontal gutters (5%). The desktop header is a single ruled row (94px minimum height). Main content starts below it (48px) and ends with generous breathing room (72px).

The home plate and measurement rail form a broad-to-narrow grid (3fr / 1fr), with the rail never narrower than (220px). Original and response figures sit side by side inside the plate. Inspection uses its own grid (2.7fr / 1fr), with a rail minimum (265px). These are connected surfaces separated by material and rules, not isolated cards.

At (1000px), inspection inputs become two columns and the inspection rail narrows. At (900px), the home composition and header tighten. At (760px), inspection, detail, model and about layouts become single columns; the result rail follows the image plate, controls stack and journey figures move below their stage copy. At (640px), the header wraps, the home title and workbench become single columns, and original/response home figures stack vertically at full width. Preserve full image content with contain sizing rather than destructive crops.

Long-form screens use split reading/evidence columns. Journey rows align an index, stage copy and a saved figure; phase boundaries interrupt the sequence with full-width ruled bands. The fresh-category band has a sage-tinted fill. The spacing scale summarizes repeated intervals; page-specific gaps remain in the source rather than being forced into one grid.

## Elevation & Depth

Surfaces are flat at rest. Material contrast, thin borders and generous spacing provide depth; the implementation has no ambient drop-shadow vocabulary. The active navigation link uses an inset underline, not floating elevation. Image-view selection is a tonal block on the plate.

### Named Rules

**The Flat Workbench Rule.** Use paper, plate and rail surfaces with fine rules to establish hierarchy. Do not add floating-card shadows to ordinary content.

## Shapes

Workbench plates and content regions are rectangular. Controls have only a slight corner easing using the control radius in the frontmatter. The serving-mode marker is circular. Solid fine rules organize text and measurements; the upload boundary uses a dashed stroke. Image surfaces preserve source proportions and clip their aligned overlays at the same bounds.

## Components

### Buttons

Compact, legible instruments with understated corners.

- **Primary:** Rust fill and stroke, white text, arrow separated by a generous gap (24px), minimum height (48px).
- **Secondary:** Transparent fill, ink text and rule-colored border.
- **Hover / Focus:** Brightness lowers to (.93) on hover. Focus uses the shared rust outline. Most disabled controls use opacity (.6) and a wait cursor; disabled upload controls use opacity (.7) and a default cursor.
- **Text link:** Ink, medium-weight sans, minimum height (44px); underline appears on hover.

### Inputs / Fields

Native controls stay visibly operable.

- **Select:** Soft-white surface, fine rule border, slight corners and full available width.
- **Upload:** Dashed field stroke around a full-width button (80px minimum height), with icon, filename and secondary instruction. Dragging introduces a pale tint.
- **Range / Checkbox:** Native input affordances with a warm range accent and sage checkbox accent. Labels remain adjacent and state controls can disable when unavailable.
- **Focus / Error:** Shared rust focus ring and explicit alert copy. Full focus CSS and native-state details live in the sidecar.

### Navigation

A compact sans navigation row sits between the wordmark and serving-mode label. Current location uses a rust inset underline and `aria-current`. On mobile the navigation takes its own full-width row; labels remain text, rather than becoming icon-only controls.

### Cards / Containers

The system uses connected plates, rails and ruled sections rather than a general card library. Plate and rail primitives are in the frontmatter. Rail definition lists separate each measurement with a rule; names stay left and values align right. Saved figures receive captions and enough space to be read as evidence.

### Inspection View Selector

Original, Overlay and Heatmap are explicit pressed-state buttons on the plate. A shared Framer Motion selection block moves with a spring (stiffness 400, damping 35). Controls are disabled before a result exists. The selected state is tonal, with readable text remaining above it.

### Decision Rail

A large serif decision heading is rust for flagged or sage for no-flag, followed by explanatory text and ruled measurements. Exact-value details expand below. A completed local or recorded result receives focus and status semantics. Keep written qualifications beside the state, including known-miss and uncertain-pose notices.

### Purpose, Methods & Proposed Work

Editorial purpose and inspiration use the same paper-and-rule language as the evidence trail. The purpose block pairs two text columns (1.1fr / 1fr), with a thesis in larger sans text (21px, line height 1.5) and muted source-bound qualification below the inspiration link. Its three principles occupy a separate full-width row; the one-class rationale follows beneath. Home uses a compact version of the same block. Athena appears as a source-linked inspiration with an explicit boundary, without introducing a separate visual identity.

Seven method explanations form a two-column ruled reading grid, each with a sans heading (22px), text (14px) and a muted “Why.” paragraph whose lead-in remains ink. Eight tool entries follow as a three-column table: tool/role with small recorded-version provenance, what it does, and why it was used. Column proportions are (31% / 34.5% / 34.5%); rows use generous vertical padding (18px) and fine rules. Below (760px), methods become one column and each table row stacks its three cells, with the final reason muted and the desktop table header hidden. Table captions and source links remain visible.

Five proposed future experiments use ruled split rows (1fr / 1.7fr), with title and sage status at left and labelled reason, next experiment and progress criterion at right. Mobile stacks each row. The proposal wording distinguishes future work from measured evidence; the scientific contents and version facts remain in the source-backed product content rather than becoming design tokens. Nine journey stages carry an additional muted rationale with an ink lead-in.

About section links wrap in a ruled text navigation row with a minimum link height (44px). Hash anchors address purpose, methods and future sections; these sections use scroll margin (24px). Cross-page hash links resolve after content loads, preserving the section destination.

### Source Reader

Project sources open inside the same paper workbench at `/read/<path>`, with a back link, serif document title, “Original project source” label and a ruled action row. The original path can wrap; “Download original file” remains a separate link. Where source metadata supplies a hash, a compact SHA-256 disclosure appears above the text. The reader presents the original source contents, rather than replacing them with rewritten UI summaries.

The reading column is centered at a maximum width (950px), with body text (16px, line height 1.7), serif document headings and fine rules. Markdown uses GFM formatting, including readable tables and links. CSV tables and the Python package/version table retain captions and column headers inside horizontally scrollable, keyboard-focusable labelled regions. Their minimum table width (440px) preserves usable columns on narrow screens. JSON uses labelled definition-list fields and nested expanded disclosures; arrays remain ordered lists. Other text uses a scrollable preformatted block.

At (760px) and below, the file/download row stacks, reading text becomes (15px), document h1 becomes (32px), and JSON fields stack label above value with nested fields inset (12px). Long paths, hashes and text wrap without changing the source data. Local and public builds use the same reader presentation; the public route rewrite supports direct source links. Recognized source-relative links open another reader, while external links and repository references remain explicit destinations. Only catalogued evidence images render in the reader.

### Interface Writing

UI headings, controls and explanations use plain, direct language: name the action, explain what a result means, and say where the limitation applies. The revised copy keeps the editorial serif hierarchy while making methods and states easier to read. This writing treatment applies to authored interface copy. Original scientific documents, exported results, dependency records and downloadable files retain their source wording and values; the reader only formats their presentation.

### Public Evidence Mode

The public static build shares the local workbench’s palette, typography, layouts and image controls. A ruled muted notice labels recorded evidence, the header identifies a saved-evidence preview, actions say “View saved result,” and the result rail names recorded inference runtime. Upload controls remain visibly disabled with an explanatory label, default cursor and opacity (.7). Local mode retains live upload and inference language. Preserve these visible distinctions when adapting the interface to a different serving mode.

### Journey Wayfinding

A warm-paper sticky bar names the stage being read and offers labelled stage-jump buttons. The active stage uses sage with white text; hover uses a pale neutral tint. Buttons retain minimum dimensions (44px by 44px). The bar sits below the viewport edge (12px) on desktop and at the top on mobile. Below (760px), the reading label becomes its own row and the stage controls use five columns. A thin rust progress line (3px) sits along the bottom.

GSAP ScrollTrigger updates the active stage and scrubs the progress line through the journey. ScrollToPlugin moves to a selected stage, accounting for the sticky bar, then focuses its linked heading. This is functional wayfinding: the content is never hidden pending scroll.

### Motion

Route and home entrances start visibly rendered: the route moves horizontally from (8px) to rest in (.16s), and the home plate moves vertically from (12px) to rest in (.45s). The result image fades in over (.25s), and the decision shifts from (8px) while appearing. `MotionConfig reducedMotion="user"`, local reduced-motion checks and the CSS preference fallback govern reduced motion. Journey progress uses linear scale animation tied to scroll with smoothing (.2s); stage jumps use `power2.inOut` (.65s). Reduced motion makes progress immediate and stage jumps instantaneous. Scoped `useGSAP` cleanup, image/font refreshes and media-query reversion keep the scroll geometry current. Exact transitions and preference behavior are recorded in the sidecar.

## Do's and Don'ts

### Do:

- **Do** keep real board images and their corresponding response together, with clear captions.
- **Do** let the image plate dominate and keep the measurement rail readable.
- **Do** retain the same response legend across inspected images.
- **Do** use explicit phase bands and captions to separate evidence contexts.
- **Do** preserve keyboard focus, written decision states and reduced-motion support.

### Don't:

- **Don't** substitute generated board pictures for project evidence.
- **Don't** turn the flat ruled workbench into a dashboard of floating rounded cards.
- **Don't** use sage or rust alone to communicate a decision.
- **Don't** relabel anomaly response as probability or a certified pass/fail outcome.
- **Don't** crop mobile home figures to force the desktop pair into a narrow viewport.
