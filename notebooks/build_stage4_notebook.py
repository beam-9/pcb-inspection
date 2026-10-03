"""Build an artifact-only PCB2 confirmation companion; execute only on request."""
import argparse
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


def create_notebook():
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    notebook = nbf.v4.new_notebook()
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.cells = [
        md("""# Fresh PCB2 confirmation of the frozen normal-reference procedure

This companion reads saved tables, figures, configuration and review receipts.
It needs neither raw images nor cached features, memory banks or weights, and
performs no acquisition, feature extraction, selection, calibration or inference.

D1 at 256 is the declared primary. D2 at 512 remains a secondary result regardless
of its outcome. PCB1 results are development history; this is category-adapted
confirmation with newly fitted PCB2 normal references, not zero-shot transfer.
The synopsis below is computed from the reviewed saved results."""),
        code("""from pathlib import Path
import hashlib, json
import pandas as pd
from IPython.display import display, Image, Markdown
root = Path.cwd()
if not (root / 'artifacts').is_dir():
    root = root.parent
stage = root / 'artifacts/stage4'
folder = stage / 'comparison'
def load_json(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def show_table(name):
    display(pd.read_csv(folder / name).round(4))
def show_figure(name):
    display(Image(filename=str(folder / 'figures' / name)))
metadata = load_json(folder / 'report_metadata.json')
assert metadata['new_model_inference'] is False
for name, expected in metadata['outputs'].items():
    path = (folder / name).resolve()
    assert path.is_relative_to(folder.resolve()), 'Unsafe report output path'
    assert sha(path) == expected, f'Report output changed: {name}'
config = load_json(root / 'configs/stage4_protocol.json')
freeze = stage / 'freeze_receipt.json'
freeze_data = load_json(freeze)
assert freeze_data['config'] == config
reviews = []
for run in ['pcb2_d1_primary', 'pcb2_d2_secondary']:
    run_folder = stage / run
    normal = load_json(run_folder / 'independent_normal_review.json')
    review = load_json(run_folder / 'independent_review.json')
    assert normal['passed'] and review['passed']
    assert normal['prepared_sha256'] == sha(run_folder / 'prepared.json')
    assert review['complete_sha256'] == sha(run_folder / 'complete.json')
    assert review['freeze_receipt_sha256'] == sha(freeze)
    assert review['normal_review_sha256'] == sha(run_folder / 'independent_normal_review.json')
    reviews.append({'run': run, 'normal_review_passed': normal['passed'],
                    'confirmation_review_passed': review['passed']})
results = pd.read_csv(folder / 'd1_vs_d2.csv')
assert set(results.recipe) == {'D1 primary', 'D2 secondary'}
primary = results.set_index('recipe').loc['D1 primary']
print('Saved reports and both independent review chains verified. No raw/cache reads.')"""),
        md("""## Primary result and declared project criteria

All four practical criteria are jointly required. They were declared before
unsealing and are project feasibility checks, not statistical equivalence tests
or factory acceptance targets. Lower normal false-alarm rate is better."""),
        code("""criteria = config['primary_practical_criteria']
anomaly_count = int(primary.tp + primary.fn)
criterion_rows = [
    ('Anomaly recall', primary.recall, '>=', criteria['recall_minimum']),
    ('Normal false-alarm rate', primary.normal_false_alarm_rate, '<=', criteria['normal_fpr_maximum']),
    ('Median common 256 anomaly pixel AP', primary.median_pixel_ap, '>=', criteria['median_common_pixel_ap_minimum']),
    ('Peak-inside fraction', primary.peak_inside_count / anomaly_count, '>=', criteria['peak_inside_fraction_minimum']),
]
criteria_table = pd.DataFrame(criterion_rows, columns=['criterion', 'observed', 'comparison', 'declared_limit'])
criteria_table['passed'] = [value >= limit if sign == '>=' else value <= limit
                           for _, value, sign, limit in criterion_rows]
display(criteria_table.round(4))
display(Markdown(f"D1 recall **{primary.recall:.1%}**, normal FPR **{primary.normal_false_alarm_rate:.1%}**, "
    f"median anomaly pixel AP **{primary.median_pixel_ap:.3f}**. "
    f"All four project criteria: **{'passed' if criteria_table.passed.all() else 'not passed'}**."))
show_table('d1_vs_d2.csv')
show_figure('detection.png')"""),
        md("""## Frozen methods and normal-only geometry review

Both recipes retain frozen ResNet18 features, projected approximate greedy
selection from all fitting patches, 4,096 full 384-dimensional reference vectors,
Euclidean nearest-reference distance and maximum-patch image scoring. The
64-dimensional projection is used only for selection. Each recipe calibrates
its own thresholds from normal images with `higher` quantiles and strict `>`.

The inherited blue-margin crop and letterbox geometry was approved on construction
normals before final freeze. Held-out normals did not participate in adaptation.
These contact sheets are saved preflight evidence, not a new image read."""),
        code("""display(pd.Series({key: config[key] for key in [
    'primary', 'secondary', 'normal_split_counts', 'selector', 'calibration',
    'geometry', 'caps', 'anomaly_access_before_finalfreeze', 'retuning_after_unseal']}))
display(pd.DataFrame(reviews))
geometry_folder = stage / 'geometry_preflight'
geometry_review = load_json(geometry_folder / 'normal_geometry_review.json')
assert geometry_review['passed'] and geometry_review['geometry'] == config['geometry']
display(pd.read_csv(geometry_folder / 'visual_selection.csv'))
for sheet in sorted(geometry_folder.glob('normal_contact_sheet_*.png')):
    display(Image(filename=str(sheet)))"""),
        md("""## Localization and defect slices

Common 256 maps cover the whole source frame; outside-crop scores are zero.
Ground truth retains every annotated region. Pixel AP measures ranking, and
heatmap values are not probabilities. Type memberships may overlap and must not
be added as independent images. Fixed PCB1 area boundaries are reference bands
on PCB2; PCB2's own area quartiles are a supplemental descriptive view. Small or
empty groups remain visible and do not establish subgroup reliability."""),
        code("""show_figure('localization.png')
show_table('defect_type.csv')
show_figure('defect_type_recall.png')
show_table('defect_size.csv')
show_figure('defect_size.png')
show_table('pcb2_size_quartiles.csv')"""),
        md("""## Score scales, latency and development history

Thresholds are frozen normal-only estimates; no anomaly-driven threshold search
is performed. Scores have recipe-specific scales. Normal FPR describes review
burden on this sample. Saved CPU latency describes the measured environment.
Category differences mean PCB1-to-PCB2 changes do not isolate a causal mechanism."""),
        code("""show_figure('score_distributions.png')
show_figure('runtime_review_burden.png')
show_table('runtime.csv')
show_table('runtime_phases.csv')
show_table('pcb1_vs_pcb2.csv')
show_figure('journey.png')"""),
        md("""## Declared qualitative selection

Examples follow the frozen priority rule, ID tie breaks and deduplication rather
than replacing unfavorable outcomes. Cyan annotations retain the source region.
Map displays use each recipe's raw score divided by its frozen pixel threshold;
ratios and clipped colors are not defect probabilities. These sheets support
inspection, not tuning."""),
        code("""qualitative = load_json(folder / 'qualitative_metadata.json')
assert qualitative['new_inference'] is False
assert qualitative['selection_sha256'] == sha(folder / 'qualitative_selection.csv')
show_table('qualitative_selection.csv')
for page in qualitative['pages']:
    show_figure(page)
show_table('qualitative_metrics.csv')"""),
        md("""## Interpretation and limits

Read the primary result first and retain the secondary result without substituting
it after seeing outcomes. This evaluates one frozen category-adaptation procedure
on PCB2; it does not establish factory readiness, cross-category statistical
equivalence, or a causal benefit of coreset selection. Pose ambiguity, resolution,
reference budget and the particular source dataset remain limitations.

Application/UI, LLM integration and Stage5 work are deferred. The report provenance
below identifies the saved evidence behind this companion; execution verifies
small report and receipt hashes without touching raw inputs or model arrays."""),
        code("""display(pd.DataFrame({'saved_source': list(metadata['sources']),
                      'sha256': list(metadata['sources'].values())}))
print('Notebook execution completed from saved artifacts only.')"""),
    ]
    nbf.validate(notebook)
    return notebook


def build(root, execute=False):
    root = Path(root).resolve()
    notebook = create_notebook()
    if execute:
        NotebookClient(notebook, timeout=180, kernel_name='python3',
                       resources={'metadata': {'path': str(root)}}).execute()
    destination = root / 'notebooks/pcb2_stage4_confirmation.ipynb'
    nbf.write(notebook, destination)
    print(('Executed' if execute else 'Built unexecuted') + ' artifact-only notebook: ' + str(destination))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--execute', action='store_true', help='Only after both confirmation reviews and reports are ready')
    args = parser.parse_args()
    build(args.root, args.execute)
