"""Build and execute a report notebook using only saved comparison artifacts."""
import argparse
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


def build(root):
    root = Path(root).resolve()
    folder = root / "artifacts/pcb1_memory_selection_comparison"
    if not (folder / "comparison_metadata.json").is_file():
        raise ValueError("Generate and review saved comparison artifacts first")
    notebook = nbf.v4.new_notebook()
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    notebook.cells = [
        md("""# Does representative normal-reference selection help?

This notebook reads saved PCB1 results and figures. It does not load raw images,
pretrained weights or memory arrays; it does not perform feature extraction,
selection, calibration or anomaly inference. PCB2 remains sealed.

The original frozen pilot is retained. C1/C2 are the completed uniform-memory
geometry experiments at 256/512. D1/D2 substitute one full-population projected
approximate greedy selector at the same 4,096-reference count. All subsequent PCB1
outcomes are development evidence, not a fresh confirmatory test.

Read the accompanying findings and journey chapter for the engineering decision.
This notebook intentionally presents every declared outcome, including regressions."""),
        code("""from pathlib import Path
import hashlib,json
import pandas as pd
from IPython.display import display,Image
root=Path.cwd()
if not (root/'artifacts').exists():root=root.parent
folder=root/'artifacts/pcb1_memory_selection_comparison'
metadata=json.loads((folder/'comparison_metadata.json').read_text())
assert metadata['new_model_inference'] is False and metadata['pcb2_exposed'] is False
for name,expected in metadata['outputs'].items():
 assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected
for family in ['geometry','coreset']:
 for size in [256,512]:
  path=root/f'artifacts/runs/{family}_{size}_v1'
  review=json.loads((path/'independent_review.json').read_text())
  assert review['passed']
  assert review['complete_sha256']==hashlib.sha256((path/'complete.json').read_bytes()).hexdigest()
print('Saved comparison artifacts verified; all four development reviews passed.')"""),
        md("""## One controlled substitution

Both resolutions use frozen ResNet18 layer2/layer3 features, 3×3 neighborhood pooling,
direct Euclidean nearest-reference distance in 384 dimensions, maximum-patch image
scoring, all-patch eligibility including padding boundaries, and the existing
crop/letterbox geometry. No orientation registration was added.

Selection alone uses a seeded Gaussian 384→64 projection. Ten fitting-normal anchors
initialize mean Euclidean distances; farthest-first updates retain minimum distance
to each selected center. The full fitting patch population remains eligible.
Projection is not used for anomaly scoring. The algorithm remains PatchCore-inspired.

Each new bank is recalibrated from the same 181 normal images using 95th/99th
`higher` quantiles and strict `>` decisions. Numeric thresholds are not reused."""),
        code("""display(pd.read_csv(folder/'comparison.csv'))
display(Image(filename=str(folder/'journey.png')))
display(pd.read_csv(folder/'matched_pair_changes.csv'))
display(Image(filename=str(folder/'matched_pairs.png')))"""),
        md("""## Detection and localization must be read together

Normal false-alarm rate is better when lower. Recall alone omits review burden.
AP and AUROC describe ranking; anomaly scores and heatmap ratios are not calibrated
probabilities. Pooled common 256 pixel AP includes all 200 images. Per-image medians
include all 100 anomalies and can reveal weaknesses hidden by pooling.

Maps are inverse-mapped into the entire source frame, with outside-crop scores
zero, before common 256 evaluation. Ground truth is nearest-resized directly from
the source and is never cropped to the prediction region. Source-resolution
per-image metrics are supporting views with different denominators."""),
        code("""display(pd.read_csv(folder/'type_recall_comparison.csv'))
display(Image(filename=str(folder/'type_recall.png')))
display(pd.read_csv(folder/'size_localization_comparison.csv'))
display(Image(filename=str(folder/'size_quartile_localization.png')))"""),
        md("""## Memory coverage is a measured sample, not a causal explanation

The 2,048 query positions per resolution were fixed using seed 44 before anomaly
outcomes. The uniform and coreset banks share those fitting-normal queries.
Distances are evaluated in the original 384-dimensional Euclidean scoring space.
Query positions can coincide with selected references; self-membership and exact
zero counts are reported. These are descriptive fitting-data coverage checks,
not independent normal-validation performance.

Read typical distances and upper-tail distances separately: a lower 95th percentile
or maximum can coexist with a higher mean or median. Padding-center fractions are
geometric proxies, not complete receptive-field support. Neither a smaller padding
fraction nor wider source-image representation proves detector improvement."""),
        code("""display(pd.read_csv(folder/'coverage_comparison.csv'))
display(pd.read_csv(folder/'memory_composition.csv'))
display(Image(filename=str(folder/'memory_composition.png')))
display(pd.read_csv(folder/'memory_regions.csv'))"""),
        md("""## Resources and score distributions

Preparation includes projection, all 4,096 selections, selected-reference/query
re-extraction, normal calibration and required diagnostics. D2 reuses the verified
normal-only engineering projection cache, but its measured original extraction
cost is charged to the 1,800-second gate; physical current work is recorded separately.
Peak RSS is process high-water memory. Latency is detector processing, without LLMs.

The original pilot excluded raw hashing from reported inference timing; development
includes it. That original-to-development timing comparison is not perfectly matched.
The C↔D comparison uses the same source-processing path.

Raw score distributions are shown separately by recipe and by calibration normals,
development normals and anomalies. Their scales need not coincide across banks."""),
        code("""display(pd.read_csv(folder/'runtime_comparison.csv'))
display(pd.read_csv(folder/'runtime_phases.csv'))
display(pd.read_csv(folder/'score_distribution_summary.csv'))
print('Raw per-image scores:',len(pd.read_csv(folder/'score_distributions.csv')),'saved rows')"""),
        md("""## The same eleven examples throughout development

These IDs and selection reasons were fixed in A2 before C1/C2 and D1/D2 outcomes.
They include strong/weak localization, near/low-score misses, small regions,
source defect types and normal false alarms. They were not selected to favor a bank.

The first columns show the original whole-source view and annotation at common 256.
Cyan outlines the unchanged annotation on each map. Display values are raw map
divided by that recipe's pixel threshold, clipped 0–2; the metric computation uses
raw scores. Compare uniform and coreset within each resolution first."""),
        code("""display(pd.read_csv(folder/'qualitative_selection.csv'))
display(Image(filename=str(folder/'fixed_a2_qualitative.png')))
display(pd.read_csv(folder/'qualitative_metrics.csv'))"""),
        md("""## Evidence limits and the next decision

This study tests one projected approximate greedy selector, one projection and
one 4,096-reference budget on already-exposed PCB1 development data. A positive
result cannot establish that memory selection was the only bottleneck; a negative
result cannot rule out other selectors or memory budgets. ResNet18, whole-board
resolution, unregistered pose and geometry-specific limitations remain.

The complete recipe and category-adaptation procedure must be frozen before fresh
PCB2 confirmation. PCB2 is not accessed by this notebook. Application/UI and LLM
layers remain deferred until a detector is worth demonstrating."""),
    ]
    nbf.validate(notebook)
    NotebookClient(notebook, timeout=180, kernel_name="python3",
                   resources={"metadata": {"path": str(root)}}).execute()
    destination = root / "notebooks/pcb1_memory_selection.ipynb"
    nbf.write(notebook, destination)
    print("Executed artifact-only memory-selection notebook", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    build(parser.parse_args().root)
