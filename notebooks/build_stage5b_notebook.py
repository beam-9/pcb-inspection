"""Build a Stage 5B notebook from publication artifacts, without detector execution."""
import argparse
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient


def build(root, execute=False):
    root=Path(root).resolve()
    target=root/'notebooks/pcb2_stage5b_orientation.ipynb'
    if target.exists(): raise FileExistsError('Preserve executed Stage 5B notebook')
    md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
    notebook=nbf.v4.new_notebook()
    notebook.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    notebook.cells=[md('''# Stage 5B — Controlled orientation normalization

Post-confirmation PCB2 development experiment. This notebook reads saved small
publication artifacts and figures. It never loads raw images, weights, reference
banks or cache maps, and never performs inference, fitting or threshold tuning.
The exact historical Stage 4 D1 bank and thresholds remain the matched baseline.
Only confidently reversed crops receive exact 180° rotation; uncertain cases
remain unchanged. All maps are returned to original source coordinates before
comparison with the untouched union GT masks.'''),
    code('''from pathlib import Path
import json, hashlib, io
import pandas as pd
from PIL import Image as PILImage
from IPython.display import display, Image, Markdown
root=Path.cwd()
if not (root/'artifacts').is_dir(): root=root.parent
base=root/'artifacts/stage5b'
def table(name): return pd.read_csv(base/name)
def show(name):
    with PILImage.open(base/'figures'/name) as im:
        im.thumbnail((1100,1800)); buf=io.BytesIO(); im.save(buf,format='PNG')
    display(Image(data=buf.getvalue()))
review=json.loads((base/'independent_review.json').read_text())
assert review['passed']
metrics=json.loads((base/'results/modified_d1_metrics.json').read_text())
display(pd.json_normalize(metrics).T)
print('Independent saved-output review passed.')'''),
    md('''## All five reversed cases

The primary target was fixed before inference. Report every reversed case, not a
selection of favorable examples. Common-256 FP counts, pixel AP and IoU differ
from native unpadded-content spread. Scores divided by the frozen pixel threshold
are anomaly response ratios, not probabilities.'''),
    code('''paired=table('results/reversed_paired_results.csv')
assert len(paired)==5 and paired.image_id.is_unique
display(paired)
show('reversed_before_after.png')
show('reversed_fp_pixels.png')
show('reversed_pixel_ap.png')'''),
    md('''## Transform and defect signal

Rotation precedes historical letterboxing. Unpadded map content is resized back to
crop dimensions, inverse-rotated, pasted at the original crop location and finally
resized to common 256. The original source and annotation remain unchanged.
Disappeared and newly added exceedances distinguish suppression of background
response from loss of defect evidence.'''),
    code('''show('orientation_geometry.png')
show('reversed_map_differences.png')
display(table('results/map_difference_statistics.csv'))
display(table('regional/reversed_grid_comparison.csv'))'''),
    md('''## No-op controls and engineering cost

All 195 canonical/uncertain evaluation images were independently rerun through the
new wrapper. Saved comparisons test actual equality, rather than copying baseline
outputs. No reversed normal group exists: unchanged normal flags test implementation
integrity, not reversed-normal robustness. Runtime is measured separately from
scientific benefit.'''),
    code('''controls=table('results/no_op_invariance.csv')
assert len(controls)==195 and controls.image_id.is_unique
display(controls)
display(table('results/runtime.csv').describe(include='all').T)
display(Markdown((base/'findings.md').read_text()))'''),
    md('''## Limits and reproducibility

Only five reversed anomalies were available, all from already exposed PCB2.
Overlapping labels, union masks and unknown physical-board identities limit
interpretation. Canonical missing/small defects remain separate questions. Stage 4
remains the historical primary and retains its original timing/transport caveats.
The freeze receipt, independent review and completion manifest bind the saved
code, inputs and outputs; large raw images and maps remain local.''')]
    nbf.validate(notebook)
    if execute: NotebookClient(notebook,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
    nbf.write(notebook,target)
    print('Executed' if execute else 'Built', target)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.'); p.add_argument('--execute',action='store_true')
    args=p.parse_args(); build(args.root,args.execute)
