"""Build and optionally execute a saved-artifact-only Stage5C notebook."""
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient


def build(root,execute=False):
    root=Path(root).resolve();target=root/'notebooks/pcb2_stage5c_orientation512.ipynb'
    if target.exists():raise FileExistsError(target)
    n=nbformat.v4.new_notebook();n.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
    n.cells=[nbformat.v4.new_markdown_cell('''# Stage 5C — Orientation normalization with historical D2

Post-confirmation PCB2 development evidence. The primary matched comparison changes orientation only within D2. D1/D2 context does not isolate resolution. This notebook reads saved tables and figures; it neither fits nor scores a detector.'''),nbformat.v4.new_code_cell('''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image
root=Path.cwd()
if not (root/'artifacts').exists():root=root.parent
base=root/'artifacts/stage5c'
protocol=json.loads((base/'orientation_protocol.json').read_text())
display(pd.DataFrame([{'input_size':protocol['input_size'],'image_threshold':protocol['thresholds']['image_threshold'],'pixel_threshold':protocol['thresholds']['pixel_threshold'],'scope':protocol['scope']}]))
display(pd.read_csv(base/'preexperiment_signal_audit.csv'))'''),nbformat.v4.new_code_cell('''metrics=json.loads((base/'results/full_metrics.json').read_text())
display(pd.DataFrame([metrics['image']]))
display(pd.read_csv(base/'results/reversed_paired_d2.csv'))
display(pd.read_csv(base/'results/lost_case_signal.csv'))
display(pd.DataFrame([metrics['runtime']]))'''),nbformat.v4.new_code_cell('''controls=pd.read_csv(base/'results/no_op_invariance.csv')
assert len(controls)==195 and controls.passed.all()
review=json.loads((base/'independent_review.json').read_text())
assert review['passed']
display(pd.DataFrame([{'exact_noops':len(controls),'unchanged_normals':int(controls.label.eq('normal').sum()),'independent_review_passed':review['passed']}]))'''),nbformat.v4.new_code_cell('''for name in ['reversed_d2_before_after','lost_case_256_vs_512','orientation_256_vs_512','reversed_fp_pixels','reversed_pixel_ap','runtime']:
    display(Image(filename=str(base/'figures'/f'{name}.png')))'''),nbformat.v4.new_markdown_cell('Read the [Stage 5C chapter](../docs/journey/stage_05c_orientation_512.md) for interpretation, limitations and the next decision. Local caches are needed to independently audit raw maps; this notebook only needs the saved summaries and figures.')]
    if execute:NotebookClient(n,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
    nbformat.write(n,target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--execute',action='store_true');a=p.parse_args();build(a.root,a.execute)
